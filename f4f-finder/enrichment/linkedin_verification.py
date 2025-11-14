import re
from typing import Optional, Tuple
from urllib.parse import urlparse
from utils.logger import logger

# LinkedIn URL patterns
LINKEDIN_PROFILE_PATTERN = re.compile(
    r'^https?://(www\.)?linkedin\.com/(in|pub|profile)/[a-zA-Z0-9_-]+/?$'
)
LINKEDIN_COMPANY_PATTERN = re.compile(
    r'^https?://(www\.)?linkedin\.com/company/[a-zA-Z0-9_-]+/?$'
)

def verify_linkedin_url(linkedin_url: Optional[str]) -> Tuple[Optional[str], float]:
    """
    Verify LinkedIn URL and return a confidence score.
    
    Args:
        linkedin_url: LinkedIn URL to verify
        
    Returns:
        Tuple of (url, score) where:
        - url: The URL if valid, None if invalid
        - score: Confidence score from 0.0 to 1.0
    """
    if not linkedin_url:
        return None, 0.0
    
    linkedin_url = linkedin_url.strip()
    
    # Basic format validation
    if not (linkedin_url.startswith('http://') or linkedin_url.startswith('https://')):
        # Try to fix common issues
        if linkedin_url.startswith('linkedin.com') or linkedin_url.startswith('www.linkedin.com'):
            linkedin_url = 'https://' + linkedin_url
        else:
            logger.debug(f"LinkedIn URL {linkedin_url} missing protocol")
            return None, 0.0
    
    # Parse URL
    try:
        parsed = urlparse(linkedin_url)
        if 'linkedin.com' not in parsed.netloc.lower():
            logger.debug(f"LinkedIn URL {linkedin_url} is not a LinkedIn domain")
            return None, 0.0
    except Exception as e:
        logger.debug(f"Error parsing LinkedIn URL {linkedin_url}: {e}")
        return None, 0.0
    
    score = 0.5  # Start with base score for valid format
    
    # Check if it matches LinkedIn profile or company pattern
    if LINKEDIN_PROFILE_PATTERN.match(linkedin_url) or LINKEDIN_COMPANY_PATTERN.match(linkedin_url):
        score = 0.8  # Good score for well-formatted LinkedIn URL
    else:
        # Still a LinkedIn URL but might be malformed
        score = 0.4
        logger.debug(f"LinkedIn URL {linkedin_url} doesn't match standard pattern")
    
    # Optional: Try to verify URL is accessible (be careful with rate limiting)
    # This could be done asynchronously or in batches
    # For now, we'll rely on format validation
    
    return linkedin_url, score

