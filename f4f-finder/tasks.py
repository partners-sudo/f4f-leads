import asyncio
from celery_app import app

from supabase_client import sb

from scraper.competitor_scraper import CompetitorScraper

from scraper.linkedin_scraper import LinkedInScraper

from scraper.marketplace_scraper import MarketplaceScraper

from enrichment.clearbit_integration import enrich_company
from enrichment.contact_verification import verify_contact
from enrichment.domain_finder import find_domain
from enrichment.email_finder import find_emails
from utils.address_parser import parse_address

from utils.logger import logger

# Valid fields for companies table (excluding auto-generated fields like id, created_at, updated_at)
VALID_COMPANY_FIELDS = {
    'name', 'domain', 'country', 'region', 'type', 'source', 
    'brand_focus', 'status', 'freshness_timestamp'
}

# Valid fields for contacts table (excluding auto-generated fields like id, created_at, updated_at)
VALID_CONTACT_FIELDS = {
    'company_id', 'name', 'email', 'phone', 'title', 
    'linkedin_url', 'confidence_score', 'last_validated'
}

def filter_company_data(data):
    """Filter company data to only include valid schema fields."""
    return {k: v for k, v in data.items() if k in VALID_COMPANY_FIELDS}

def filter_contact_data(data):
    """Filter contact data to only include valid schema fields."""
    return {k: v for k, v in data.items() if k in VALID_CONTACT_FIELDS}


def run_async(coro):
    """Helper function to run async code in Celery tasks, handling event loop creation."""
    try:
        # Try to get the existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        # If loop exists and is not closed, use it
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists in this thread (common during Celery retries)
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)


@app.task(bind=True, max_retries=3)
def scrape_competitor_partners(self, url, source="competitor"):
    try:
        scraper = CompetitorScraper(url)
        companies = run_async(scraper.extract_companies())
        for c in companies:
            enriched = enrich_company(c.get('domain'))
            c.update(enriched)
            # Filter to only include valid schema fields
            filtered_company = filter_company_data(c)
            sb.table('companies').upsert(filtered_company).execute()
        return {'count': len(companies)}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)

@app.task(bind=True)
def scrape_linkedin_companies(self, keyword):
    try:
        scraper = LinkedInScraper(keyword)
        results = run_async(scraper.extract_contacts())
        
        companies_saved = 0
        contacts_saved = 0
        
        for result in results:
            try:
                # Extract company and contact data
                company_data = result.get("company", {})
                contact_data = result.get("contact", {})
                
                # Enrich company data if domain is available
                # This will fill in missing fields like domain, country, region if LinkedIn didn't provide them
                if company_data.get("domain"):
                    enriched = enrich_company(company_data.get("domain"))
                    # Update company_data with enriched data (only if not already present)
                    for key, value in enriched.items():
                        if value and not company_data.get(key):
                            company_data[key] = value
                
                # Step 1: Save/upsert company (domain is unique, so upsert will work)
                if company_data.get("name"):
                    # If domain is missing, try to enrich by company name
                    if not company_data.get("domain"):
                        logger.warning(f"Missing domain for {company_data.get('name')}, will try enrichment by name")
                        # Note: Current enrich_company only works with domain, but this is a placeholder
                        # for future enhancement where you might enrich by company name
                    
                    # Filter to only include valid schema fields before upserting
                    filtered_company_data = filter_company_data(company_data)
                    
                    # Upsert company by domain (unique constraint) or name if domain is missing
                    # Supabase automatically handles upsert on unique fields
                    company_response = sb.table('companies').upsert(filtered_company_data).execute()
                    
                    # Get the company_id from the response
                    # Upsert returns the inserted/updated record(s)
                    company_id = None
                    if company_response.data and len(company_response.data) > 0:
                        company_id = company_response.data[0].get('id')
                        companies_saved += 1
                    else:
                        # If upsert didn't return data, fetch by domain or name to get the id
                        if company_data.get('domain'):
                            fetch_response = sb.table('companies').select('id').eq('domain', company_data['domain']).limit(1).execute()
                        else:
                            fetch_response = sb.table('companies').select('id').eq('name', company_data['name']).limit(1).execute()
                        
                        if fetch_response.data and len(fetch_response.data) > 0:
                            company_id = fetch_response.data[0].get('id')
                            companies_saved += 1
                        else:
                            logger.warning(f"Could not get company_id for: {company_data.get('name')}")
                            continue
                    
                    # Step 2: Save contact with company_id reference
                    if company_id:
                        contact_data['company_id'] = company_id
                        # Only save contact if there's meaningful data (linkedin_url or phone)
                        if contact_data.get('linkedin_url') or contact_data.get('phone'):
                            # Filter to only include valid schema fields
                            filtered_contact_data = filter_contact_data(contact_data)
                            sb.table('contacts').upsert(filtered_contact_data).execute()
                            contacts_saved += 1
                else:
                    logger.warning(f"Skipping record - missing name: {company_data}")
                    
            except Exception as e:
                logger.error(f"Error saving company/contact record: {e}")
                continue
        
        return {
            'companies_saved': companies_saved,
            'contacts_saved': contacts_saved,
            'total_processed': len(results)
        }
    except Exception as e:
        raise self.retry(exc=e, countdown=60)

@app.task(bind=True)
def scrape_marketplaces(self, marketplace_url):
    try:
        scraper = MarketplaceScraper(marketplace_url)
        companies = run_async(scraper.extract_listings())
        for c in companies:
            # Filter to only include valid schema fields
            filtered_company = filter_company_data(c)
            sb.table('companies').upsert(filtered_company).execute()
        return {'count': len(companies)}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)

@app.task(bind=True)
def verify_contacts(self, contact_ids=None, batch_size=100):
    """
    Verify email and LinkedIn URL for contacts and update confidence_score and last_validated.
    
    Args:
        contact_ids: Optional list of contact IDs to verify. If None, verifies all contacts.
        batch_size: Number of contacts to process in each batch (default: 100)
        
    Returns:
        Dictionary with verification statistics
    """
    try:
        verified_count = 0
        error_count = 0
        
        # Fetch contacts
        if contact_ids:
            # Verify specific contacts
            query = sb.table('contacts').select('*').in_('id', contact_ids)
        else:
            # Verify all contacts
            query = sb.table('contacts').select('*')
        
        # Process in batches
        offset = 0
        while True:
            batch_query = query.range(offset, offset + batch_size - 1)
            response = batch_query.execute()
            
            if not response.data or len(response.data) == 0:
                break
            
            contacts = response.data
            logger.info(f"Processing batch of {len(contacts)} contacts (offset: {offset})")
            
            for contact in contacts:
                try:
                    # Verify contact
                    verification_result = verify_contact(contact)
                    
                    # Update contact with verification results
                    update_data = {
                        'email': verification_result['email'],
                        'linkedin_url': verification_result['linkedin_url'],
                        'confidence_score': verification_result['confidence_score'],
                        'last_validated': verification_result['last_validated']
                    }
                    
                    # Filter to only include valid schema fields
                    filtered_update = filter_contact_data(update_data)
                    
                    # Update the contact
                    sb.table('contacts').update(filtered_update).eq('id', contact['id']).execute()
                    verified_count += 1
                    
                except Exception as e:
                    logger.error(f"Error verifying contact {contact.get('id')}: {e}")
                    error_count += 1
                    continue
            
            offset += batch_size
            
            # Break if we got fewer contacts than batch_size (last batch)
            if len(contacts) < batch_size:
                break
        
        return {
            'verified_count': verified_count,
            'error_count': error_count,
            'total_processed': verified_count + error_count
        }
        
    except Exception as e:
        logger.error(f"Error in verify_contacts task: {e}")
        raise self.retry(exc=e, countdown=60)

def _process_shop_csv_impl(file_path: str, source: str = "csv_upload"):
    """
    Internal implementation of shop CSV processing (can be called directly or as Celery task).
    
    Args:
        file_path: Path to CSV or PDF file
        source: Source identifier for the companies (default: "csv_upload")
        
    Returns:
        Dictionary with processing statistics
    """
    try:
        from processors.csv_processor import process_shop_file
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Starting CSV/PDF processing: {file_path}")
        logger.info(f"{'='*60}\n")
        
        # Step 1: Process file and extract shop data
        shops = process_shop_file(file_path)
        logger.info(f"Extracted {len(shops)} shops from file")
        
        companies_saved = 0
        contacts_saved = 0
        errors = 0
        
        # Step 2: Process each shop
        for idx, shop in enumerate(shops, 1):
            try:
                shop_name = shop.get('name')
                shop_address = shop.get('address')
                
                if not shop_name:
                    logger.warning(f"Shop {idx}: Skipping - no name")
                    continue
                
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing shop {idx}/{len(shops)}: {shop_name}")
                logger.info(f"{'='*60}")
                
                # Step 1: Parse address to extract country and region
                # Log raw address first to see what we got
                logger.info(f"   Raw Address (length: {len(shop_address) if shop_address else 0}):")
                if shop_address:
                    # Show address with line breaks visible
                    address_display = shop_address.replace('\n', ' | ')
                    logger.info(f"      {address_display}")
                
                parsed_address = parse_address(shop_address) if shop_address else {}
                country = parsed_address.get('country')
                region = parsed_address.get('region')
                full_address = parsed_address.get('full_address') or shop_address
                
                logger.info(f"   Full Address (parsed):")
                if full_address:
                    # Show full address with all parts
                    address_lines = full_address.split('\n')
                    for idx, line in enumerate(address_lines, 1):
                        logger.info(f"      Part {idx}: {line}")
                if country:
                    logger.info(f"   Country: {country}")
                if region:
                    logger.info(f"   Region: {region}")
                
                # Step 2a: Find domain (use full address with country for better results)
                domain = find_domain(shop_name, full_address)
                
                # Step 2b: Create company record
                company_data = {
                    'name': shop_name,
                    'domain': domain,
                    'source': source,
                }
                
                # Add country and region from parsed address
                if country:
                    company_data['country'] = country
                if region:
                    company_data['region'] = region
                
                # Enrich company if domain found
                if domain:
                    enriched = enrich_company(domain)
                    for key, value in enriched.items():
                        if value and not company_data.get(key):
                            company_data[key] = value
                
                # Filter to only include valid schema fields
                filtered_company_data = filter_company_data(company_data)
                
                # Save/upsert company
                company_response = sb.table('companies').upsert(filtered_company_data).execute()
                
                # Get company_id
                company_id = None
                if company_response.data and len(company_response.data) > 0:
                    company_id = company_response.data[0].get('id')
                    companies_saved += 1
                else:
                    # Fetch by domain or name
                    if domain:
                        fetch_response = sb.table('companies').select('id').eq('domain', domain).limit(1).execute()
                    else:
                        fetch_response = sb.table('companies').select('id').eq('name', shop_name).limit(1).execute()
                    
                    if fetch_response.data and len(fetch_response.data) > 0:
                        company_id = fetch_response.data[0].get('id')
                        companies_saved += 1
                    else:
                        logger.warning(f"Could not get company_id for: {shop_name}")
                        errors += 1
                        continue
                
                # Step 2c: Find emails if domain exists
                if domain and company_id:
                    logger.info(f"Finding emails for domain: {domain}")
                    email_results = find_emails(domain, shop_name, verify=True)
                    
                    # Save contacts for each found email
                    for email, score in email_results[:5]:  # Limit to top 5 emails per company
                        contact_data = {
                            'company_id': company_id,
                            'name': None,  # We don't have contact names from CSV
                            'email': email,
                            'confidence_score': score,
                        }
                        
                        # Verify the contact to get full verification
                        verification_result = verify_contact(contact_data)
                        contact_data.update({
                            'email': verification_result['email'],
                            'confidence_score': verification_result['confidence_score'],
                            'last_validated': verification_result['last_validated']
                        })
                        
                        # Filter to only include valid schema fields
                        filtered_contact_data = filter_contact_data(contact_data)
                        
                        # Save contact
                        sb.table('contacts').upsert(filtered_contact_data).execute()
                        contacts_saved += 1
                        logger.info(f"  ✓ Saved contact: {email} (score: {score:.2f})")
                else:
                    logger.warning(f"No domain found for {shop_name}, skipping email search")
                
                logger.info(f"✅ Completed shop {idx}/{len(shops)}: {shop_name}")
                
            except Exception as e:
                logger.error(f"Error processing shop {idx} ({shop.get('name', 'unknown')}): {e}")
                errors += 1
                continue
        
        result = {
            'total_shops': len(shops),
            'companies_saved': companies_saved,
            'contacts_saved': contacts_saved,
            'errors': errors
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Processing complete!")
        logger.info(f"   Total shops: {result['total_shops']}")
        logger.info(f"   Companies saved: {result['companies_saved']}")
        logger.info(f"   Contacts saved: {result['contacts_saved']}")
        logger.info(f"   Errors: {result['errors']}")
        logger.info(f"{'='*60}\n")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in process_shop_csv: {e}")
        raise


@app.task(bind=True, max_retries=3)
def process_shop_csv(self, file_path: str, source: str = "csv_upload"):
    """
    Celery task wrapper for processing shop CSV files.
    
    Args:
        file_path: Path to CSV or PDF file
        source: Source identifier for the companies (default: "csv_upload")
        
    Returns:
        Dictionary with processing statistics
    """
    try:
        return _process_shop_csv_impl(file_path, source)
    except Exception as e:
        logger.error(f"Error in process_shop_csv task: {e}")
        raise self.retry(exc=e, countdown=60)
