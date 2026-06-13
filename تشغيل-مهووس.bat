@echo off
chcp 65001 >nul
cd /d "%~dp0"
title نظام التسعير الذكي - مهووس

echo.
echo  ============================================
echo     نظام التسعير الذكي - مهووس
echo  ============================================
echo.
echo   - جاري بدء التطبيق ...
echo   - سيفتح المتصفح تلقائيا خلال ثوان
echo   - العنوان: http://localhost:8601
echo   - لايقاف التطبيق: اغلق هذه النافذة
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python -m streamlit run app.py --server.port 8601
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -m streamlit run app.py --server.port 8601
    ) else (
        echo.
        echo  [خطأ] لم يتم العثور على Python. ثبّت Python ثم اعد المحاولة.
        echo.
    )
)

echo.
echo   توقف التطبيق. اضغط اي زر للاغلاق.
pause >nul
