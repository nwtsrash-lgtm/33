@echo off
chcp 65001 >nul 2>&1
title إعداد جدار الحماية — مهووس

echo.
echo   جاري فتح جدار الحماية لتطبيق مهووس...
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] يحتاج صلاحية مسؤول — جاري إعادة التشغيل...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

netsh advfirewall firewall delete rule name="Mahwous" >nul 2>&1
netsh advfirewall firewall add rule name="Mahwous" dir=in action=allow protocol=TCP localport=8502
netsh advfirewall firewall add rule name="Mahwous" dir=out action=allow protocol=TCP localport=8502

echo.
echo   [OK] تم فتح المنفذ 8502
echo.
echo   الآن شغّل: تشغيل_على_الشبكة.bat
echo.
pause
