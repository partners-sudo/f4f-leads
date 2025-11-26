"""
Competitor Discovery Module

Discovers retailers and sellers that carry competitor brands by:
1. Scraping brand websites for retailer lists
2. Searching marketplaces (eBay, Amazon, Etsy, etc.)
3. Finding convention vendor lists
4. Finding stores with overlapping products
"""

import asyncio
import re
import httpx
import os
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from utils.logger import logger
from enrichment.domain_finder import normalize_domain, find_domain
from enrichment.clearbit_integration import enrich_company
from enrichment.email_finder import find_emails
from enrichment.contact_verification import verify_contact
from supabase_client import sb

# Import filter functions - need to handle relative imports
import sys
from pathlib import Path
# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from tasks import filter_company_data, filter_contact_data


class CompetitorDiscovery:
    """Main class for discovering retailers that sell competitor brands."""
    
    def __init__(self, brand_names: List[str]):
        """
        Initialize competitor discovery.
        
        Args:
            brand_names: List of brand names to search for (e.g., ["Funko", "Tubbz", "Cable guys"])
        """
        self.brand_names = [b.strip() for b in brand_names if b.strip()]
        self.discovered_companies: List[Dict] = []
        self.seen_domains: Set[str] = set()
        self.seen_names: Set[str] = set()
        # Track which brands each company matches
        self.company_brand_matches: Dict[str, Set[str]] = {}  # domain -> set of brands
        
    async def discover_all(self) -> Dict:
        """
        Run all discovery strategies and return results.
        
        Returns:
            Dictionary with discovery results and statistics
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 Starting Competitor Discovery for: {', '.join(self.brand_names)}")
        logger.info(f"{'='*80}\n")
        
        # Strategy 1: Brand website retailer lists
        logger.info("📋 Strategy 1: Brand Website Retailer Lists")
        brand_results = await self._discover_from_brand_sites()
        logger.info(f"   Found {len(brand_results)} companies from brand sites\n")
        
        # Strategy 2: Marketplace sellers
        logger.info("🛒 Strategy 2: Marketplace Sellers")
        marketplace_results = await self._discover_from_marketplaces()
        logger.info(f"   Found {len(marketplace_results)} companies from marketplaces\n")
        
        # Strategy 3: Convention vendor lists
        logger.info("🎪 Strategy 3: Convention Vendor Lists")
        convention_results = await self._discover_from_conventions()
        logger.info(f"   Found {len(convention_results)} companies from conventions\n")
        
        # Strategy 4: Overlap search (stores selling similar products)
        logger.info("🔍 Strategy 4: Overlap Search (Similar Products)")
        overlap_results = await self._discover_from_overlap_search()
        logger.info(f"   Found {len(overlap_results)} companies from overlap search\n")
        
        # Combine all results
        all_results = brand_results + marketplace_results + convention_results + overlap_results
        
        # Deduplicate
        logger.info("🔄 Deduplicating results...")
        deduped = self._deduplicate_companies(all_results)
        logger.info(f"   After deduplication: {len(deduped)} unique companies\n")
        
        # Infer company names for entries missing names
        logger.info("🏷️  Inferring company names...")
        inferred = self._infer_company_names(deduped)
        logger.info(f"   Processed {len(inferred)} companies\n")
        
        self.discovered_companies = inferred
        
        return {
            'total_discovered': len(self.discovered_companies),
            'by_strategy': {
                'brand_sites': len(brand_results),
                'marketplaces': len(marketplace_results),
                'conventions': len(convention_results),
                'overlap': len(overlap_results)
            },
            'after_deduplication': len(deduped)
        }
    
    async def _discover_from_brand_sites(self) -> List[Dict]:
        """Discover retailers from brand websites (where-to-buy pages, retailer lists, etc.)."""
        results = []
        
        for brand in self.brand_names:
            try:
                # Search for brand websites - try multiple potential domains
                brand_domains = await self._find_brand_websites(brand)
                if not brand_domains:
                    logger.warning(f"   Could not find website for {brand}")
                    continue
                
                # Try all found brand domains (in case there are regional variations)
                for brand_domain in brand_domains:
                    logger.info(f"   Checking brand domain: {brand_domain}")
                    
                    # Common retailer list page patterns (from strategy doc)
                    retailer_pages = [
                        f"https://{brand_domain}/where-to-buy",
                        f"https://{brand_domain}/store-locator",
                        f"https://{brand_domain}/stockists",
                        f"https://{brand_domain}/retailers",
                        f"https://{brand_domain}/distributors",
                        f"https://{brand_domain}/partners",
                        f"https://{brand_domain}/find-a-store",
                        f"https://{brand_domain}/dealers",
                        f"https://{brand_domain}/stores",
                        f"https://{brand_domain}/collections",  # Like EXGPro Cable Guys
                    ]
                    
                    # Check ALL retailer pages, not just the first one
                    # Different pages may have different retailers
                    total_found = 0
                    for page_url in retailer_pages:
                        try:
                            page_results = await self._scrape_retailer_list_page(page_url, brand)
                            if page_results:
                                results.extend(page_results)
                                total_found += len(page_results)
                                logger.info(f"   ✓ Found {len(page_results)} retailers on {page_url}")
                        except Exception as e:
                            logger.debug(f"   Could not scrape {page_url}: {e}")
                            continue
                    
                    if total_found > 0:
                        logger.info(f"   Total retailers found from {brand_domain}: {total_found}")
                        
            except Exception as e:
                logger.error(f"   Error discovering from {brand} brand site: {e}")
                continue
        
        return results
    
    async def _find_brand_websites(self, brand_name: str) -> List[str]:
        """
        Find official websites for a brand. Returns list of potential brand domains.
        Checks all Serper.dev results, not just the first one.
        """
        domains = []
        
        # Use domain finder to find brand website
        domain = find_domain(brand_name)
        if domain:
            domains.append(domain)
        
        # Also search for brand website using Serper to find additional/regional sites
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return domains if domains else []
            
            query = f"{brand_name} official website"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 10}  # Get more results
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Check ALL results, not just the first one
                brand_lower = brand_name.lower().replace(' ', '').replace('-', '')
                seen_domains = set(domains)
                
                # First pass: prioritize domains that match brand name
                priority_domains = []
                candidate_domains = []
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if link:
                        parsed = urlparse(link)
                        domain = normalize_domain(parsed.netloc)
                        
                        if not domain or domain in seen_domains:
                            continue
                        
                        # Skip social media and directory sites
                        if any(d in domain for d in ['facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'wikipedia', 'reddit', 'yelp', 'bbb']):
                            continue
                        
                        seen_domains.add(domain)
                        domain_lower = domain.lower()
                        
                        # Check if brand name appears in domain (higher priority)
                        if brand_lower in domain_lower or domain_lower in brand_lower:
                            priority_domains.append(domain)
                        else:
                            candidate_domains.append(domain)
                
                # Return priority domains first, then candidates
                all_domains = priority_domains + candidate_domains
                if all_domains:
                    # Combine with domain finder result, avoiding duplicates
                    for d in all_domains:
                        if d not in domains:
                            domains.append(d)
                    
                    logger.info(f"   Found {len(domains)} potential brand website(s) for {brand_name}")
        except Exception as e:
            logger.debug(f"   Error finding brand website for {brand_name}: {e}")
        
        return domains if domains else []
    
    async def _scrape_retailer_list_page(self, url: str, brand: str) -> List[Dict]:
        """Scrape a retailer list page from a brand website."""
        results = []
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return results
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for retailer links - common patterns
                # Links in lists, tables, divs with retailer/store classes, embedded maps
                selectors = [
                    'a[href*="retailer"]',
                    'a[href*="store"]',
                    'a[href*="dealer"]',
                    'a[href*="stockist"]',
                    'a[href*="distributor"]',
                    'a[href*="partner"]',
                    '.retailer',
                    '.store',
                    '.dealer',
                    '.stockist',
                    '.distributor',
                    '.partner',
                    '[class*="retailer"]',
                    '[class*="store"]',
                    '[class*="stockist"]',
                    '[class*="vendor"]',
                    'table a',  # Links in tables
                    'ul.retailer-list a',  # Links in retailer lists
                    'div.retailer-grid a',  # Branded stockist grids
                ]
                
                # Also check for embedded maps (Google Maps, etc.)
                map_links = soup.find_all('a', href=re.compile(r'(maps\.google|google\.com/maps|openstreetmap)'))
                for map_link in map_links:
                    # Extract business name from map link if possible
                    title = map_link.get('title', '') or map_link.get_text(strip=True)
                    if title:
                        # Try to find associated website link near the map link
                        parent = map_link.parent
                        if parent:
                            nearby_links = parent.find_all('a', href=re.compile(r'^https?://'))
                            for nearby_link in nearby_links:
                                href = nearby_link.get('href', '')
                                if href and not any(skip in href for skip in ['maps.google', 'google.com/maps']):
                                    try:
                                        parsed = urlparse(href)
                                        domain = normalize_domain(parsed.netloc)
                                        if domain and domain not in found_links:
                                            found_links.add(domain)
                                            name = title or self._infer_name_from_domain(domain)
                                            
                                            if domain not in self.company_brand_matches:
                                                self.company_brand_matches[domain] = set()
                                            self.company_brand_matches[domain].add(brand)
                                            
                                            results.append({
                                                'name': name,
                                                'domain': domain,
                                                'source': 'competitor_discovery_brand_site',
                                                'brand_focus': brand,
                                                'matched_brands': [brand]
                                            })
                                    except Exception:
                                        continue
                
                found_links = set()
                for selector in selectors:
                    elements = soup.select(selector)
                    for elem in elements:
                        href = elem.get('href', '')
                        if not href:
                            continue
                        
                        # Make absolute URL
                        if href.startswith('/'):
                            href = urljoin(url, href)
                        elif not href.startswith('http'):
                            continue
                        
                        # Extract domain
                        try:
                            parsed = urlparse(href)
                            domain = normalize_domain(parsed.netloc)
                            if domain and domain not in found_links:
                                found_links.add(domain)
                                
                                # Get company name from link text or domain
                                name = elem.get_text(strip=True) or self._infer_name_from_domain(domain)
                                
                                # Track brand match
                                if domain not in self.company_brand_matches:
                                    self.company_brand_matches[domain] = set()
                                self.company_brand_matches[domain].add(brand)
                                
                                results.append({
                                    'name': name,
                                    'domain': domain,
                                    'source': 'competitor_discovery_brand_site',
                                    'brand_focus': brand,
                                    'matched_brands': [brand]
                                })
                        except Exception:
                            continue
                
        except Exception as e:
            logger.debug(f"   Error scraping {url}: {e}")
        
        return results
    
    async def _discover_from_marketplaces(self) -> List[Dict]:
        """Discover sellers from marketplaces (eBay, Amazon, Etsy, Walmart, MercadoLibre, Shopee, Lazada, AliExpress)."""
        results = []
        
        for brand in self.brand_names:
            # Search eBay
            try:
                ebay_results = await self._search_ebay(brand)
                results.extend(ebay_results)
            except Exception as e:
                logger.debug(f"   Error searching eBay for {brand}: {e}")
            
            # Search Amazon
            try:
                amazon_results = await self._search_amazon(brand)
                results.extend(amazon_results)
            except Exception as e:
                logger.debug(f"   Error searching Amazon for {brand}: {e}")
            
            # Search Etsy
            try:
                etsy_results = await self._search_etsy(brand)
                results.extend(etsy_results)
            except Exception as e:
                logger.debug(f"   Error searching Etsy for {brand}: {e}")
            
            # Search Walmart Marketplace
            try:
                walmart_results = await self._search_walmart(brand)
                results.extend(walmart_results)
            except Exception as e:
                logger.debug(f"   Error searching Walmart for {brand}: {e}")
            
            # Search MercadoLibre (LatAm)
            try:
                mercadolibre_results = await self._search_mercadolibre(brand)
                results.extend(mercadolibre_results)
            except Exception as e:
                logger.debug(f"   Error searching MercadoLibre for {brand}: {e}")
            
            # Search Shopee (Asia)
            try:
                shopee_results = await self._search_shopee(brand)
                results.extend(shopee_results)
            except Exception as e:
                logger.debug(f"   Error searching Shopee for {brand}: {e}")
            
            # Search Lazada (Asia)
            try:
                lazada_results = await self._search_lazada(brand)
                results.extend(lazada_results)
            except Exception as e:
                logger.debug(f"   Error searching Lazada for {brand}: {e}")
            
            # Search AliExpress (China/Global)
            try:
                aliexpress_results = await self._search_aliexpress(brand)
                results.extend(aliexpress_results)
            except Exception as e:
                logger.debug(f"   Error searching AliExpress for {brand}: {e}")
        
        return results
    
    async def _search_ebay(self, brand: str) -> List[Dict]:
        """Search eBay for sellers of the brand."""
        results = []
        
        try:
            # Use Serper to search eBay
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            query = f"{brand} site:ebay.com sellers"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if 'ebay.com' in link and '/usr/' in link:
                        # Extract seller username from eBay URL
                        # Format: https://www.ebay.com/usr/username
                        parts = link.split('/usr/')
                        if len(parts) > 1:
                            seller_username = parts[1].split('/')[0].split('?')[0]
                            if seller_username:
                                results.append({
                                    'name': f"eBay Seller: {seller_username}",
                                    'domain': None,  # eBay sellers don't have domains
                                    'source': 'competitor_discovery_marketplace_ebay',
                                    'brand_focus': brand,
                                    'matched_brands': [brand]
                                })
        except Exception as e:
            logger.debug(f"   Error searching eBay: {e}")
        
        return results
    
    async def _search_amazon(self, brand: str) -> List[Dict]:
        """Search Amazon for sellers of the brand."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            query = f"{brand} site:amazon.com sellers stores"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if 'amazon.com' in link and ('/stores/' in link or '/gp/seller/' in link):
                        # Try to extract seller/store name
                        title = result.get('title', '')
                        store_name = title.split('Amazon.com:')[1].split('|')[0].strip() if 'Amazon.com:' in title else None
                        
                        if store_name:
                            results.append({
                                'name': f"Amazon Store: {store_name}",
                                'domain': None,
                                'source': 'competitor_discovery_marketplace_amazon',
                                'brand_focus': brand,
                                'matched_brands': [brand]
                            })
        except Exception as e:
            logger.debug(f"   Error searching Amazon: {e}")
        
        return results
    
    async def _search_etsy(self, brand: str) -> List[Dict]:
        """Search Etsy for shops selling the brand."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            query = f"{brand} site:etsy.com shop"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if 'etsy.com/shop/' in link:
                        # Extract shop name from Etsy URL
                        # Format: https://www.etsy.com/shop/shopname
                        parts = link.split('/shop/')
                        if len(parts) > 1:
                            shop_name = parts[1].split('/')[0].split('?')[0]
                            if shop_name:
                                # Try to find shop's external website
                                shop_domain = await self._find_etsy_shop_website(link)
                                
                                # Track brand match if domain found
                                if shop_domain:
                                    if shop_domain not in self.company_brand_matches:
                                        self.company_brand_matches[shop_domain] = set()
                                    self.company_brand_matches[shop_domain].add(brand)
                                
                                results.append({
                                    'name': f"Etsy Shop: {shop_name}",
                                    'domain': shop_domain,
                                    'source': 'competitor_discovery_marketplace_etsy',
                                    'brand_focus': brand,
                                    'matched_brands': [brand]
                                })
        except Exception as e:
            logger.debug(f"   Error searching Etsy: {e}")
        
        return results
    
    async def _find_etsy_shop_website(self, etsy_url: str) -> Optional[str]:
        """Try to find external website for an Etsy shop."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(etsy_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Look for external website link
                    website_link = soup.find('a', href=re.compile(r'^https?://(?!www\.etsy\.com)'))
                    if website_link:
                        href = website_link.get('href', '')
                        if href:
                            parsed = urlparse(href)
                            return normalize_domain(parsed.netloc)
        except Exception:
            pass
        return None
    
    async def _search_walmart(self, brand: str) -> List[Dict]:
        """Search Walmart Marketplace for sellers of the brand."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            query = f"{brand} site:walmart.com marketplace sellers"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if 'walmart.com' in link and ('/ip/' in link or '/seller/' in link):
                        title = result.get('title', '')
                        # Try to extract seller/store name
                        store_name = title.split('|')[0].strip() if '|' in title else title
                        
                        if store_name:
                            results.append({
                                'name': f"Walmart Marketplace: {store_name}",
                                'domain': None,
                                'source': 'competitor_discovery_marketplace_walmart',
                                'brand_focus': brand,
                                'matched_brands': [brand]
                            })
        except Exception as e:
            logger.debug(f"   Error searching Walmart: {e}")
        
        return results
    
    async def _search_mercadolibre(self, brand: str) -> List[Dict]:
        """Search MercadoLibre (LatAm) for sellers of the brand."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            query = f"{brand} site:mercadolibre.com tienda"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if 'mercadolibre.com' in link and '/tienda/' in link:
                        # Extract store name from URL
                        parts = link.split('/tienda/')
                        if len(parts) > 1:
                            store_name = parts[1].split('/')[0].split('?')[0]
                            if store_name:
                                results.append({
                                    'name': f"MercadoLibre: {store_name}",
                                    'domain': None,
                                    'source': 'competitor_discovery_marketplace_mercadolibre',
                                    'brand_focus': brand,
                                    'matched_brands': [brand]
                                })
        except Exception as e:
            logger.debug(f"   Error searching MercadoLibre: {e}")
        
        return results
    
    async def _search_shopee(self, brand: str) -> List[Dict]:
        """Search Shopee (Asia) for sellers of the brand."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            query = f"{brand} site:shopee.com shop"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if 'shopee.com' in link and '/shop/' in link:
                        # Extract shop name from URL
                        parts = link.split('/shop/')
                        if len(parts) > 1:
                            shop_name = parts[1].split('/')[0].split('?')[0]
                            if shop_name:
                                results.append({
                                    'name': f"Shopee: {shop_name}",
                                    'domain': None,
                                    'source': 'competitor_discovery_marketplace_shopee',
                                    'brand_focus': brand,
                                    'matched_brands': [brand]
                                })
        except Exception as e:
            logger.debug(f"   Error searching Shopee: {e}")
        
        return results
    
    async def _search_lazada(self, brand: str) -> List[Dict]:
        """Search Lazada (Asia) for sellers of the brand."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            query = f"{brand} site:lazada.com shop"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if 'lazada.com' in link and ('/shop/' in link or '/seller/' in link):
                        title = result.get('title', '')
                        store_name = title.split('|')[0].strip() if '|' in title else title
                        
                        if store_name:
                            results.append({
                                'name': f"Lazada: {store_name}",
                                'domain': None,
                                'source': 'competitor_discovery_marketplace_lazada',
                                'brand_focus': brand,
                                'matched_brands': [brand]
                            })
        except Exception as e:
            logger.debug(f"   Error searching Lazada: {e}")
        
        return results
    
    async def _search_aliexpress(self, brand: str) -> List[Dict]:
        """Search AliExpress (China/Global) for sellers of the brand."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            query = f"{brand} site:aliexpress.com store"
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if 'aliexpress.com' in link and '/store/' in link:
                        # Extract store name from URL
                        parts = link.split('/store/')
                        if len(parts) > 1:
                            store_name = parts[1].split('/')[0].split('?')[0]
                            if store_name:
                                results.append({
                                    'name': f"AliExpress: {store_name}",
                                    'domain': None,
                                    'source': 'competitor_discovery_marketplace_aliexpress',
                                    'brand_focus': brand,
                                    'matched_brands': [brand]
                                })
        except Exception as e:
            logger.debug(f"   Error searching AliExpress: {e}")
        
        return results
    
    async def _discover_from_conventions(self) -> List[Dict]:
        """Discover retailers from convention/expo vendor lists."""
        results = []
        
        # Build brand-specific convention search queries
        for brand in self.brand_names:
            # Brand-specific convention searches
            brand_convention_queries = [
                f"{brand} vendor list",
                f"{brand} exhibitors",
                f"{brand} comic con retailers",
                f"{brand} anime expo vendors",
                f"{brand} toy fair exhibitors",
            ]
            
            for query in brand_convention_queries:
                try:
                    convention_results = await self._search_convention_vendors(query, brand)
                    results.extend(convention_results)
                except Exception as e:
                    logger.debug(f"   Error searching conventions with '{query}': {e}")
        
        # General convention searches
        convention_keywords = [
            "comic con vendor list",
            "toy fair exhibitor list",
            "collectibles expo vendors",
            "pop culture convention vendors",
            "anime convention vendors",
            "gaming convention exhibitors",
            "comic con 2024 vendors",
            "anime expo 2024 exhibitors",
            "toy fair 2024 vendors"
        ]
        
        for keyword in convention_keywords:
            try:
                convention_results = await self._search_convention_vendors(keyword)
                results.extend(convention_results)
            except Exception as e:
                logger.debug(f"   Error searching conventions with '{keyword}': {e}")
        
        return results
    
    async def _search_convention_vendors(self, keyword: str, brand: Optional[str] = None) -> List[Dict]:
        """Search for convention vendor lists."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": keyword, "num": 10}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    title = result.get('title', '')
                    
                    # Check if this looks like a vendor list page
                    if any(term in link.lower() or term in title.lower() 
                           for term in ['vendor', 'exhibitor', 'exhibitor-list', 'vendor-list']):
                        try:
                            # Try to scrape vendor list from this page
                            vendor_results = await self._scrape_vendor_list_page(link)
                            results.extend(vendor_results)
                        except Exception as e:
                            logger.debug(f"   Could not scrape vendor list from {link}: {e}")
        except Exception as e:
            logger.debug(f"   Error searching convention vendors: {e}")
        
        return results
    
    async def _scrape_vendor_list_page(self, url: str) -> List[Dict]:
        """Scrape a vendor/exhibitor list page."""
        results = []
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return results
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for vendor/exhibitor entries
                # Common patterns: lists, tables, divs with vendor info
                vendor_selectors = [
                    '.vendor',
                    '.exhibitor',
                    '[class*="vendor"]',
                    '[class*="exhibitor"]',
                    'table tr',
                    'ul li',
                ]
                
                found_domains = set()
                for selector in vendor_selectors:
                    elements = soup.select(selector)
                    for elem in elements:
                        # Look for links in vendor entry
                        links = elem.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            if not href or href.startswith('#'):
                                continue
                            
                            # Make absolute URL
                            if href.startswith('/'):
                                href = urljoin(url, href)
                            elif not href.startswith('http'):
                                continue
                            
                            # Extract domain
                            try:
                                parsed = urlparse(href)
                                domain = normalize_domain(parsed.netloc)
                                
                                # Skip if it's the convention site itself or common directories
                                if (domain and domain not in found_domains and 
                                    not any(skip in domain for skip in ['facebook', 'instagram', 'twitter', 'linkedin'])):
                                    found_domains.add(domain)
                                    
                                    # Get company name
                                    name = link.get_text(strip=True) or elem.get_text(strip=True)[:100] or self._infer_name_from_domain(domain)
                                    
                                    # Determine which brands match based on keyword or passed brand
                                    matched_brands = []
                                    if brand:
                                        matched_brands = [brand]
                                    else:
                                        for b in self.brand_names:
                                            if b.lower() in keyword.lower():
                                                matched_brands.append(b)
                                    if not matched_brands:
                                        # If no specific brand match, match all brands
                                        matched_brands = self.brand_names.copy()
                                    
                                    # Track brand matches
                                    if domain not in self.company_brand_matches:
                                        self.company_brand_matches[domain] = set()
                                    for brand in matched_brands:
                                        self.company_brand_matches[domain].add(brand)
                                    
                                    results.append({
                                        'name': name,
                                        'domain': domain,
                                        'source': 'competitor_discovery_convention',
                                        'matched_brands': matched_brands
                                    })
                            except Exception:
                                continue
        except Exception as e:
            logger.debug(f"   Error scraping vendor list from {url}: {e}")
        
        return results
    
    async def _discover_from_overlap_search(self) -> List[Dict]:
        """Discover stores by searching for overlapping products."""
        results = []
        
        # Build brand-specific overlap queries
        brand_overlap_queries = []
        for brand in self.brand_names:
            brand_overlap_queries.extend([
                f"{brand} collectibles store",
                f"{brand} retailer",
                f"{brand} stockist",
                f"stores selling {brand}",
                f"where to buy {brand}",
            ])
        
        # Category-based overlap queries
        category_queries = [
            "pop culture collectibles store",
            "vinyl figure retailer",
            "anime figure shop",
            "gaming merch retailer",
            "pop culture store USA",
            "collectibles shop online",
            "anime collectibles shop",
            "gaming merchandise stores",
            "nerd culture boutique",
            "comic book store collectibles",
        ]
        
        overlap_queries = brand_overlap_queries + category_queries
        
        for query in overlap_queries:
            try:
                overlap_results = await self._search_overlapping_stores(query)
                results.extend(overlap_results)
            except Exception as e:
                logger.debug(f"   Error in overlap search '{query}': {e}")
        
        return results
    
    async def _search_overlapping_stores(self, query: str) -> List[Dict]:
        """Search for stores with overlapping products."""
        results = []
        
        try:
            api_key = os.getenv('SERPER_API_KEY')
            if not api_key:
                return results
            
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query, "num": 20}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    title = result.get('title', '')
                    
                    # Skip marketplace and directory sites
                    if any(skip in link.lower() for skip in ['amazon.com', 'ebay.com', 'etsy.com', 'facebook.com', 'yelp.com']):
                        continue
                    
                    try:
                        parsed = urlparse(link)
                        domain = normalize_domain(parsed.netloc)
                        
                        if domain and domain not in self.seen_domains:
                            # Extract company name from title or domain
                            name = title.split('|')[0].split('-')[0].strip() or self._infer_name_from_domain(domain)
                            
                            # Determine which brands match based on query
                            matched_brands = []
                            for brand in self.brand_names:
                                if brand.lower() in query.lower():
                                    matched_brands.append(brand)
                            if not matched_brands:
                                # If no specific brand match, match all brands for category overlap
                                matched_brands = self.brand_names.copy()
                            
                            # Track brand matches
                            if domain not in self.company_brand_matches:
                                self.company_brand_matches[domain] = set()
                            for brand in matched_brands:
                                self.company_brand_matches[domain].add(brand)
                            
                            results.append({
                                'name': name,
                                'domain': domain,
                                'source': 'competitor_discovery_overlap',
                                'matched_brands': matched_brands
                            })
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"   Error in overlap search: {e}")
        
        return results
    
    def _deduplicate_companies(self, companies: List[Dict]) -> List[Dict]:
        """Deduplicate companies by domain and name similarity."""
        seen = set()
        deduped = []
        
        for company in companies:
            domain = company.get('domain', '').lower().strip() if company.get('domain') else None
            name = company.get('name', '').lower().strip() if company.get('name') else None
            
            # Create unique key
            if domain:
                key = f"domain:{domain}"
            elif name:
                # Normalize name for comparison
                normalized_name = re.sub(r'[^a-z0-9]', '', name)
                key = f"name:{normalized_name}"
            else:
                continue  # Skip entries without domain or name
            
            if key not in seen:
                seen.add(key)
                deduped.append(company)
            else:
                # Merge data if we have more info
                existing = next((c for c in deduped if self._get_key(c) == key), None)
                if existing:
                    # Update with any new information
                    for k, v in company.items():
                        if v and not existing.get(k):
                            existing[k] = v
                    
                    # Merge matched_brands lists
                    if 'matched_brands' in company and 'matched_brands' in existing:
                        existing_brands = set(existing.get('matched_brands', []))
                        new_brands = set(company.get('matched_brands', []))
                        existing['matched_brands'] = list(existing_brands | new_brands)
                    elif 'matched_brands' in company:
                        existing['matched_brands'] = company['matched_brands']
                    
                    # Also update brand matches tracking
                    if domain and domain in self.company_brand_matches:
                        existing_domain = existing.get('domain')
                        if existing_domain and existing_domain in self.company_brand_matches:
                            self.company_brand_matches[existing_domain].update(self.company_brand_matches[domain])
        
        return deduped
    
    def _get_key(self, company: Dict) -> str:
        """Get unique key for a company."""
        domain = company.get('domain', '').lower().strip() if company.get('domain') else None
        name = company.get('name', '').lower().strip() if company.get('name') else None
        
        if domain:
            return f"domain:{domain}"
        elif name:
            normalized_name = re.sub(r'[^a-z0-9]', '', name)
            return f"name:{normalized_name}"
        return ""
    
    def _infer_company_names(self, companies: List[Dict]) -> List[Dict]:
        """Infer company names from domains if missing."""
        for company in companies:
            if not company.get('name') and company.get('domain'):
                company['name'] = self._infer_name_from_domain(company['domain'])
        return companies
    
    def _infer_name_from_domain(self, domain: str) -> str:
        """Infer company name from domain."""
        if not domain:
            return "Unknown Company"
        
        # Remove TLD and www
        domain = normalize_domain(domain)
        parts = domain.split('.')
        if parts:
            main_part = parts[0]
            # Capitalize and add spaces for readability
            # e.g., "example-shop" -> "Example Shop"
            name = main_part.replace('-', ' ').replace('_', ' ')
            name = ' '.join(word.capitalize() for word in name.split())
            return name
        
        return "Unknown Company"
    
    async def _validate_brand_relevance(self, domain: str, matched_brands: List[str]) -> List[str]:
        """
        Validate brand relevance by checking if the website mentions the brands.
        
        Args:
            domain: Company domain
            matched_brands: List of brands to validate
            
        Returns:
            List of validated brands (brands that appear on the website)
        """
        if not domain or not matched_brands:
            return matched_brands
        
        validated_brands = []
        
        try:
            # Check homepage and common pages for brand mentions
            pages_to_check = [
                f"https://{domain}",
                f"https://{domain}/products",
                f"https://{domain}/shop",
                f"https://{domain}/collections",
            ]
            
            found_brands = set()
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                for page_url in pages_to_check[:2]:  # Check first 2 pages to save time
                    try:
                        response = await client.get(page_url)
                        if response.status_code == 200:
                            text = response.text.lower()
                            
                            # Check for brand mentions
                            for brand in matched_brands:
                                brand_lower = brand.lower()
                                # Check if brand name appears in text
                                if brand_lower in text:
                                    found_brands.add(brand)
                                # Also check for common variations
                                brand_words = brand_lower.split()
                                if len(brand_words) > 1:
                                    # Check if all words appear (for multi-word brands)
                                    if all(word in text for word in brand_words):
                                        found_brands.add(brand)
                    except Exception:
                        continue
            
            # If we found any brands, return those; otherwise return all (assume relevance)
            if found_brands:
                validated_brands = list(found_brands)
            else:
                # If no brands found but we have a domain, assume relevance (might be category overlap)
                validated_brands = matched_brands
                
        except Exception as e:
            logger.debug(f"   Error validating brand relevance for {domain}: {e}")
            # On error, assume all brands are relevant
            validated_brands = matched_brands
        
        return validated_brands if validated_brands else matched_brands
    
    async def save_to_supabase(self) -> Dict:
        """
        Save discovered companies and contacts to Supabase.
        
        Returns:
            Dictionary with save statistics
        """
        logger.info(f"\n💾 Saving {len(self.discovered_companies)} companies to Supabase...")
        
        companies_saved = 0
        companies_updated = 0
        contacts_saved = 0
        errors = 0
        
        for idx, company_data in enumerate(self.discovered_companies, 1):
            try:
                name = company_data.get('name')
                domain = company_data.get('domain')
                
                if not name:
                    logger.warning(f"   Skipping company {idx}: no name")
                    continue
                
                logger.info(f"\n   Processing {idx}/{len(self.discovered_companies)}: {name}")
                
                # Find domain if missing
                if not domain:
                    logger.info(f"   Finding domain for {name}...")
                    domain = find_domain(name)
                    if domain:
                        company_data['domain'] = domain
                
                # Enrich company if domain exists
                if domain:
                    logger.info(f"   Enriching company data for {domain}...")
                    enriched = enrich_company(domain)
                    for key, value in enriched.items():
                        if value and not company_data.get(key):
                            company_data[key] = value
                
                # Convert matched_brands to product_overlap list
                # Use tracked brand matches or matched_brands from company data
                matched_brands = company_data.get('matched_brands', [])
                if not matched_brands and domain:
                    # Check tracked brand matches
                    if domain in self.company_brand_matches:
                        matched_brands = list(self.company_brand_matches[domain])
                
                # If still no matches, use all brands (category overlap)
                if not matched_brands:
                    matched_brands = self.brand_names.copy()
                
                # Validate brand relevance if domain exists
                if domain and matched_brands:
                    validated_brands = await self._validate_brand_relevance(domain, matched_brands)
                    if validated_brands:
                        matched_brands = validated_brands
                    else:
                        # If validation fails, still keep matches but log warning
                        logger.warning(f"   Brand relevance validation failed for {domain}, keeping original matches")
                
                # Set product_overlap as list of matched brands
                company_data['product_overlap'] = matched_brands
                company_data['source'] = company_data.get('source', 'competitor_discovery')
                
                # Filter to valid fields
                filtered_company_data = filter_company_data(company_data)
                
                # Check if company already exists before upsert
                existing = None
                if domain:
                    existing = sb.table('companies').select('id').eq('domain', domain).limit(1).execute()
                elif name:
                    existing = sb.table('companies').select('id').eq('name', name).limit(1).execute()
                
                is_new = not (existing and existing.data and len(existing.data) > 0)
                
                # Upsert company
                company_response = sb.table('companies').upsert(filtered_company_data).execute()
                
                if company_response.data and len(company_response.data) > 0:
                    company_id = company_response.data[0].get('id')
                    
                    if is_new:
                        companies_saved += 1
                    else:
                        companies_updated += 1
                    
                    # Find emails if domain exists
                    if domain and company_id:
                        logger.info(f"   Finding emails for {domain}...")
                        email_results = find_emails(domain, name, verify=True)
                        
                        # Save top 5 contacts
                        for email, score in email_results[:5]:
                            contact_data = {
                                'company_id': company_id,
                                'name': None,
                                'email': email,
                                'confidence_score': score,
                            }
                            
                            # Verify contact
                            verification_result = verify_contact(contact_data)
                            contact_data.update({
                                'email': verification_result['email'],
                                'confidence_score': verification_result['confidence_score'],
                                'last_validated': verification_result.get('last_validated')
                            })
                            
                            # Filter to valid fields
                            filtered_contact_data = filter_contact_data(contact_data)
                            
                            # Upsert contact
                            sb.table('contacts').upsert(filtered_contact_data).execute()
                            contacts_saved += 1
                            logger.info(f"     ✓ Saved contact: {email} (score: {score:.2f})")
                else:
                    errors += 1
                    logger.warning(f"   Failed to save company: {name}")
                
            except Exception as e:
                errors += 1
                logger.error(f"   Error processing company {idx}: {e}")
                continue
        
        logger.info(f"\n✅ Save complete!")
        logger.info(f"   Companies saved: {companies_saved}")
        logger.info(f"   Companies updated: {companies_updated}")
        logger.info(f"   Contacts saved: {contacts_saved}")
        logger.info(f"   Errors: {errors}")
        
        return {
            'companies_saved': companies_saved,
            'companies_updated': companies_updated,
            'contacts_saved': contacts_saved,
            'errors': errors
        }
    
    def generate_report(self, discovery_stats: Dict, save_stats: Dict) -> str:
        """
        Generate a text report of the discovery process.
        
        Args:
            discovery_stats: Statistics from discovery process
            save_stats: Statistics from save process
            
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("COMPETITOR DISCOVERY REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Brands Searched: {', '.join(self.brand_names)}")
        report.append("")
        report.append("DISCOVERY STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Companies Discovered: {discovery_stats['total_discovered']}")
        report.append("")
        report.append("By Strategy:")
        for strategy, count in discovery_stats['by_strategy'].items():
            strategy_name = strategy.replace('_', ' ').title()
            report.append(f"  • {strategy_name}: {count}")
        report.append(f"After Deduplication: {discovery_stats['after_deduplication']}")
        report.append("")
        report.append("SAVE STATISTICS")
        report.append("-" * 80)
        report.append(f"Companies Saved: {save_stats['companies_saved']}")
        report.append(f"Companies Updated: {save_stats['companies_updated']}")
        report.append(f"Contacts Saved: {save_stats['contacts_saved']}")
        report.append(f"Errors: {save_stats['errors']}")
        report.append("")
        report.append("DISCOVERED COMPANIES")
        report.append("-" * 80)
        
        for idx, company in enumerate(self.discovered_companies, 1):
            name = company.get('name', 'Unknown')
            domain = company.get('domain', 'N/A')
            source = company.get('source', 'unknown')
            product_overlap = company.get('product_overlap', [])
            
            report.append(f"{idx}. {name}")
            report.append(f"   Domain: {domain}")
            report.append(f"   Source: {source}")
            if product_overlap:
                if isinstance(product_overlap, list):
                    report.append(f"   Product Overlap: {', '.join(product_overlap)}")
                else:
                    report.append(f"   Product Overlap: {product_overlap}")
            if company.get('brand_focus'):
                report.append(f"   Brand Focus: {company.get('brand_focus')}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)

