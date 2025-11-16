"""
Contact verification module for verifying email and LinkedIn URL.
Calculates confidence scores and updates contacts in the database.
"""
import re
from typing import Dict, Optional
from datetime import datetime
from enrichment.email_verification import verify_email
from enrichment.linkedin_verification import verify_linkedin_url
from utils.logger import logger

# Decision-maker role keywords (case-insensitive matching)
DECISION_MAKER_KEYWORDS = {
    'buyer', 'purchasing', 'procurement', 'acquisition',
    'owner', 'founder', 'co-founder', 'cofounder',
    'manager', 'director', 'head', 'chief', 'executive',
    'vp', 'vice president', 'president', 'ceo', 'cfo', 'cto', 'coo',
    'lead', 'senior', 'principal', 'partner',
    'decision', 'decision maker', 'decision-maker'
}


def is_decision_maker(title: Optional[str]) -> bool:
    """
    Check if a job title matches decision-maker roles.
    
    Args:
        title: Job title to check
        
    Returns:
        True if title matches decision-maker role, False otherwise
    """
    if not title:
        return False
    
    # Normalize title for matching
    title_lower = title.lower().strip()
    
    # Check if any decision-maker keyword is in the title
    for keyword in DECISION_MAKER_KEYWORDS:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, title_lower):
            logger.info(f"  ✓ Title '{title}' matches decision-maker keyword: '{keyword}'")
            return True
    
    logger.info(f"  ✗ Title '{title}' does not match decision-maker role")
    return False


def calculate_confidence_score(email_score: float, linkedin_score: float, 
                               has_email: bool, has_linkedin: bool,
                               is_decision_maker_role: bool = False) -> float:
    """
    Calculate overall confidence score based on email, LinkedIn verification, and role.
    
    Args:
        email_score: Email verification score (0.0-1.0)
        linkedin_score: LinkedIn URL verification score (0.0-1.0)
        has_email: Whether email exists
        has_linkedin: Whether LinkedIn URL exists
        is_decision_maker_role: Whether job title matches decision-maker role
        
    Returns:
        Overall confidence score (0.0-1.0)
    """
    logger.info("\n📊 Calculating overall confidence score...")
    
    if not has_email and not has_linkedin:
        logger.info("  ✗ No email or LinkedIn URL available")
        logger.info("    Final confidence score: 0.00")
        return 0.0
    
    # Base score from email and LinkedIn
    if has_email and has_linkedin:
        # Both present: weighted average (email 60%, LinkedIn 40%)
        base_score = (email_score * 0.6) + (linkedin_score * 0.4)
        logger.info(f"  ✓ Both email and LinkedIn present")
        logger.info(f"    Email score: {email_score:.2f} (weight: 60%)")
        logger.info(f"    LinkedIn score: {linkedin_score:.2f} (weight: 40%)")
        logger.info(f"    Base score: {base_score:.2f} = ({email_score:.2f} × 0.6) + ({linkedin_score:.2f} × 0.4)")
    elif has_email:
        # Only email: use email score
        base_score = email_score
        logger.info(f"  ✓ Only email present")
        logger.info(f"    Base score: {base_score:.2f} (email score)")
    else:
        # Only LinkedIn: use LinkedIn score
        base_score = linkedin_score
        logger.info(f"  ✓ Only LinkedIn present")
        logger.info(f"    Base score: {base_score:.2f} (LinkedIn score)")
    
    # Boost score if it's a decision-maker role
    if is_decision_maker_role:
        # Add 0.1 boost for decision-maker roles (capped at 1.0)
        old_score = base_score
        base_score = min(base_score + 0.1, 1.0)
        logger.info(f"  ✓ Decision-maker role boost applied")
        logger.info(f"    Score: {base_score:.2f} = {old_score:.2f} + 0.10 (decision-maker boost)")
    else:
        logger.info(f"  ✗ No decision-maker role boost")
        logger.info(f"    Score: {base_score:.2f} (no boost)")
    
    logger.info(f"\n✅ Final confidence score: {base_score:.2f}")
    
    return base_score


def verify_contact(contact: Dict) -> Dict:
    """
    Verify a single contact's email and LinkedIn URL.
    Performs multiple checks:
    1. Email format, domain existence, domain activity, email server reachability
    2. LinkedIn URL format and name/title matching
    3. Job title decision-maker role matching
    
    Args:
        contact: Contact dictionary with email, linkedin_url, name, and title fields
        
    Returns:
        Dictionary with verification results:
        {
            'email': verified_email or None,
            'linkedin_url': verified_linkedin_url or None,
            'confidence_score': float,
            'last_validated': datetime string
        }
    """
    contact_id = contact.get('id', 'unknown')
    email = contact.get('email')
    linkedin_url = contact.get('linkedin_url')
    person_name = contact.get('name')
    person_title = contact.get('title')
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🔍 Verifying Contact ID: {contact_id}")
    if person_name:
        logger.info(f"   Name: {person_name}")
    if person_title:
        logger.info(f"   Title: {person_title}")
    logger.info(f"{'='*60}")
    
    # Verify email (includes format, domain existence, domain activity, email server checks)
    verified_email, email_score = verify_email(email)
    has_email = verified_email is not None
    
    # Verify LinkedIn URL (includes format and name/title matching)
    verified_linkedin_url, linkedin_score = verify_linkedin_url(
        linkedin_url, 
        person_name=person_name,
        person_title=person_title
    )
    has_linkedin = verified_linkedin_url is not None
    
    # Check if job title matches decision-maker role
    if person_title:
        logger.info(f"\n💼 Checking decision-maker role for title: '{person_title}'")
    is_decision_maker_role = is_decision_maker(person_title)
    
    # Calculate overall confidence score
    confidence_score = calculate_confidence_score(
        email_score, linkedin_score, has_email, has_linkedin,
        is_decision_maker_role=is_decision_maker_role
    )
    
    result = {
        'email': verified_email,
        'linkedin_url': verified_linkedin_url,
        'confidence_score': round(confidence_score, 2),
        'last_validated': datetime.utcnow().isoformat()
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ Verification Complete for Contact ID: {contact_id}")
    logger.info(f"   Email: {verified_email or 'N/A'} (score: {email_score:.2f})")
    logger.info(f"   LinkedIn: {verified_linkedin_url or 'N/A'} (score: {linkedin_score:.2f})")
    logger.info(f"   Decision-maker: {is_decision_maker_role}")
    logger.info(f"   Final Confidence Score: {confidence_score:.2f}")
    logger.info(f"{'='*60}\n")
    
    return result

