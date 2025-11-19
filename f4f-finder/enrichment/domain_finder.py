"""
Domain finder module for finding website domains from company names and addresses.
Uses multiple strategies to find the most likely domain.
"""
import re
import httpx
from typing import Optional, Tuple
from urllib.parse import urlparse
from utils.logger import logger
import socket


def normalize_domain(domain: str) -> str:
    """
    Normalize a domain by removing protocol, www, and trailing slashes.
    
    Args:
        domain: Domain string (can be URL or just domain)
        
    Returns:
        Normalized domain string
    """
    if not domain:
        return ""
    
    # Remove protocol
    domain = re.sub(r'^https?://', '', domain)
    # Remove www.
    domain = re.sub(r'^www\.', '', domain)
    # Remove trailing slashes and paths
    domain = domain.split('/')[0]
    # Remove trailing dots
    domain = domain.rstrip('.')
    # Convert to lowercase
    domain = domain.lower().strip()
    
    return domain


def check_domain_exists(domain: str) -> bool:
    """
    Check if domain exists by performing DNS lookup.
    
    Args:
        domain: Domain name to check
        
    Returns:
        True if domain exists, False otherwise
    """
    try:
        socket.gethostbyname(domain)
        return True
    except (socket.gaierror, socket.herror):
        return False


def check_domain_active(domain: str) -> bool:
    """
    Check if domain is active by attempting HTTP/HTTPS connection.
    
    Args:
        domain: Domain name to check
        
    Returns:
        True if domain is active, False otherwise
    """
    try:
        for protocol in ['https', 'http']:
            try:
                url = f"{protocol}://{domain}"
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(url, follow_redirects=True)
                    if response.status_code < 500:
                        return True
            except (httpx.RequestError, httpx.TimeoutException):
                continue
        return False
    except Exception:
        return False


def generate_domain_candidates(company_name: str, address: Optional[str] = None) -> list:
    """
    Generate potential domain candidates from company name and address.
    
    Args:
        company_name: Company name
        address: Optional address (can contain city, state, etc.)
        
    Returns:
        List of potential domain strings
    """
    candidates = []
    
    if not company_name:
        return candidates
    
    # Clean company name
    name = company_name.strip()
    
    # Remove common business suffixes and clean up
    suffixes = ['inc', 'llc', 'ltd', 'corp', 'corporation', 'company', 'co', 'shop', 'store', 'retail']
    name_clean = name.lower()
    for suffix in suffixes:
        # Remove suffix if at end
        pattern = r'\b' + re.escape(suffix) + r'\.?$'
        name_clean = re.sub(pattern, '', name_clean, flags=re.IGNORECASE)
    
    name_clean = name_clean.strip()
    
    # Strategy 1: Direct company name as domain
    # Remove special characters, spaces become nothing or hyphens
    domain_variants = [
        re.sub(r'[^a-z0-9]', '', name_clean),  # No separators
        re.sub(r'[^a-z0-9]', '-', name_clean),  # Hyphens
        re.sub(r'[^a-z0-9]', '', name_clean).replace(' ', ''),  # Spaces removed
    ]
    
    # Strategy 2: Extract key words from company name
    words = re.findall(r'\b\w+\b', name_clean)
    if len(words) > 1:
        # First word
        domain_variants.append(words[0])
        # First two words combined
        domain_variants.append(''.join(words[:2]))
        domain_variants.append('-'.join(words[:2]))
        # All words combined
        domain_variants.append(''.join(words))
        domain_variants.append('-'.join(words))
    
    # Strategy 3: If address provided, extract useful parts
    if address:
        # Handle multi-line addresses
        address_lines = [line.strip() for line in address.split('\n') if line.strip()]
        address_combined = ', '.join(address_lines)
        address_parts = [part.strip() for part in address_combined.split(',')]
        
        # Extract city (usually second-to-last or third-to-last part)
        if len(address_parts) >= 2:
            # Try to find city (skip "Attn:" lines, street addresses with numbers)
            for part in reversed(address_parts[-3:]):
                part_clean = part.strip().lower()
                # Skip if it's a country name, state code, or ZIP code
                if (not re.search(r'\d{5}', part_clean) and 
                    len(part_clean) > 2 and 
                    part_clean not in ['us', 'usa', 'uk', 'ca', 'mx', 'gt'] and
                    not part_clean.startswith('attn')):
                    city_clean = re.sub(r'[^a-z0-9]', '', part_clean)
                    if city_clean and len(city_clean) > 2:
                        domain_variants.append(f"{city_clean}{name_clean}")
                        domain_variants.append(f"{city_clean}-{name_clean}")
                        break
    
    # Remove duplicates and empty strings
    candidates = list(set([c for c in domain_variants if c and len(c) > 2]))
    
    # Add common TLDs
    tlds = ['com', 'net', 'org', 'co', 'io', 'biz']
    final_candidates = []
    for candidate in candidates:
        for tld in tlds:
            final_candidates.append(f"{candidate}.{tld}")
    
    return final_candidates[:20]  # Limit to top 20 candidates


def find_domain_by_search(company_name: str, address: Optional[str] = None) -> Optional[str]:
    """
    Find domain by searching Google (requires API key or web scraping).
    This is a placeholder - you can integrate with Google Custom Search API.
    
    Args:
        company_name: Company name
        address: Optional address
        
    Returns:
        Domain if found, None otherwise
    """
    # TODO: Implement Google Custom Search API integration
    # For now, return None - we'll rely on candidate checking
    return None


def find_domain(company_name: str, address: Optional[str] = None) -> Optional[str]:
    """
    Find website domain for a company using multiple strategies.
    
    Args:
        company_name: Company name
        address: Optional address
        
    Returns:
        Domain if found, None otherwise
    """
    if not company_name:
        logger.warning("No company name provided for domain finding")
        return None
    
    logger.info(f"\n🔍 Finding domain for: {company_name}")
    if address:
        logger.info(f"   Address: {address}")
    
    # Strategy 1: Generate candidates and check them
    candidates = generate_domain_candidates(company_name, address)
    logger.info(f"   Generated {len(candidates)} domain candidates")
    
    # Check each candidate
    for candidate in candidates:
        logger.info(f"   Checking: {candidate}")
        if check_domain_exists(candidate):
            logger.info(f"   ✓ Domain exists: {candidate}")
            if check_domain_active(candidate):
                logger.info(f"   ✓ Domain is active: {candidate}")
                normalized = normalize_domain(candidate)
                logger.info(f"   ✅ Found domain: {normalized}")
                return normalized
            else:
                logger.info(f"   ⚠ Domain exists but not active: {candidate}")
        else:
            logger.info(f"   ✗ Domain does not exist: {candidate}")
    
    # Strategy 2: Try Google search (if implemented)
    domain = find_domain_by_search(company_name, address)
    if domain:
        normalized = normalize_domain(domain)
        logger.info(f"   ✅ Found domain via search: {normalized}")
        return normalized
    
    logger.warning(f"   ✗ Could not find domain for: {company_name}")
    return None

