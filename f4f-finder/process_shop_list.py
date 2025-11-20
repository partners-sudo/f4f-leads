"""
Main script to process shop list from PDF/CSV file.
This script processes the file, finds domains and emails, and saves to Supabase.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from utils.logger import logger
from tasks import process_shop_csv

# Load environment variables
load_dotenv()


def main():
    """
    Main function to process shop list.
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
        logger.info("Usage: python process_shop_list.py [path_to_file] [--force]")
        logger.info(f"  --force, -f: Force re-extraction (ignore cache)")
        logger.info(f"Default file: {default_file}")
        sys.exit(1)
    
    logger.info(f"Processing shop list from: {file_path}")
    if force_re_extract:
        logger.info("⚠️  Force re-extraction enabled (cache will be ignored)")
    
    # Check if Celery is configured
    redis_url = os.environ.get("REDIS_URL")
    
    # For Windows compatibility, prefer synchronous execution
    # Celery has known issues on Windows with Python 3.13
    use_celery = redis_url and os.name != 'nt'  # Don't use Celery on Windows
    
    if not use_celery:
        logger.info("Running synchronously (recommended for Windows)")
        # Run synchronously
        try:
            # Import the implementation function and call it directly
            from tasks import _process_shop_csv_impl
            # Call the function directly (not as a Celery task)
            use_cache = not force_re_extract
            result = _process_shop_csv_impl(file_path, source="csv_upload", use_cache=use_cache)
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
    else:
        # Run as Celery task (Linux/Mac only)
        logger.info("Running as Celery task...")
        task = process_shop_csv.delay(file_path, source="csv_upload")
        logger.info(f"Task ID: {task.id}")
        logger.info("Monitor task progress with: celery -A celery_app inspect active")
        logger.info("Or check results with: celery -A celery_app result <task_id>")


if __name__ == "__main__":
    main()

