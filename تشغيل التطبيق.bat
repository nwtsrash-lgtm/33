@echo off
chcp 65001 >nul
title نظام التسعير الذكي - مهوس
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   نظام التسعير الذكي - مهوس mahwous     ║
echo  ║   جاري تشغيل التطبيق...                 ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python غير مثبت! يرجى تثبيت Python 3.10+
    pause
    exit /b 1
)

:: Install requirements if needed
if not exist ".venv_ready" (
    echo  📦 جاري تثبيت المتطلبات لأول مرة...
    pip install -r requirements.txt --quiet 2>nul
    echo done > .venv_ready
    echo  ✅ تم تثبيت المتطلبات
)

echo.
echo  🚀 التطبيق يعمل على: http://localhost:8502
echo  📌 لإيقاف التطبيق اغلق هذه النافذة
echo.

streamlit run app.py --server.headless true --server.port 8502

pause
