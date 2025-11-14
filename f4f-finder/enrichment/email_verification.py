import re
from typing import Optional, Tuple
from utils.logger import logger

# Email regex pattern for basic validation
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Disposable email domains (common ones)
DISPOSABLE_EMAIL_DOMAINS = {
    'tempmail.com', '10minutemail.com', 'guerrillamail.com',
    'mailinator.com', 'throwaway.email', 'temp-mail.org'
}

def verify_email(email: Optional[str]) -> Tuple[Optional[str], float]:
    """
    Verify email address and return a confidence score.
    
    Args:
        email: Email address to verify
        
    Returns:
        Tuple of (email, score) where:
        - email: The email if valid, None if invalid
        - score: Confidence score from 0.0 to 1.0
    """
    if not email:
        return None, 0.0
    
    email = email.strip().lower()
    
    # Basic format validation
    if not EMAIL_PATTERN.match(email):
        logger.debug(f"Email {email} failed format validation")
        return None, 0.0
    
    score = 0.5  # Start with base score for valid format
    
    # Check for disposable email domains
    domain = email.split('@')[1] if '@' in email else ''
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        logger.debug(f"Email {email} is from disposable domain")
        return email, 0.2  # Low score for disposable emails
    
    # Additional validation checks
    # Check for common typos or suspicious patterns
    if '..' in email or email.startswith('.') or email.endswith('.'):
        logger.debug(f"Email {email} has suspicious pattern")
        return email, 0.3
    
    # Check domain has valid TLD
    parts = domain.split('.')
    if len(parts) < 2:
        return None, 0.0
    
    # Valid format, not disposable, no suspicious patterns
    score = 0.8
    
    # TODO: Add API-based verification (e.g., ZeroBounce, Hunter.io, etc.)
    # For now, we return a good score for well-formatted emails
    
    return email, score
