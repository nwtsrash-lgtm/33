@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem هذا الملف يفوّض للمشغّل الموحّد run_app.bat (يضمن Python 3.11 ومنفذ 8501)
rem لتفادي تشغيل التطبيق على Python 3.14 غير المتوافق مع Streamlit.
call "%~dp0run_app.bat"
