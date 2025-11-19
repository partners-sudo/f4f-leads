"""
Address parser to extract country, region, and other components from addresses.
"""
import re
from typing import Dict, Optional, Tuple
from utils.logger import logger

# Common country names and their codes
COUNTRY_NAMES = {
    'united states': 'US', 'usa': 'US', 'u.s.a.': 'US', 'u.s.': 'US',
    'canada': 'CA',
    'mexico': 'MX',
    'guatemala': 'GT',
    'belize': 'BZ',
    'el salvador': 'SV',
    'honduras': 'HN',
    'nicaragua': 'NI',
    'costa rica': 'CR',
    'panama': 'PA',
    'united kingdom': 'GB', 'uk': 'GB', 'england': 'GB', 'scotland': 'GB', 'wales': 'GB',
    'ireland': 'IE',
    'france': 'FR',
    'germany': 'DE',
    'spain': 'ES',
    'italy': 'IT',
    'netherlands': 'NL',
    'belgium': 'BE',
    'switzerland': 'CH',
    'austria': 'AT',
    'portugal': 'PT',
    'sweden': 'SE',
    'norway': 'NO',
    'denmark': 'DK',
    'finland': 'FI',
    'poland': 'PL',
    'czech republic': 'CZ',
    'greece': 'GR',
    'russia': 'RU',
    'japan': 'JP',
    'china': 'CN',
    'south korea': 'KR', 'korea': 'KR',
    'india': 'IN',
    'australia': 'AU',
    'new zealand': 'NZ',
    'brazil': 'BR',
    'argentina': 'AR',
    'chile': 'CL',
    'colombia': 'CO',
    'peru': 'PE',
    'venezuela': 'VE',
}

# Region mapping based on country
REGION_MAP = {
    'US': 'Americas', 'CA': 'Americas', 'MX': 'Americas',
    'GT': 'Americas', 'BZ': 'Americas', 'SV': 'Americas', 'HN': 'Americas',
    'NI': 'Americas', 'CR': 'Americas', 'PA': 'Americas',
    'BR': 'Americas', 'AR': 'Americas', 'CL': 'Americas', 'CO': 'Americas',
    'PE': 'Americas', 'VE': 'Americas',
    'GB': 'EMEA', 'IE': 'EMEA', 'FR': 'EMEA', 'DE': 'EMEA', 'ES': 'EMEA',
    'IT': 'EMEA', 'NL': 'EMEA', 'BE': 'EMEA', 'CH': 'EMEA', 'AT': 'EMEA',
    'PT': 'EMEA', 'SE': 'EMEA', 'NO': 'EMEA', 'DK': 'EMEA', 'FI': 'EMEA',
    'PL': 'EMEA', 'CZ': 'EMEA', 'GR': 'EMEA', 'RU': 'EMEA',
    'JP': 'APAC', 'CN': 'APAC', 'KR': 'APAC', 'IN': 'APAC',
    'AU': 'APAC', 'NZ': 'APAC',
}

# US State abbreviations
US_STATES = {
    'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
    'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
    'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
    'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
    'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy', 'dc'
}


def parse_address(address: str) -> Dict[str, Optional[str]]:
    """
    Parse an address string to extract country, region, city, and other components.
    
    Args:
        address: Full address string (can be multi-line)
        
    Returns:
        Dictionary with parsed address components:
        {
            'full_address': str,
            'country': str (country code),
            'region': str (EMEA, APAC, Americas),
            'city': str,
            'state': str,
            'zip': str
        }
    """
    if not address:
        return {
            'full_address': None,
            'country': None,
            'region': None,
            'city': None,
            'state': None,
            'zip': None
        }
    
    # Normalize address - handle multi-line addresses
    # Split by newlines and combine, removing empty lines
    address_lines = [line.strip() for line in address.split('\n') if line.strip()]
    full_address = ', '.join(address_lines)
    
    result = {
        'full_address': full_address,
        'country': None,
        'region': None,
        'city': None,
        'state': None,
        'zip': None
    }
    
    # Convert to lowercase for matching
    address_lower = full_address.lower()
    
    # Try to find country
    country_code = None
    for country_name, code in COUNTRY_NAMES.items():
        if country_name in address_lower:
            country_code = code
            result['country'] = code
            break
    
    # If no country found, try to infer from context
    if not country_code:
        # Check for US state abbreviations (usually indicates US)
        address_parts = [part.strip() for part in full_address.split(',')]
        for part in reversed(address_parts[-3:]):  # Check last 3 parts
            part_clean = part.lower().strip()
            if part_clean in US_STATES:
                country_code = 'US'
                result['country'] = 'US'
                result['state'] = part_clean.upper()
                break
        
        # Check for ZIP code pattern (US)
        zip_match = re.search(r'\b\d{5}(-\d{4})?\b', full_address)
        if zip_match and not country_code:
            country_code = 'US'
            result['country'] = 'US'
            result['zip'] = zip_match.group()
    
    # Set region based on country
    if country_code and country_code in REGION_MAP:
        result['region'] = REGION_MAP[country_code]
    
    # Try to extract city (usually second-to-last or third-to-last part)
    address_parts = [part.strip() for part in full_address.split(',')]
    if len(address_parts) >= 2:
        # City is often before state/country
        if country_code == 'US' and len(address_parts) >= 3:
            # US format: Street, City, State ZIP
            result['city'] = address_parts[-2].strip()
        elif len(address_parts) >= 2:
            # International format: Street, City, Country
            result['city'] = address_parts[-2].strip()
    
    # Extract state if US
    if country_code == 'US' and not result.get('state'):
        for part in reversed(address_parts[-3:]):
            part_clean = part.lower().strip()
            if part_clean in US_STATES:
                result['state'] = part_clean.upper()
                break
    
    # Extract ZIP code if US
    if country_code == 'US' and not result.get('zip'):
        zip_match = re.search(r'\b\d{5}(-\d{4})?\b', full_address)
        if zip_match:
            result['zip'] = zip_match.group()
    
    logger.debug(f"Parsed address: {result}")
    return result


def get_region_from_country(country_code: Optional[str]) -> Optional[str]:
    """
    Get region code from country code.
    
    Args:
        country_code: Two-letter country code
        
    Returns:
        Region code (EMEA, APAC, Americas) or None
    """
    if country_code and country_code in REGION_MAP:
        return REGION_MAP[country_code]
    return None

