@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   تشغيل نظام التسعير الذكي - مهووس (واجهة v32)
echo   Python 3.11 (لان 3.14 غير متوافق مع Streamlit)
echo ============================================================
echo.
echo سيفتح المتصفح تلقائيا على http://localhost:8501
echo لايقاف التطبيق: اغلق هذه النافذة او اضغط Ctrl+C
echo.
"C:\Users\Hp\AppData\Local\Programs\Python\Python311\python.exe" -m streamlit run app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false
pause
