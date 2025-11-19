# Quick Run Guide - Shop Data Processing

## 🚀 One-Time Run (Process Your Shop List Now)

### Simple Command:
```powershell
cd C:\dev\f4f-leads\f4f-finder
python process_shop_list.py D://shop_list.pdf
```

### What It Does:
1. Reads your PDF/CSV file
2. Extracts shop names and addresses  
3. Finds domains/websites for each shop
4. Discovers and verifies email addresses
5. Saves everything to Supabase automatically

### Watch Progress:
You'll see real-time logs showing each shop being processed:
```
Processing shop 1/2000: Shop Name
🔍 Finding domain...
   ✅ Found domain: shopname.com
📧 Finding emails...
   ✅ Found 3 verified emails
✅ Completed shop 1/2000
```

---

## 🔄 Automation Options

### Option 1: Windows Task Scheduler (Easiest)

1. **Double-click the batch file:**
   ```
   run_shop_processor.bat
   ```

2. **Or set up Windows Task Scheduler:**
   - Open Task Scheduler
   - Create Basic Task
   - Set trigger (daily/weekly/etc.)
   - Action: Run `run_shop_processor.bat`

### Option 2: Python Scheduler (More Flexible)

**Install schedule library:**
```powershell
pip install schedule
```

**Run automated processing:**
```powershell
# Daily at 2 AM (default)
python auto_process.py D://shop_list.pdf

# Daily at specific time
python auto_process.py D://shop_list.pdf 03:00

# Hourly
python auto_process.py D://shop_list.pdf hourly

# Weekly (Mondays at 2 AM)
python auto_process.py D://shop_list.pdf weekly
```

The script will:
- Run immediately once
- Then run on your schedule
- Keep running until you stop it (Ctrl+C)

---

## 📋 Prerequisites

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Set up `.env` file** with:
   ```
   SUPABASE_URL=your_url
   SUPABASE_SERVICE_ROLE_KEY=your_key
   ```

3. **Have your shop list file ready:**
   - PDF or CSV format
   - Should have shop names and addresses

---

## 🎯 Quick Examples

### Process a CSV file:
```powershell
python process_shop_list.py "C:\data\shops.csv"
```

### Process with custom source tag:
```powershell
python process_shop_list.py D://shop_list.pdf
# Source will be "csv_upload" by default
```

### Run batch file:
```powershell
.\run_shop_processor.bat
```

---

## 📊 Check Results

After processing, check your Supabase database:
- **companies** table → All shops with domains
- **contacts** table → All found email addresses

---

## ⚠️ Important Notes

- **Processing time**: For 2000 shops, expect several hours
- **Network required**: Each shop requires internet requests
- **Resumable**: Can re-run if interrupted (skips duplicates)
- **Windows compatible**: Runs synchronously on Windows (no Celery needed)

---

## 🆘 Troubleshooting

**File not found?**
```powershell
# Use forward slashes
python process_shop_list.py D://shop_list.pdf
```

**Missing dependencies?**
```powershell
pip install -r requirements.txt
```

**Need help?** Check `RUN_INSTRUCTIONS.md` for detailed guide.

