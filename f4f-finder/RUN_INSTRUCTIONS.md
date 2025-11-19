# How to Run Shop Data Processing

## Quick Start

### 1. Basic Run (Process Your Shop List)

```powershell
cd C:\dev\f4f-leads\f4f-finder
python process_shop_list.py D://shop_list.pdf
```

Or with a CSV file:
```powershell
python process_shop_list.py "path\to\your\shops.csv"
```

### 2. What Happens

The script will:
1. ✅ Read your PDF/CSV file
2. ✅ Extract shop names and addresses
3. ✅ Find domains/websites for each shop
4. ✅ Discover and verify email addresses
5. ✅ Save everything to Supabase automatically

You'll see real-time progress logs like:
```
🚀 Starting CSV/PDF processing: D://shop_list.pdf
Extracted 2000 shops from file
Processing shop 1/2000: Shop Name
🔍 Finding domain for: Shop Name
   ✅ Found domain: shopname.com
📧 Finding emails for domain: shopname.com
   ✅ Found 3 verified emails
✅ Completed shop 1/2000: Shop Name
```

## Automation Options

### Option 1: Windows Task Scheduler (Recommended for Windows)

1. **Create a batch file** (`run_shop_processor.bat`):
```batch
@echo off
cd C:\dev\f4f-leads\f4f-finder
python process_shop_list.py D://shop_list.pdf
pause
```

2. **Set up Windows Task Scheduler**:
   - Open Task Scheduler
   - Create Basic Task
   - Set trigger (daily, weekly, etc.)
   - Set action to run the batch file

### Option 2: Python Script with Scheduling

Create `auto_process.py`:
```python
import schedule
import time
from process_shop_list import main

# Schedule to run daily at 2 AM
schedule.every().day.at("02:00").do(main)

while True:
    schedule.run_pending()
    time.sleep(60)
```

Run it:
```powershell
python auto_process.py
```

### Option 3: One-Time Run with Logging

Create `run_with_logging.bat`:
```batch
@echo off
cd C:\dev\f4f-leads\f4f-finder
python process_shop_list.py D://shop_list.pdf > processing_log_%date:~-4,4%%date:~-7,2%%date:~-10,2%.txt 2>&1
```

This saves all output to a dated log file.

## Monitoring Progress

### Check Supabase Database

After processing, check your Supabase database:
- `companies` table - all shops with domains
- `contacts` table - all found email addresses

### View Logs

The script outputs detailed logs showing:
- Which shops were processed
- Domains found
- Emails discovered
- Any errors encountered

## Processing Large Files

For 2000+ shops:
- **Time**: Expect several hours (each shop requires network requests)
- **Progress**: Watch the terminal for real-time updates
- **Resumable**: If interrupted, you can re-run (it will skip duplicates based on domain/name)

## Troubleshooting

### File Not Found
```powershell
# Use forward slashes or double backslashes
python process_shop_list.py D://shop_list.pdf
python process_shop_list.py D:\\shop_list.pdf
```

### Missing Dependencies
```powershell
pip install -r requirements.txt
```

### Supabase Connection Issues
- Check your `.env` file has correct credentials
- Verify Supabase is accessible

## Advanced: Process Multiple Files

Create `process_multiple_files.py`:
```python
import os
from process_shop_list import main
from pathlib import Path

files_to_process = [
    "D://shop_list.pdf",
    "D://shop_list_2.csv",
    # Add more files
]

for file_path in files_to_process:
    if Path(file_path).exists():
        print(f"Processing {file_path}...")
        # Modify main() to accept file path, or call the function directly
        # main(file_path)
    else:
        print(f"File not found: {file_path}")
```

