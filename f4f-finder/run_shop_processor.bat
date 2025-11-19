@echo off
REM Automated Shop Data Processing Script
REM This script processes shop lists and saves to Supabase

echo ========================================
echo Shop Data Processing
echo ========================================
echo.

cd /d "%~dp0"

REM Set the file path (change this to your file)
set SHOP_FILE=D://shop_list.pdf

echo Processing file: %SHOP_FILE%
echo.

REM Run the processor
python process_shop_list.py "%SHOP_FILE%"

echo.
echo ========================================
echo Processing Complete
echo ========================================
echo.

REM Optional: Keep window open to see results
pause

