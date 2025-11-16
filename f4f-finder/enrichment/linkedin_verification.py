import re
from typing import Optional, Tuple
from urllib.parse import urlparse
from utils.logger import logger

# LinkedIn URL patterns
LINKEDIN_PROFILE_PATTERN = re.compile(
    r'^https?://(www\.)?linkedin\.com/(in|pub|profile)/([a-zA-Z0-9_-]+)/?$'
)
LINKEDIN_COMPANY_PATTERN = re.compile(
    r'^https?://(www\.)?linkedin\.com/company/[a-zA-Z0-9_-]+/?$'
)


def extract_linkedin_slug(linkedin_url: str) -> Optional[str]:
    """
    Extract the slug (username part) from a LinkedIn profile URL.
    
    Args:
        linkedin_url: LinkedIn profile URL
        
    Returns:
        The slug/username from the URL, or None if not found
    """
    match = LINKEDIN_PROFILE_PATTERN.match(linkedin_url)
    if match:
        return match.group(3)
    return None


def normalize_name(name: Optional[str]) -> str:
    """
    Normalize a name for comparison by converting to lowercase and removing special characters.
    
    Args:
        name: Name to normalize
        
    Returns:
        Normalized name string
    """
    if not name:
        return ""
    # Convert to lowercase, remove extra spaces, and remove special characters except hyphens
    normalized = re.sub(r'[^a-z0-9\s-]', '', name.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def check_name_match(linkedin_url: str, person_name: Optional[str]) -> bool:
    """
    Check if LinkedIn URL slug matches the person's name.
    
    Args:
        linkedin_url: LinkedIn profile URL
        person_name: Person's name to match against
        
    Returns:
        True if name matches, False otherwise
    """
    if not person_name:
        return False
    
    slug = extract_linkedin_slug(linkedin_url)
    if not slug:
        return False
    
    # Normalize both for comparison
    normalized_slug = normalize_name(slug.replace('-', ' ').replace('_', ' '))
    normalized_name = normalize_name(person_name)
    
    if not normalized_slug or not normalized_name:
        return False
    
    # Split into words
    slug_words = set(normalized_slug.split())
    name_words = set(normalized_name.split())
    
    # Check if there's significant overlap (at least 2 words match, or if single word, exact match)
    if len(slug_words) == 1 and len(name_words) == 1:
        return slug_words == name_words
    
    # For multi-word names, check if at least 2 words match
    common_words = slug_words.intersection(name_words)
    # Filter out common words that don't help with matching
    common_words = {w for w in common_words if len(w) > 2}
    
    return len(common_words) >= 2 or (len(common_words) >= 1 and len(name_words) <= 2)


def check_title_match(linkedin_url: str, person_title: Optional[str]) -> bool:
    """
    Check if LinkedIn URL might match the person's title (indirect check).
    This is a weaker check since LinkedIn URLs don't contain titles,
    but we can verify the URL format is valid for a profile.
    
    Args:
        linkedin_url: LinkedIn profile URL
        person_title: Person's title (not directly used, but URL format validation)
        
    Returns:
        True if URL is a valid profile URL format
    """
    # Since LinkedIn URLs don't contain titles, we just verify it's a profile URL
    # The presence of a title in the contact data suggests it's a person, not a company
    if person_title and LINKEDIN_PROFILE_PATTERN.match(linkedin_url):
        return True
    return False


def verify_linkedin_url(linkedin_url: Optional[str], 
                        person_name: Optional[str] = None,
                        person_title: Optional[str] = None) -> Tuple[Optional[str], float]:
    """
    Verify LinkedIn URL and return a confidence score.
    Also checks if the URL matches the person's name or title if provided.
    
    Args:
        linkedin_url: LinkedIn URL to verify
        person_name: Optional person's name to match against URL
        person_title: Optional person's title (for validation context)
        
    Returns:
        Tuple of (url, score) where:
        - url: The URL if valid, None if invalid
        - score: Confidence score from 0.0 to 1.0
    """
    if not linkedin_url:
        logger.info("LinkedIn verification: No LinkedIn URL provided")
        return None, 0.0
    
    linkedin_url = linkedin_url.strip()
    logger.info(f"\n🔗 Verifying LinkedIn URL: {linkedin_url}")
    
    # Basic format validation
    logger.info("  ✓ Checking LinkedIn URL format...")
    if not (linkedin_url.startswith('http://') or linkedin_url.startswith('https://')):
        # Try to fix common issues
        if linkedin_url.startswith('linkedin.com') or linkedin_url.startswith('www.linkedin.com'):
            linkedin_url = 'https://' + linkedin_url
            logger.info(f"  ✓ Fixed missing protocol, URL: {linkedin_url}")
        else:
            logger.info(f"  ✗ LinkedIn URL '{linkedin_url}' missing protocol")
            return None, 0.0
    
    # Parse URL
    try:
        parsed = urlparse(linkedin_url)
        if 'linkedin.com' not in parsed.netloc.lower():
            logger.info(f"  ✗ LinkedIn URL '{linkedin_url}' is not a LinkedIn domain")
            return None, 0.0
    except Exception as e:
        logger.info(f"  ✗ Error parsing LinkedIn URL '{linkedin_url}': {e}")
        return None, 0.0
    
    logger.info("  ✓ LinkedIn URL format is valid")
    score = 0.4  # Start with base score for valid format
    logger.info(f"    Score: {score:.2f} (valid format)")
    
    # Check if it matches LinkedIn profile or company pattern
    is_profile = LINKEDIN_PROFILE_PATTERN.match(linkedin_url)
    is_company = LINKEDIN_COMPANY_PATTERN.match(linkedin_url)
    
    if is_company:
        # Company URLs are official and legitimate, give them a high score
        score = 0.85  # High score for company URLs (they're official pages)
        logger.info(f"  ✓ URL matches LinkedIn company pattern")
        logger.info(f"    Score: {score:.2f} (company page - official and legitimate)")
    elif is_profile:
        score = 0.6  # Good score for well-formatted profile URL
        logger.info(f"  ✓ URL matches LinkedIn profile pattern")
        logger.info(f"    Score: {score:.2f} (profile pattern)")
    else:
        # Still a LinkedIn URL but might be malformed
        score = 0.3
        logger.info(f"  ⚠ LinkedIn URL '{linkedin_url}' doesn't match standard pattern")
        logger.info(f"    Score: {score:.2f} (non-standard pattern)")
    
    # Check if LinkedIn URL matches person's name (if provided) - only for profiles
    if person_name and is_profile:
        logger.info(f"  ✓ Checking if URL matches person name: '{person_name}'...")
        if check_name_match(linkedin_url, person_name):
            score += 0.3
            logger.info(f"  ✓ LinkedIn URL matches person name")
            logger.info(f"    Score: {score:.2f} (+0.30 for name match)")
        else:
            logger.info(f"  ✗ LinkedIn URL does not match person name")
            logger.info(f"    Score: {score:.2f} (no name match)")
    elif is_company:
        logger.info(f"  ✓ Company LinkedIn URL (name matching not applicable)")
    
    # Check if LinkedIn URL format matches title context (if provided) - only for profiles
    if person_title and is_profile:
        logger.info(f"  ✓ Checking title context: '{person_title}'...")
        if check_title_match(linkedin_url, person_title):
            score += 0.1
            logger.info(f"  ✓ URL is valid profile format for title")
            logger.info(f"    Score: {score:.2f} (+0.10 for title context)")
        else:
            logger.info(f"    Score: {score:.2f} (no title context match)")
    elif is_company:
        logger.info(f"  ✓ Company LinkedIn URL (title context not applicable)")
    
    # Cap score at 1.0
    score = min(score, 1.0)
    logger.info(f"  ✓ Final LinkedIn score: {score:.2f}")
    
    return linkedin_url, round(score, 2)

