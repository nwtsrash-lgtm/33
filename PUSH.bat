@echo off
cd /d "%~dp0"
echo.
echo   جاري رفع التحديثات...
echo.

git add -A
git commit -m "fix: NO field + competitors count + scraping improvements"
git push origin master

if %errorlevel% equ 0 (
    echo.
    echo   [OK] تم الرفع بنجاح!
) else (
    echo.
    echo   جاري المحاولة على main...
    git push origin main
)

echo.
pause
