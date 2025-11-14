#!/usr/bin/env python3
"""
Standalone command to verify contacts' email and LinkedIn URL.
This script can be run directly to verify all contacts or specific ones.

Usage:
    python verify_contacts.py                    # Verify all contacts
    python verify_contacts.py --contact-ids id1,id2,id3  # Verify specific contacts
    python verify_contacts.py --batch-size 50    # Use custom batch size
"""
import argparse
import sys
from supabase_client import sb
from enrichment.contact_verification import verify_contact
from utils.logger import logger

# Valid fields for contacts table (excluding auto-generated fields)
VALID_CONTACT_FIELDS = {
    'company_id', 'name', 'email', 'phone', 'title', 
    'linkedin_url', 'confidence_score', 'last_validated'
}

def filter_contact_data(data):
    """Filter contact data to only include valid schema fields."""
    return {k: v for k, v in data.items() if k in VALID_CONTACT_FIELDS}


def verify_contacts_command(contact_ids=None, batch_size=100):
    """
    Verify email and LinkedIn URL for contacts and update confidence_score and last_validated.
    
    Args:
        contact_ids: Optional list of contact IDs to verify. If None, verifies all contacts.
        batch_size: Number of contacts to process in each batch (default: 100)
        
    Returns:
        Dictionary with verification statistics
    """
    verified_count = 0
    error_count = 0
    
    try:
        # Fetch contacts
        if contact_ids:
            # Verify specific contacts
            logger.info(f"Verifying {len(contact_ids)} specific contacts")
            query = sb.table('contacts').select('*').in_('id', contact_ids)
        else:
            # Verify all contacts
            logger.info("Verifying all contacts")
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
                    
                    if verified_count % 10 == 0:
                        logger.info(f"Verified {verified_count} contacts so far...")
                    
                except Exception as e:
                    logger.error(f"Error verifying contact {contact.get('id')}: {e}")
                    error_count += 1
                    continue
            
            offset += batch_size
            
            # Break if we got fewer contacts than batch_size (last batch)
            if len(contacts) < batch_size:
                break
        
        logger.info(f"Verification complete: {verified_count} verified, {error_count} errors")
        return {
            'verified_count': verified_count,
            'error_count': error_count,
            'total_processed': verified_count + error_count
        }
        
    except Exception as e:
        logger.error(f"Error in verify_contacts_command: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Verify contacts\' email and LinkedIn URL and update confidence scores'
    )
    parser.add_argument(
        '--contact-ids',
        type=str,
        help='Comma-separated list of contact IDs to verify (if not provided, verifies all)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of contacts to process in each batch (default: 100)'
    )
    
    args = parser.parse_args()
    
    contact_ids = None
    if args.contact_ids:
        contact_ids = [id.strip() for id in args.contact_ids.split(',')]
    
    try:
        result = verify_contacts_command(contact_ids=contact_ids, batch_size=args.batch_size)
        print(f"\nVerification Results:")
        print(f"  Verified: {result['verified_count']}")
        print(f"  Errors: {result['error_count']}")
        print(f"  Total: {result['total_processed']}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

