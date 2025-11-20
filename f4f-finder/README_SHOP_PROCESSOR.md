# Shop List Processor

This system processes CSV or PDF files containing shop data (names and addresses), finds their websites/domains, discovers email addresses, and automatically saves everything to Supabase.

## Features

- **CSV/PDF Processing**: Extracts shop names and addresses from CSV or PDF files
- **Domain Finding**: Automatically finds website domains from company names and addresses
- **Email Discovery**: Finds and verifies email addresses from domains
- **Database Integration**: Automatically saves companies and contacts to Supabase
- **Async Processing**: Uses Celery for background processing of large files

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (`.env` file):
```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SERPER_API_KEY=your_serper_api_key  # Required for domain finding via Serper.dev
REDIS_URL=redis://localhost:6379/0  # Optional, for Celery
```

3. Start Redis (if using Celery):
```bash
redis-server
```

4. Start Celery worker (if using Celery):
```bash
celery -A celery_app worker --loglevel=info
```

## Usage

### Basic Usage

Process a CSV or PDF file:

```bash
python process_shop_list.py D://shop_list.pdf
```

Or specify a different file:
```bash
python process_shop_list.py path/to/your/file.csv
```

### CSV Format

The CSV file should have columns for shop name and address. The processor will automatically detect common column names:

**Name columns** (case-insensitive):
- `name`, `shop_name`, `store_name`, `business_name`, `company_name`, `company`, `shop`, `store`

**Address columns** (case-insensitive):
- `address`, `street_address`, `location`, `addr`, `full_address`

Or you can have separate columns that will be combined:
- `street`, `city`, `state`, `zip`, `postal_code`, `country`

### PDF Format

The processor can extract data from PDF files, but the parsing is heuristic-based. For best results, use CSV format.

### Processing Flow

1. **File Processing**: Extracts shop names and addresses from the file
2. **Domain Finding**: For each shop, generates domain candidates and checks if they exist
3. **Email Discovery**: For each found domain:
   - Scrapes the website for email addresses
   - Generates common email patterns (info@, contact@, etc.)
   - Verifies all found emails
4. **Database Save**: Saves companies and contacts to Supabase

### Running Synchronously vs. Asynchronously

- **Without Redis/Celery**: The script runs synchronously (not recommended for large files)
- **With Redis/Celery**: The script runs as a Celery task in the background

### Monitoring Progress

If running with Celery, you can monitor the task:

```bash
# Check active tasks
celery -A celery_app inspect active

# Check task result
celery -A celery_app result <task_id>
```

## Output

The processor saves data to two Supabase tables:

### Companies Table
- `name`: Shop name
- `domain`: Found website domain
- `source`: Source identifier (default: "csv_upload")
- Other enriched fields (country, region, etc.) if available

### Contacts Table
- `company_id`: Reference to the company
- `email`: Found and verified email address
- `confidence_score`: Email verification score (0.0-1.0)
- `last_validated`: Timestamp of verification

## Configuration

### Domain Finding

The domain finder uses multiple strategies:
1. **Primary**: Searches using Serper.dev API with company name + city/country
   - Filters out directory sites (Yelp, Facebook, Tripadvisor, etc.)
   - Returns the best homepage candidate + domain
2. **Fallback**: Generates domain candidates from company name
   - Checks if domains exist (DNS lookup)
   - Verifies domains are active (HTTP/HTTPS)
   - Returns the first valid domain found

### Email Finding

The email finder uses multiple strategies:
1. **Primary**: Scrapes specific website pages for email addresses
   - Visits: `/`, `/contact`, `/about`, `/impressum`
   - Extracts emails using regex
   - Filters out spammy/automated emails (noreply, notifications, etc.)
2. **Fallback**: If no emails found, generates fallback guesses:
   - `info@domain`
   - `sales@domain`
   - `contact@domain`
3. **Verification**: Verifies all emails using DNS, MX records, and optional SMTP checks
4. Returns verified emails sorted by confidence score (best match first)

## Troubleshooting

### File Not Found
Make sure the file path is correct. On Windows, use forward slashes or double backslashes:
```
D://shop_list.pdf
D:\\shop_list.pdf
```

### No Domains Found
- Check if company names are clear and readable
- Some shops may not have websites
- The domain finder uses heuristics and may not find all domains

### No Emails Found
- Some domains may not have publicly listed emails
- Email verification is strict and may filter out some emails
- Check the logs for verification scores

### Processing Takes Too Long
- For large files (2000+ shops), use Celery for background processing
- Consider processing in batches
- Domain and email finding involves network requests and can be slow

## Limitations

- PDF parsing is heuristic-based and may not work perfectly for all PDF formats
- Domain finding relies on heuristics and may not find all domains
- Email finding may not discover all emails (depends on website structure)
- Processing time depends on network speed and number of shops

## Future Enhancements

- Google Custom Search API integration for better domain finding
- More sophisticated PDF parsing
- Batch processing with progress tracking
- Web UI for file upload and monitoring

