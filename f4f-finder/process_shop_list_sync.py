"""
Synchronous version of shop list processor (no Celery required).
This version runs directly without Celery, which avoids Windows compatibility issues.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from utils.logger import logger

# Load environment variables
load_dotenv()


def process_shop_file_sync(file_path: str, source: str = "csv_upload", use_cache: bool = True):
    """
    Process shop file synchronously (direct execution, no Celery).
    
    Args:
        file_path: Path to CSV or PDF file
        source: Source identifier for the companies (default: "csv_upload")
        use_cache: Whether to use cache if available (default: True)
    """
    from processors.csv_processor import process_shop_file
    from enrichment.domain_finder import find_domain
    from enrichment.email_finder import find_emails
    from enrichment.clearbit_integration import enrich_company
    from enrichment.contact_verification import verify_contact
    from supabase_client import sb
    
    # Valid fields for companies table
    VALID_COMPANY_FIELDS = {
        'name', 'domain', 'country', 'region', 'type', 'source', 
        'brand_focus', 'status', 'freshness_timestamp'
    }
    
    # Valid fields for contacts table
    VALID_CONTACT_FIELDS = {
        'company_id', 'name', 'email', 'phone', 'title', 
        'linkedin_url', 'confidence_score', 'last_validated'
    }
    
    def filter_company_data(data):
        return {k: v for k, v in data.items() if k in VALID_COMPANY_FIELDS}
    
    def filter_contact_data(data):
        return {k: v for k, v in data.items() if k in VALID_CONTACT_FIELDS}
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Starting CSV/PDF processing: {file_path}")
    logger.info(f"{'='*60}\n")
    
    # Step 1: Process file and extract shop data
    shops = process_shop_file(file_path, use_cache=use_cache)
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
            
            # Step 2a: Find domain
            domain = find_domain(shop_name, shop_address)
            
            # Step 2b: Create company record
            company_data = {
                'name': shop_name,
                'domain': domain,
                'source': source,
            }
            
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
            import traceback
            logger.error(traceback.format_exc())
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


def main():
    """
    Main function to process shop list synchronously.
    """
    # Default file path from user's request
    default_file = "D://shop_list.pdf"
    
    # Parse command line arguments
    file_path = default_file
    force_re_extract = False
    
    for arg in sys.argv[1:]:
        if arg == '--force' or arg == '-f':
            force_re_extract = True
        elif not arg.startswith('-'):
            file_path = arg
    
    # Check if file exists
    if not Path(file_path).exists():
        logger.error(f"File not found: {file_path}")
        logger.info("Usage: python process_shop_list_sync.py [path_to_file] [--force]")
        logger.info(f"  --force, -f: Force re-extraction (ignore cache)")
        logger.info(f"Default file: {default_file}")
        sys.exit(1)
    
    logger.info(f"Processing shop list from: {file_path}")
    logger.info("Running synchronously (no Celery required)")
    if force_re_extract:
        logger.info("⚠️  Force re-extraction enabled (cache will be ignored)")
    
    try:
        use_cache = not force_re_extract
        result = process_shop_file_sync(file_path, source="csv_upload", use_cache=use_cache)
        logger.info("\n" + "="*60)
        logger.info("Processing Results:")
        logger.info(f"  Total shops: {result['total_shops']}")
        logger.info(f"  Companies saved: {result['companies_saved']}")
        logger.info(f"  Contacts saved: {result['contacts_saved']}")
        logger.info(f"  Errors: {result['errors']}")
        logger.info("="*60)
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

