import asyncio
from celery_app import app

from supabase_client import sb

from scraper.competitor_scraper import CompetitorScraper

from scraper.linkedin_scraper import LinkedInScraper

from scraper.marketplace_scraper import MarketplaceScraper

from enrichment.email_verification import verify_email

from enrichment.clearbit_integration import enrich_company

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
            c['email'] = verify_email(c.get('email'))
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
