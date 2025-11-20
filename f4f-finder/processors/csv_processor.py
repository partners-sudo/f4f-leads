"""
CSV and PDF processor for extracting shop data from files.
"""
import csv
import re
import json
from typing import List, Dict, Optional
from pathlib import Path
import PyPDF2
import pdfplumber
from utils.logger import logger


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted text
    """
    text = ""
    
    try:
        # Try pdfplumber first (better for tables)
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
        try:
            # Fallback to PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
        except Exception as e2:
            logger.error(f"Both PDF extraction methods failed: {e2}")
            raise
    
    return text


def parse_pdf_to_csv_data(pdf_path: str) -> List[Dict[str, str]]:
    """
    Parse PDF and extract shop data (name and address) from tables.
    Uses pdfplumber to extract table data properly.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of dictionaries with 'name' and 'address' keys
    """
    shops = []
    
    # Keywords to skip (document headers, titles, etc.)
    skip_keywords = [
        'exhibit', 'service list', 'method of service', 'first class mail',
        'name', 'address',  # Skip if these are header rows
    ]
    
    try:
        # Try to extract tables using pdfplumber (better for structured data)
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract tables with default settings (simpler and more reliable)
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        # Skip empty tables
                        if not table or len(table) < 2:
                            continue
                        
                        # Find header row (usually first row)
                        header_row = None
                        name_col_idx = None
                        address_col_idx = None
                        
                        # Look for header row with "Name" and "Address" columns
                        for row_idx, row in enumerate(table[:5]):  # Check first 5 rows for header
                            if not row:
                                continue
                            row_lower = [str(cell).lower() if cell else '' for cell in row]
                            
                            # Check if this looks like a header row
                            if 'name' in row_lower and 'address' in row_lower:
                                header_row = row_idx
                                name_col_idx = row_lower.index('name')
                                # Find address column (could be "Address" or similar)
                                for idx, cell in enumerate(row_lower):
                                    if 'address' in cell:
                                        address_col_idx = idx
                                        break
                                break
                        
                        # If we found header, process data rows
                        if name_col_idx is not None and address_col_idx is not None:
                            start_row = header_row + 1 if header_row is not None else 1
                            row_idx = start_row
                            while row_idx < len(table):
                                row = table[row_idx]
                                if not row or len(row) <= max(name_col_idx, address_col_idx):
                                    row_idx += 1
                                    continue
                                
                                name = str(row[name_col_idx]).strip() if name_col_idx < len(row) else ''
                                
                                if not name:
                                    row_idx += 1
                                    continue
                                
                                # ALWAYS extract full address from page text to get ALL parts
                                # Table extraction often misses multi-line addresses
                                address_parts = []
                                
                                try:
                                    # Get full page text
                                    page_text = page.extract_text()
                                    if page_text and name in page_text:
                                        # Find the name in the text
                                        name_pos = page_text.find(name)
                                        if name_pos >= 0:
                                            # Get a chunk of text after the name (enough for full address)
                                            # Look for the next shop name or "Method of Service" to know where to stop
                                            search_start = name_pos + len(name)
                                            search_end = search_start + 1000  # Look ahead 1000 chars
                                            
                                            # Find where address ends (next shop name or "Method of Service")
                                            next_name_pos = page_text.find('\n', search_start + 200)  # At least 200 chars for address
                                            method_pos = page_text.find('Method of Service', search_start)
                                            first_class_pos = page_text.find('First Class Mail', search_start)
                                            
                                            # Determine end position
                                            end_positions = [p for p in [next_name_pos, method_pos, first_class_pos, search_end] if p > search_start]
                                            end_pos = min(end_positions) if end_positions else search_end
                                            
                                            # Extract the address section
                                            address_section = page_text[search_start:end_pos]
                                            
                                            # Split into lines and collect address parts
                                            lines = address_section.split('\n')
                                            for line in lines:
                                                line = line.strip()
                                                if not line or len(line) < 2:
                                                    continue
                                                
                                                line_lower = line.lower()
                                                
                                                # Stop if we hit headers or next entry
                                                if any(skip in line_lower for skip in ['name', 'address', 'method of service', 'first class mail']):
                                                    # But only stop if we've already collected some address parts
                                                    if len(address_parts) > 0:
                                                        break
                                                    continue
                                                
                                                # Collect this line as address part
                                                address_parts.append(line)
                                                
                                                # Stop if we have enough parts (typically 4-5: Attn, Street, City, Country)
                                                if len(address_parts) >= 5:
                                                    break
                                            
                                            logger.debug(f"Extracted {len(address_parts)} address parts for {name}")
                                except Exception as e:
                                    logger.warning(f"Could not extract address from page text for {name}: {e}")
                                    # Fallback: try to get from table cell
                                    address_cell = row[address_col_idx] if address_col_idx < len(row) else ''
                                    if address_cell:
                                        if isinstance(address_cell, str):
                                            address_parts = [l.strip() for l in address_cell.split('\n') if l.strip()]
                                        else:
                                            address_parts = [str(address_cell).strip()]
                                
                                # Combine all address parts
                                address = '\n'.join(address_parts) if address_parts else ''
                                
                                # Skip empty rows or header-like rows
                                if not name or not address:
                                    row_idx += 1
                                    continue
                                
                                # Skip if name contains skip keywords (document headers)
                                name_lower = name.lower()
                                if any(keyword in name_lower for keyword in skip_keywords):
                                    row_idx += 1
                                    continue
                                
                                # Skip if address is just "First Class Mail" or similar
                                address_lower = address.lower()
                                if 'first class mail' in address_lower or 'method of service' in address_lower:
                                    row_idx += 1
                                    continue
                                
                                # Valid shop entry - combine all address parts
                                shops.append({
                                    'name': name,
                                    'address': address  # Full multi-line address
                                })
                                
                                row_idx += 1
                
                # If no tables found, fall back to text extraction
                if not shops:
                    text = page.extract_text()
                    if text:
                        shops.extend(_parse_text_fallback(text, skip_keywords))
        
        # If pdfplumber didn't work, try fallback
        if not shops:
            logger.warning("No tables found with pdfplumber, trying text extraction fallback")
            text = extract_text_from_pdf(pdf_path)
            shops = _parse_text_fallback(text, skip_keywords)
    
    except Exception as e:
        logger.warning(f"pdfplumber table extraction failed: {e}, trying text extraction")
        text = extract_text_from_pdf(pdf_path)
        shops = _parse_text_fallback(text, skip_keywords)
    
    logger.info(f"Extracted {len(shops)} shops from PDF")
    return shops


def _parse_text_fallback(text: str, skip_keywords: List[str]) -> List[Dict[str, str]]:
    """
    Fallback text parsing when table extraction fails.
    """
    shops = []
    lines = text.split('\n')
    current_shop = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_shop.get('name') and current_shop.get('address'):
                # Skip if name contains skip keywords
                name_lower = current_shop['name'].lower()
                if not any(keyword in name_lower for keyword in skip_keywords):
                    shops.append(current_shop)
            current_shop = {}
            continue
        
        # Skip lines that are clearly headers
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in skip_keywords):
            continue
        
        # Heuristic: if line looks like an address (contains numbers, street keywords, or ZIP codes)
        is_address = (
            bool(re.search(r'\d{5}(-\d{4})?', line)) or  # ZIP code pattern
            (bool(re.search(r'\d+', line)) and any(
                keyword in line_lower for keyword in ['street', 'st', 'avenue', 'ave', 'road', 'rd', 
                                                     'drive', 'dr', 'lane', 'ln', 'blvd', 'boulevard',
                                                     'cir', 'circle', 'way', 'ct', 'court']
            ))
        )
        
        # Heuristic: if line looks like a name (contains LLC, Inc, Corp, etc. or reasonable business name)
        is_name = (
            any(term in line_lower for term in ['llc', 'inc', 'corp', 'ltd', 'company', 'warehouse', 'cafe', 'shop', 'store']) or
            (not bool(re.search(r'\d', line)) and 5 <= len(line) <= 100 and 
             not any(keyword in line_lower for keyword in ['first class', 'method of service', 'exhibit']))
        )
        
        if is_name and not current_shop.get('name'):
            current_shop['name'] = line
        elif is_address or (current_shop.get('name') and not current_shop.get('address')):
            # Build multi-line address
            if 'address' not in current_shop:
                current_shop['address'] = line
            else:
                # Keep as multi-line address (preserve structure)
                current_shop['address'] += '\n' + line
    
    # Add last shop if exists
    if current_shop.get('name') and current_shop.get('address'):
        name_lower = current_shop['name'].lower()
        if not any(keyword in name_lower for keyword in skip_keywords):
            shops.append(current_shop)
    
    return shops


def read_csv_file(csv_path: str) -> List[Dict[str, str]]:
    """
    Read CSV file and return list of dictionaries.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of dictionaries with CSV data
    """
    shops = []
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        # Try to detect delimiter
        sample = file.read(1024)
        file.seek(0)
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        
        reader = csv.DictReader(file, delimiter=delimiter)
        
        for row in reader:
            # Normalize column names (case-insensitive, handle spaces)
            normalized_row = {}
            for key, value in row.items():
                normalized_key = key.strip().lower().replace(' ', '_')
                normalized_row[normalized_key] = value.strip() if value else None
            
            shops.append(normalized_row)
    
    logger.info(f"Read {len(shops)} rows from CSV")
    return shops


def normalize_shop_data(shop: Dict[str, str]) -> Dict[str, Optional[str]]:
    """
    Normalize shop data to have consistent 'name' and 'address' fields.
    
    Args:
        shop: Dictionary with shop data (may have various column names)
        
    Returns:
        Normalized dictionary with 'name' and 'address' fields
    """
    normalized = {
        'name': None,
        'address': None
    }
    
    # Try to find name field
    name_fields = ['name', 'shop_name', 'store_name', 'business_name', 'company_name', 'company', 'shop', 'store']
    for field in name_fields:
        if field in shop and shop[field]:
            normalized['name'] = shop[field].strip()
            break
    
    # Try to find address field
    address_fields = ['address', 'street_address', 'location', 'addr', 'full_address']
    for field in address_fields:
        if field in shop and shop[field]:
            normalized['address'] = shop[field].strip()
            break
    
    # If address is split across multiple fields, combine them
    if not normalized['address']:
        address_parts = []
        address_part_fields = ['street', 'city', 'state', 'zip', 'postal_code', 'country']
        for field in address_part_fields:
            if field in shop and shop[field]:
                address_parts.append(shop[field].strip())
        if address_parts:
            normalized['address'] = ', '.join(address_parts)
    
    return normalized


def get_cache_file_path(file_path: str) -> Path:
    """
    Generate cache file path based on source file path.
    
    Args:
        file_path: Path to source file
        
    Returns:
        Path to cache file
    """
    file_path_obj = Path(file_path)
    # Create cache file in same directory as source file
    # e.g., D://shop_list.pdf -> D://shop_list_extracted.json
    cache_name = file_path_obj.stem + "_extracted.json"
    cache_path = file_path_obj.parent / cache_name
    return cache_path


def load_shops_from_cache(cache_path: Path) -> Optional[List[Dict[str, Optional[str]]]]:
    """
    Load extracted shops from cache file.
    
    Args:
        cache_path: Path to cache file
        
    Returns:
        List of shops if cache exists and is valid, None otherwise
    """
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            shops = json.load(f)
        logger.info(f"✅ Loaded {len(shops)} shops from cache: {cache_path}")
        return shops
    except Exception as e:
        logger.warning(f"Failed to load cache from {cache_path}: {e}")
        return None


def save_shops_to_cache(shops: List[Dict[str, Optional[str]]], cache_path: Path):
    """
    Save extracted shops to cache file.
    
    Args:
        shops: List of shop dictionaries
        cache_path: Path to cache file
    """
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(shops, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Saved {len(shops)} shops to cache: {cache_path}")
    except Exception as e:
        logger.warning(f"Failed to save cache to {cache_path}: {e}")


def process_shop_file(file_path: str, use_cache: bool = True) -> List[Dict[str, Optional[str]]]:
    """
    Process a file (CSV or PDF) and extract shop data.
    Uses cache to avoid re-extracting if cache file exists and is newer than source.
    
    Args:
        file_path: Path to CSV or PDF file
        use_cache: Whether to use cache if available (default: True)
        
    Returns:
        List of normalized shop dictionaries with 'name' and 'address'
    """
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Check cache first
    if use_cache:
        cache_path = get_cache_file_path(file_path)
        
        # Check if cache exists and is newer than source file
        if cache_path.exists():
            source_mtime = file_path_obj.stat().st_mtime
            cache_mtime = cache_path.stat().st_mtime
            
            # If cache is newer or same age, use it
            if cache_mtime >= source_mtime:
                cached_shops = load_shops_from_cache(cache_path)
                if cached_shops:
                    return cached_shops
                else:
                    logger.info("Cache file exists but is invalid, re-extracting...")
            else:
                logger.info("Source file is newer than cache, re-extracting...")
        else:
            logger.info("No cache file found, extracting from source...")
    
    # Extract from source file
    file_ext = file_path_obj.suffix.lower()
    
    logger.info(f"📄 Extracting shops from {file_path}...")
    if file_ext == '.csv':
        shops = read_csv_file(str(file_path_obj))
    elif file_ext == '.pdf':
        shops = parse_pdf_to_csv_data(str(file_path_obj))
    else:
        raise ValueError(f"Unsupported file type: {file_ext}. Supported: .csv, .pdf")
    
    # Normalize all shops
    normalized_shops = []
    for shop in shops:
        normalized = normalize_shop_data(shop)
        if normalized['name']:  # Only include shops with names
            normalized_shops.append(normalized)
    
    logger.info(f"Processed {len(normalized_shops)} shops from {file_path}")
    
    # Save to cache
    if use_cache:
        cache_path = get_cache_file_path(file_path)
        save_shops_to_cache(normalized_shops, cache_path)
    
    return normalized_shops

