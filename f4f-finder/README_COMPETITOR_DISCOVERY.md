# Competitor Discovery

This module discovers retailers and sellers that carry competitor brands through multiple discovery strategies.

## Features

The competitor discovery system:

1. **Runs all discovery strategies:**
   - **Brand-site scraping**: Finds retailers listed on brand websites (where-to-buy pages, retailer lists, etc.)
   - **Marketplace search**: Discovers sellers on eBay, Amazon, Etsy, and other marketplaces
   - **Convention vendor lists**: Finds retailers from convention/expo vendor lists
   - **Overlap search**: Discovers stores selling similar/overlapping products

2. **Deduplicates results** by domain and name similarity

3. **Infers company names** from domains when missing

4. **Inserts/updates companies** in Supabase with `product_overlap` flag set

5. **Discovers emails** with confidence scores

6. **Inserts/updates contacts** in Supabase

7. **Generates a comprehensive report** with statistics and discovered companies

## Usage

### Direct Python Script

Run the discovery directly:

```bash
cd f4f-finder
python run_competitor_discovery.py
```

Or with custom brands:

```bash
python run_competitor_discovery.py "Funko" "Tubbz" "Cable guys"
```

### Celery Task

Run as a Celery task:

```python
from tasks import discover_competitors

# Run discovery
result = discover_competitors.delay(["Funko", "Tubbz", "Cable guys"])

# Check status
print(result.status)

# Get result
result_data = result.get()
```

## Configuration

The discovery system requires:

- **SERPER_API_KEY**: Environment variable for Serper.dev API (used for search)
- **Supabase credentials**: Already configured in `supabase_client.py`

## Discovery Strategies

### 1. Brand Website Retailer Lists

Searches for and scrapes retailer lists from brand websites. Looks for common page patterns:
- `/where-to-buy`
- `/retailers`
- `/find-a-store`
- `/stockists`
- `/dealers`
- `/partners`
- `/stores`

### 2. Marketplace Sellers

Searches for sellers on:
- **eBay**: Finds sellers listing products from the brand
- **Amazon**: Finds Amazon stores and sellers
- **Etsy**: Finds Etsy shops selling the brand

### 3. Convention Vendor Lists

Searches for and scrapes vendor/exhibitor lists from:
- Comic cons
- Toy fairs
- Collectibles expos
- Pop culture conventions
- Anime conventions
- Gaming conventions

### 4. Overlap Search

Searches for stores selling similar products using queries like:
- "stores selling [brand] collectibles"
- "pop culture collectibles stores"
- "vinyl figure retailers"
- "anime collectibles shops"
- "gaming merchandise stores"

## Output

The system generates:

1. **Console output**: Real-time logging of discovery progress
2. **Supabase database**: Companies and contacts saved/updated
3. **Report file**: `competitor_discovery_report.txt` with:
   - Discovery statistics by strategy
   - Save statistics (companies saved/updated, contacts saved)
   - Full list of discovered companies with details

## Report Format

```
================================================================================
COMPETITOR DISCOVERY REPORT
================================================================================

Brands Searched: Funko, Tubbz, Cable guys

DISCOVERY STATISTICS
--------------------------------------------------------------------------------
Total Companies Discovered: 150
After Deduplication: 120

By Strategy:
  • Brand Sites: 45
  • Marketplaces: 60
  • Conventions: 20
  • Overlap: 25

SAVE STATISTICS
--------------------------------------------------------------------------------
Companies Saved: 80
Companies Updated: 40
Contacts Saved: 200
Errors: 0

DISCOVERED COMPANIES
--------------------------------------------------------------------------------
1. Example Retailer
   Domain: exampleretailer.com
   Source: brand_site
   Brand Focus: Funko
...
```

## Database Schema

Companies are saved with:
- `name`: Company name
- `domain`: Website domain
- `source`: Discovery source (brand_site, marketplace_ebay, marketplace_amazon, marketplace_etsy, convention, overlap_search)
- `brand_focus`: Brand name if discovered from brand-specific search
- `product_overlap`: Always set to `true` for competitor-discovered companies
- Other fields: country, region, type (enriched from Clearbit if available)

Contacts are saved with:
- `company_id`: Reference to company
- `email`: Email address
- `confidence_score`: Confidence score (0.0-1.0)
- `last_validated`: Timestamp of last validation

## Notes

- The discovery process can take a while depending on the number of brands and search results
- Some marketplace sellers may not have domains (e.g., eBay sellers)
- Convention vendor lists may vary in format and accessibility
- Email discovery only runs for companies with valid domains
- The system automatically deduplicates by domain and normalized name

