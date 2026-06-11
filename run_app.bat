@echo off
chcp 65001 >nul
cd /d "%~dp0"
title نظام التسعير الذكي - مهووس (v32)

echo ============================================================
echo    نظام التسعير الذكي - مهووس  ^|  واجهة v32
echo    يتطلب Python 3.11 (Streamlit لا يعمل على 3.14+)
echo ============================================================
echo.

rem ── ابحث عن Python 3.11 (المسار المعروف ثم py launcher) ──
set "PY="
set "PY311=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY311%" (
    set "PY=%PY311%"
) else (
    py -3.11 --version >nul 2>&1 && set "PY=py -3.11"
)

if not defined PY (
    echo [تحذير] لم يُعثر على Python 3.11 في المسار المعتاد.
    echo         سيُجرَّب python من PATH وقد يفشل اذا كان 3.14+.
    echo         التحميل: https://www.python.org/downloads/release/python-3119/
    echo.
    set "PY=python"
)

echo [تشغيل] %PY%
echo سيفتح المتصفح تلقائيا على: http://localhost:8501
echo لايقاف التطبيق: اغلق هذه النافذة او اضغط Ctrl+C
echo.

%PY% -m streamlit run app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

echo.
echo [توقف] انتهى التطبيق. اضغط اي مفتاح للاغلاق.
pause >nul
