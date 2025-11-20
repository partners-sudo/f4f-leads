"""
Domain finder module for finding website domains from company names and addresses.
Uses multiple strategies to find the most likely domain.
"""
import re
import httpx
import os
from typing import Optional, Tuple, Dict
from urllib.parse import urlparse
from utils.logger import logger
from utils.address_parser import parse_address
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


# Directory sites to filter out
DIRECTORY_SITES = [
    'yelp.com', 'facebook.com', 'tripadvisor.com', 'foursquare.com',
    'yellowpages.com', 'whitepages.com', 'superpages.com', 'dexknows.com',
    'merchantcircle.com', 'manta.com', 'bbb.org', 'angieslist.com',
    'homeadvisor.com', 'thumbtack.com', 'nextdoor.com', 'linkedin.com',
    'indeed.com', 'glassdoor.com', 'crunchbase.com', 'zoominfo.com',
    'clutch.co', 'goodfirms.co', 'trustpilot.com', 'g2.com',
    'capterra.com', 'getapp.com', 'softwareadvice.com'
]


def is_directory_site(url: str) -> bool:
    """
    Check if a URL is from a directory/review site.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is from a directory site, False otherwise
    """
    url_lower = url.lower()
    for directory in DIRECTORY_SITES:
        if directory in url_lower:
            return True
    return False


def find_domain_by_search(company_name: str, address: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Find domain by searching using Serper.dev API.
    
    Args:
        company_name: Company name
        address: Optional address (can contain city, state, country)
        
    Returns:
        Tuple of (domain, homepage_url) if found, None otherwise
    """
    api_key = os.getenv('SERPER_API_KEY')
    if not api_key:
        logger.warning("SERPER_API_KEY not found in environment variables")
        return None
    
    # Parse address to extract city and country
    city = None
    country = None
    if address:
        parsed = parse_address(address)
        city = parsed.get('city')
        country = parsed.get('country')
    
    # Build search query
    query_parts = [company_name]
    if city:
        query_parts.append(city)
    if country:
        # Convert country code to name if needed
        country_names = {
            'US': 'USA', 'CA': 'Canada', 'MX': 'Mexico', 'GB': 'UK',
            'FR': 'France', 'DE': 'Germany', 'ES': 'Spain', 'IT': 'Italy'
        }
        country_name = country_names.get(country, country)
        query_parts.append(country_name)
    
    query = ' '.join(query_parts)
    logger.info(f"   Searching Serper.dev with query: {query}")
    
    try:
        # Call Serper.dev API
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": 10  # Get top 10 results
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Extract organic results
            organic_results = data.get('organic', [])
            logger.info(f"   Found {len(organic_results)} search results")
            
            # Filter out directory sites and find best homepage candidate
            for result in organic_results:
                link = result.get('link', '')
                if not link:
                    continue
                
                # Skip directory sites
                if is_directory_site(link):
                    logger.debug(f"   Skipping directory site: {link}")
                    continue
                
                # Extract domain from URL
                try:
                    parsed_url = urlparse(link)
                    domain = parsed_url.netloc
                    if not domain:
                        continue
                    
                    # Remove www. prefix
                    domain = normalize_domain(domain)
                    
                    # Verify domain exists and is active
                    if check_domain_exists(domain) and check_domain_active(domain):
                        logger.info(f"   ✅ Found domain via search: {domain} (from {link})")
                        return (domain, link)
                except Exception as e:
                    logger.debug(f"   Error parsing URL {link}: {e}")
                    continue
            
            logger.warning(f"   No valid domain found in search results")
            return None
            
    except httpx.HTTPError as e:
        logger.error(f"   HTTP error calling Serper.dev API: {e}")
        return None
    except Exception as e:
        logger.error(f"   Error calling Serper.dev API: {e}")
        return None


def find_domain(company_name: str, address: Optional[str] = None) -> Optional[str]:
    """
    Find website domain for a company using multiple strategies.
    
    Args:
        company_name: Company name
        address: Optional address (can contain city, state, country)
        
    Returns:
        Domain if found, None otherwise
    """
    if not company_name:
        logger.warning("No company name provided for domain finding")
        return None
    
    logger.info(f"\n🔍 Finding domain for: {company_name}")
    if address:
        logger.info(f"   Address: {address}")
    
    # Strategy 1: Use Serper.dev search API (primary method)
    logger.info("   Strategy 1: Searching with Serper.dev API...")
    search_result = find_domain_by_search(company_name, address)
    if search_result:
        domain, homepage_url = search_result
        logger.info(f"   ✅ Found domain via search: {domain}")
        return domain
    
    # Strategy 2: Generate candidates and check them (fallback)
    logger.info("   Strategy 2: Generating domain candidates...")
    candidates = generate_domain_candidates(company_name, address)
    logger.info(f"   Generated {len(candidates)} domain candidates")
    
    # Check each candidate
    for candidate in candidates:
        logger.debug(f"   Checking: {candidate}")
        if check_domain_exists(candidate):
            logger.debug(f"   ✓ Domain exists: {candidate}")
            if check_domain_active(candidate):
                logger.info(f"   ✓ Domain is active: {candidate}")
                normalized = normalize_domain(candidate)
                logger.info(f"   ✅ Found domain: {normalized}")
                return normalized
            else:
                logger.debug(f"   ⚠ Domain exists but not active: {candidate}")
        else:
            logger.debug(f"   ✗ Domain does not exist: {candidate}")
    
    logger.warning(f"   ✗ Could not find domain for: {company_name}")
    return None

