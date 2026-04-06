@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "SCRIPTS=%ROOT%scripts"
set "OUTPUT=%ROOT%output"

echo ============================================================
echo  XIC Extractor Pipeline
echo ============================================================
echo.

:: Step 1 - Extract RT and Intensity from .raw files
echo [Step 1/2] Extracting XIC data from .raw files...
powershell -ExecutionPolicy Bypass -File "%SCRIPTS%\01_extract_xic.ps1"
if errorlevel 1 (
    echo.
    echo ERROR: Step 1 failed. Check the error message above.
    pause
    exit /b 1
)

echo.
:: Step 2 - Convert CSV to Excel
echo [Step 2/2] Generating Excel report...
python "%SCRIPTS%\02_csv_to_excel.py"
if errorlevel 1 (
    echo.
    echo ERROR: Step 2 failed. Make sure Python and openpyxl are installed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done! Results saved to:
echo  %OUTPUT%\xic_results.csv
echo  %OUTPUT%\xic_results.xlsx
echo ============================================================
pause
