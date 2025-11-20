# Quick Start Guide - Shop List Processor

## Step 1: Install Dependencies

```bash
cd f4f-finder
pip install -r requirements.txt
```

## Step 2: Set Up Environment Variables

Create a `.env` file in the `f4f-finder` folder (or ensure your existing `.env` has these):

```env
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
SERPER_API_KEY=your_serper_api_key_here  # Required for domain finding
REDIS_URL=redis://localhost:6379/0  # Optional - only needed for async processing
```

**Note:** If you don't set `REDIS_URL`, the script will run synchronously (which is fine for testing, but slower for large files).

## Step 3: Run the Processor

### Option A: Simple Run (Synchronous - No Redis needed)

```bash
python process_shop_list.py D://shop_list.pdf
```

Or specify a different file:
```bash
python process_shop_list.py path/to/your/file.csv
```

### Option B: Async Run (Recommended for large files - Requires Redis)

1. **Start Redis** (if not already running):
   ```bash
   redis-server
   ```

2. **Start Celery Worker** (in a separate terminal):
   ```bash
   cd f4f-finder
   celery -A celery_app worker --loglevel=info
   ```

3. **Run the processor**:
   ```bash
   python process_shop_list.py D://shop_list.pdf
   ```

4. **Monitor progress** (in another terminal):
   ```bash
   celery -A celery_app inspect active
   ```

## What Happens

The script will:
1. ✅ Read your PDF/CSV file
2. ✅ Extract shop names and addresses
3. ✅ Find domains/websites for each shop
4. ✅ Discover and verify email addresses
5. ✅ Save everything to Supabase (companies and contacts tables)

## Expected Output

You'll see progress logs like:
```
🚀 Starting CSV/PDF processing: D://shop_list.pdf
Extracted 2000 shops from file
Processing shop 1/2000: Shop Name
🔍 Finding domain for: Shop Name
   ✅ Found domain: shopname.com
📧 Finding emails for domain: shopname.com
   ✅ Found 3 verified emails
✅ Completed shop 1/2000: Shop Name
...
```

## Troubleshooting

### File Not Found
- Make sure the file path is correct
- On Windows, use forward slashes: `D://shop_list.pdf` or double backslashes: `D:\\shop_list.pdf`

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Supabase Connection Error
- Check your `.env` file has correct `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- Make sure Supabase is accessible

### Slow Processing
- For 2000+ shops, this will take time (each shop requires network requests)
- Consider using Celery for background processing
- Processing time depends on network speed

## CSV Format

Your CSV should have columns like:
- `name` or `shop_name` or `company_name` (for shop name)
- `address` or `street_address` or `location` (for address)

Or separate columns that will be combined:
- `street`, `city`, `state`, `zip`, `country`

The processor automatically detects common column name variations.

