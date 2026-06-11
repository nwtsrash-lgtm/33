@echo off
title Mahwous
cd /d "%~dp0"

:: فتح جدار الحماية
powershell -Command "Start-Process powershell -ArgumentList '-Command netsh advfirewall firewall add rule name=Mahwous dir=in action=allow protocol=TCP localport=8502' -Verb RunAs -Wait" 2>nul

:: تثبيت المكتبات أول مرة
if not exist ".venv_ready" (
    echo Installing...
    pip install -r requirements.txt --quiet --disable-pip-version-check
    echo OK > .venv_ready
)

:: فتح المتصفح
start http://localhost:8502

:: تشغيل التطبيق
streamlit run app.py --server.address 0.0.0.0 --server.port 8502 --server.fileWatcherType none
pause
