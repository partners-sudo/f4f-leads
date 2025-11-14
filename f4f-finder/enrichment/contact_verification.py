"""
Contact verification module for verifying email and LinkedIn URL.
Calculates confidence scores and updates contacts in the database.
"""
from typing import Dict, Optional
from datetime import datetime
from enrichment.email_verification import verify_email
from enrichment.linkedin_verification import verify_linkedin_url
from utils.logger import logger


def calculate_confidence_score(email_score: float, linkedin_score: float, 
                               has_email: bool, has_linkedin: bool) -> float:
    """
    Calculate overall confidence score based on email and LinkedIn verification.
    
    Args:
        email_score: Email verification score (0.0-1.0)
        linkedin_score: LinkedIn URL verification score (0.0-1.0)
        has_email: Whether email exists
        has_linkedin: Whether LinkedIn URL exists
        
    Returns:
        Overall confidence score (0.0-1.0)
    """
    if not has_email and not has_linkedin:
        return 0.0
    
    if has_email and has_linkedin:
        # Both present: weighted average (email 60%, LinkedIn 40%)
        return (email_score * 0.6) + (linkedin_score * 0.4)
    elif has_email:
        # Only email: use email score
        return email_score
    else:
        # Only LinkedIn: use LinkedIn score
        return linkedin_score


def verify_contact(contact: Dict) -> Dict:
    """
    Verify a single contact's email and LinkedIn URL.
    
    Args:
        contact: Contact dictionary with email and linkedin_url fields
        
    Returns:
        Dictionary with verification results:
        {
            'email': verified_email or None,
            'linkedin_url': verified_linkedin_url or None,
            'confidence_score': float,
            'last_validated': datetime string
        }
    """
    email = contact.get('email')
    linkedin_url = contact.get('linkedin_url')
    
    # Verify email
    verified_email, email_score = verify_email(email)
    has_email = verified_email is not None
    
    # Verify LinkedIn URL
    verified_linkedin_url, linkedin_score = verify_linkedin_url(linkedin_url)
    has_linkedin = verified_linkedin_url is not None
    
    # Calculate overall confidence score
    confidence_score = calculate_confidence_score(
        email_score, linkedin_score, has_email, has_linkedin
    )
    
    result = {
        'email': verified_email,
        'linkedin_url': verified_linkedin_url,
        'confidence_score': round(confidence_score, 2),
        'last_validated': datetime.utcnow().isoformat()
    }
    
    logger.debug(f"Verified contact: email_score={email_score:.2f}, "
                f"linkedin_score={linkedin_score:.2f}, "
                f"confidence={confidence_score:.2f}")
    
    return result

