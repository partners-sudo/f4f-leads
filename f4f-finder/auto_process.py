"""
Automated shop data processing with scheduling.
Run this script to automatically process shop lists on a schedule.
"""
import schedule
import time
import sys
from pathlib import Path
from dotenv import load_dotenv
from utils.logger import logger
from tasks import _process_shop_csv_impl

load_dotenv()


def process_shop_file(file_path: str):
    """
    Process a shop file and return results.
    """
    if not Path(file_path).exists():
        logger.error(f"File not found: {file_path}")
        return None
    
    logger.info(f"Starting automated processing of: {file_path}")
    try:
        result = _process_shop_csv_impl(file_path, source="automated_csv_upload")
        logger.info(f"✅ Processing complete: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Error processing file: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def main():
    """
    Main function to set up automated processing.
    """
    # Default file path
    default_file = "D://shop_list.pdf"
    
    # Get file path from command line or use default
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_file
    
    # Check if file exists
    if not Path(file_path).exists():
        logger.error(f"File not found: {file_path}")
        logger.info("Usage: python auto_process.py [path_to_file] [schedule]")
        logger.info("Schedule options: daily, weekly, hourly, or time like '02:00'")
        sys.exit(1)
    
    # Get schedule from command line or use default (daily at 2 AM)
    if len(sys.argv) > 2:
        schedule_type = sys.argv[2]
        if schedule_type == "daily":
            schedule.every().day.at("02:00").do(process_shop_file, file_path)
            logger.info(f"Scheduled daily processing at 2:00 AM for: {file_path}")
        elif schedule_type == "weekly":
            schedule.every().monday.at("02:00").do(process_shop_file, file_path)
            logger.info(f"Scheduled weekly processing (Mondays at 2:00 AM) for: {file_path}")
        elif schedule_type == "hourly":
            schedule.every().hour.do(process_shop_file, file_path)
            logger.info(f"Scheduled hourly processing for: {file_path}")
        elif ":" in schedule_type:
            # Time format like "02:00"
            schedule.every().day.at(schedule_type).do(process_shop_file, file_path)
            logger.info(f"Scheduled daily processing at {schedule_type} for: {file_path}")
        else:
            logger.error(f"Unknown schedule type: {schedule_type}")
            sys.exit(1)
    else:
        # Default: daily at 2 AM
        schedule.every().day.at("02:00").do(process_shop_file, file_path)
        logger.info(f"Scheduled daily processing at 2:00 AM for: {file_path}")
    
    logger.info("="*60)
    logger.info("Automated processing started. Press Ctrl+C to stop.")
    logger.info("="*60)
    
    # Run immediately once, then on schedule
    logger.info("Running initial processing...")
    process_shop_file(file_path)
    
    # Keep running and check schedule
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("\nStopping automated processing...")


if __name__ == "__main__":
    main()

