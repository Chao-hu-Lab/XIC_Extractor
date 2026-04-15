@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   XIC Extractor - 標準品 Excel 轉 targets
echo ============================================
echo.
echo 請選擇要轉換的分頁：
echo   1. DNA   （NL = dR, 116.0474 Da）
echo   2. RNA   （NL = R / MeR 自動偵測）
echo   3. DNA + RNA 合併
echo.
choice /c 123 /n /m "請輸入 1、2 或 3： "

if errorlevel 3 (
    set SHEET=both
) else if errorlevel 2 (
    set SHEET=RNA
) else (
    set SHEET=DNA
)

echo.
echo 已選擇: %SHEET%
echo.
echo 正在開啟選檔視窗，請選擇 RT 標準品 Excel 檔...
echo.

uv run python scripts\xlsx_to_targets.py --sheet %SHEET%

echo.
echo ============================================
echo  完成！已輸出至 config\ 資料夾
echo  檔名格式：^<Excel 檔名^>_targets_%SHEET%.csv
echo  確認無誤後將檔名改為 targets.csv 即可使用
echo ============================================
echo.
pause
