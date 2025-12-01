# Scraping Methods Overview

This document provides a comprehensive overview of the three main data discovery/scraping methods in the F4F Leads project.

---

## 1. LinkedIn Scraping

### Purpose
Find companies and contacts on LinkedIn based on keyword searches (e.g., "retail buyer", "collectibles", "pop culture").

### How It Works

**Entry Point:**
- Celery Task: `scrape_linkedin_companies(keyword)`
- File: `f4f-finder/scraper/linkedin_scraper.py`

**Process Flow:**

1. **Authentication**
   - Uses Playwright to automate browser
   - Logs into LinkedIn with credentials from `.env`
   - Handles 2FA/verification codes (from `LINKEDIN_VERIFICATION_CODE` env var)
   - Saves browser state (cookies/session) to `.linkedin_state.json` for reuse

2. **Search & Scraping**
   - Searches LinkedIn companies using keyword: `https://www.linkedin.com/search/results/companies/?keywords={keyword}`
   - Extracts company information:
     - Company name
     - LinkedIn URL
     - Website domain
     - Industry
     - Company size
     - Location
   - Visits each company's `/about/` page for detailed info
   - Extracts contacts (employees) from company pages:
     - Name
     - LinkedIn URL
     - Title/Position
     - Phone (if available)

3. **Data Processing**
   - Enriches company data using Clearbit (if domain available)
   - Infers missing domains using domain finder
   - Validates and filters data

4. **Database Storage**
   - Upserts companies to `companies` table
   - Sets `source = "linkedin"`
   - Sets `brand_focus = {keyword}` (the search term)
   - Upserts contacts to `contacts` table with:
     - `company_id` reference
     - `linkedin_url`
     - `phone` (if found)
     - `title`

**Key Features:**
- ✅ Browser automation with Playwright
- ✅ Session persistence (saves login state)
- ✅ Handles LinkedIn verification codes
- ✅ Extracts both company and contact data
- ✅ Automatic enrichment with Clearbit
- ✅ Can run as Celery task (async) or directly

**Usage:**
```python
from tasks import scrape_linkedin_companies

# As Celery task
result = scrape_linkedin_companies.delay("retail buyer")

# Or directly
result = scrape_linkedin_companies("collectibles")
```

**Output:**
- Companies saved to Supabase with LinkedIn data
- Contacts saved with LinkedIn profiles
- Returns: `{'companies_saved': X, 'contacts_saved': Y, 'total_processed': Z}`

---

## 2. CSV/PDF Parsing

### Purpose
Process uploaded shop lists from CSV or PDF files (e.g., retailer lists, vendor lists, service lists).

### How It Works

**Entry Points:**
- Celery Task: `process_shop_csv(file_path, source="csv_upload")`
- Sync Script: `process_shop_list_sync.py` (Windows-compatible, no Celery)
- Main Script: `process_shop_list.py`
- File: `f4f-finder/processors/csv_processor.py`

**Process Flow:**

1. **File Processing**
   - Supports both CSV and PDF files
   - **CSV**: Reads directly, expects columns like "Name", "Address", "City", etc.
   - **PDF**: Uses `pdfplumber` (primary) or `PyPDF2` (fallback) to extract tables
   - Detects header rows automatically
   - Normalizes shop data (cleans names, addresses)

2. **Caching**
   - Saves extracted data to `.cache/{filename}.json`
   - Reuses cache if source file hasn't changed
   - Can force re-extraction with `--force` flag

3. **Domain Discovery**
   - For each shop, finds website domain using:
     - Serper.dev API search (primary)
     - Domain candidate generation (fallback)
   - Uses shop name + address for better accuracy

4. **Company Enrichment**
   - Enriches company data with Clearbit (if domain found)
   - Extracts country/region from address
   - Parses address components

5. **Email Discovery**
   - Scrapes website for emails (`/`, `/contact`, `/about`, `/impressum`)
   - Generates email candidates (info@, sales@, etc.)
   - Verifies emails and assigns confidence scores

6. **Contact Verification**
   - Verifies each email address
   - Calculates confidence scores
   - Validates email format, domain, SMTP

7. **Database Storage**
   - Upserts companies to `companies` table
   - Sets `source = {source}` (default: "csv_upload")
   - Sets `country` and `region` from parsed address
   - Upserts contacts to `contacts` table with:
     - `email`
     - `confidence_score`
     - `last_validated` timestamp

**Key Features:**
- ✅ Supports CSV and PDF files
- ✅ Automatic table detection in PDFs
- ✅ Caching system (avoids re-processing)
- ✅ Address parsing (extracts country, region, city)
- ✅ Domain finding with multiple strategies
- ✅ Email discovery and verification
- ✅ Windows-compatible sync version (no Celery)

**Usage:**
```python
from tasks import process_shop_csv

# As Celery task
result = process_shop_csv.delay("path/to/shops.csv", source="vendor_list")

# Or sync (Windows-friendly)
from process_shop_list_sync import process_shop_file_sync
result = process_shop_file_sync("path/to/shops.pdf", source="retailer_list")
```

**Output:**
- Companies saved with domain, location data
- Contacts saved with verified emails
- Returns: `{'companies_saved': X, 'contacts_saved': Y, 'errors': Z}`

---

## 3. Competitor Discovery

### Purpose
Automatically discover retailers that sell competitor brands (e.g., Funko, Tubbz, Cable Guys) using multiple discovery strategies.

### How It Works

**Entry Points:**
- Celery Task: `discover_competitors(brand_names)`
- Main Script: `run_competitor_discovery.py`
- File: `f4f-finder/discovery/competitor_discovery.py`

**Process Flow:**

1. **Strategy 1: Brand Website Retailer Lists**
   - Finds official brand websites using Serper.dev (checks ALL results, not just first)
   - Tries multiple potential brand domains
   - Scrapes retailer list pages:
     - `/where-to-buy`
     - `/store-locator`
     - `/stockists`
     - `/retailers`
     - `/distributors`
     - `/partners`
     - `/find-a-store`
     - `/dealers`
     - `/stores`
     - `/collections` (e.g., EXGPro Cable Guys)
   - Checks ALL pages (not just first working one)
   - Extracts retailer links, embedded maps, stockist grids

2. **Strategy 2: Marketplace Sellers**
   - Searches multiple marketplaces for brand sellers:
     - **eBay**: Finds sellers listing products
     - **Amazon**: Finds Amazon stores and sellers
     - **Etsy**: Finds Etsy shops
     - **Walmart Marketplace**: Finds Walmart sellers
     - **MercadoLibre**: Finds LatAm sellers
     - **Shopee**: Finds Asian sellers
     - **Lazada**: Finds Asian sellers
     - **AliExpress**: Finds China/Global sellers
   - Extracts seller/store names and external websites

3. **Strategy 3: Convention Vendor Lists**
   - Searches for convention/expo vendor lists:
     - Brand-specific: "Funko vendor list", "Tubbz exhibitors"
     - General: "comic con vendor list", "toy fair exhibitors"
     - Year-specific: "comic con 2024 vendors"
   - Scrapes vendor list pages from conventions
   - Extracts vendor names and websites

4. **Strategy 4: Overlap Search**
   - Searches for stores with overlapping products:
     - Brand-specific: "{brand} collectibles store", "{brand} retailer"
     - Category-based: "pop culture collectibles store", "vinyl figure retailer"
   - Uses Serper.dev to find stores selling similar products
   - Identifies category overlap

5. **Deduplication**
   - Deduplicates by domain and normalized name
   - Merges brand matches when same company found multiple times
   - Tracks which brands each company matches

6. **Brand Matching & Validation**
   - Tracks which brands each retailer matches
   - Validates brand relevance by checking if website mentions brands
   - Sets `product_overlap` as list of matched brands (e.g., `["Funko", "Tubbz"]`)

7. **Company Processing**
   - Infers company names from domains if missing
   - Finds domains for companies without them
   - Enriches with Clearbit data

8. **Email Discovery**
   - Automatically discovers emails for companies with domains
   - Scrapes website pages
   - Verifies emails and assigns confidence scores

9. **Database Storage**
   - Upserts companies to `companies` table
   - Sets `source = "competitor_discovery_*"` (with strategy suffix)
   - Sets `product_overlap = [list of matched brands]` (not boolean!)
   - Sets `brand_focus` if discovered from brand-specific search
   - Upserts contacts with verified emails

**Key Features:**
- ✅ 4 discovery strategies (brand sites, marketplaces, conventions, overlap)
- ✅ Checks ALL Serper.dev results (not just first)
- ✅ Checks ALL retailer pages (not just first working one)
- ✅ 8 marketplace integrations
- ✅ Brand relevance validation
- ✅ Product overlap tracking (list of brands)
- ✅ Automatic email discovery
- ✅ Comprehensive deduplication

**Usage:**
```python
from tasks import discover_competitors

# As Celery task
result = discover_competitors.delay(["Funko", "Tubbz", "Cable guys"])

# Or directly
python run_competitor_discovery.py "Funko" "Tubbz" "Cable guys"
```

**Output:**
- Companies saved with `product_overlap` list
- Contacts saved with emails
- Report generated: `competitor_discovery_report.txt`
- Returns: `{'discovery_stats': {...}, 'save_stats': {...}, 'report': '...'}`

---

## Comparison Table

| Feature | LinkedIn | CSV/PDF | Competitor Discovery |
|---------|----------|---------|---------------------|
| **Input** | Keyword | File (CSV/PDF) | Brand names |
| **Primary Source** | LinkedIn | Uploaded files | Web (brand sites, marketplaces, conventions) |
| **Company Data** | ✅ | ✅ | ✅ |
| **Contact Data** | ✅ (LinkedIn profiles) | ✅ (Emails) | ✅ (Emails) |
| **Domain Finding** | ✅ (enrichment) | ✅ (primary) | ✅ (primary) |
| **Email Discovery** | ❌ | ✅ | ✅ |
| **Enrichment** | ✅ (Clearbit) | ✅ (Clearbit) | ✅ (Clearbit) |
| **Deduplication** | ✅ (by domain) | ✅ (by domain) | ✅ (by domain + name) |
| **Brand Tracking** | ✅ (`brand_focus`) | ❌ | ✅ (`product_overlap` list) |
| **Source Tagging** | `linkedin` | `csv_upload` (custom) | `competitor_discovery_*` |
| **Async Support** | ✅ (Celery) | ✅ (Celery + Sync) | ✅ (Celery) |
| **Windows Compatible** | ✅ | ✅ (sync version) | ✅ |

---

## Data Flow Summary

### All Methods Follow Similar Pattern:

1. **Discovery/Extraction** → Find companies and contacts
2. **Enrichment** → Add domain, location, company data
3. **Validation** → Verify emails, domains, data quality
4. **Deduplication** → Remove duplicates
5. **Storage** → Save to Supabase (companies + contacts)

### Database Schema:

**Companies Table:**
- `name`, `domain`, `country`, `region`, `type`
- `source` (identifies discovery method)
- `brand_focus` (keyword/brand from LinkedIn/competitor discovery)
- `product_overlap` (list of brands - competitor discovery only)
- `status`, `freshness_timestamp`

**Contacts Table:**
- `company_id` (reference to company)
- `name`, `email`, `phone`, `title`
- `linkedin_url` (LinkedIn scraping)
- `confidence_score`, `last_validated`

---

## When to Use Each Method

### Use LinkedIn Scraping When:
- You want to find companies by industry/keyword
- You need LinkedIn profiles for contacts
- You're looking for decision-makers (buyers, managers)
- You want to target specific roles/titles

### Use CSV/PDF Parsing When:
- You have existing lists of shops/retailers
- You need to process vendor lists, service lists, etc.
- You want to bulk import known retailers
- You have structured data (name + address)

### Use Competitor Discovery When:
- You want to find retailers selling competitor products
- You need to discover new leads automatically
- You want comprehensive coverage (brand sites + marketplaces + conventions)
- You need to track which brands each retailer matches
- You want the highest-quality leads with lowest manual effort

---

## Integration Points

All three methods:
- Use the same Supabase database
- Share enrichment functions (Clearbit, domain finder, email finder)
- Use the same contact verification system
- Can run as Celery tasks or directly
- Generate logs and statistics
- Handle errors gracefully with retries

---

## Next Steps After Discovery

After any scraping method:
1. **LinkedIn Enrichment** (second layer) - Find specific contacts at discovered companies
2. **Email Verification** - Verify discovered emails
3. **Outreach** - Use n8n workflows for automated outreach
4. **Analytics** - Track performance by source, brand, region

