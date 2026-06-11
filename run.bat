@echo off
rem هذا الملف يفوّض للمشغّل الموحّد run_app.bat
rem (يضمن Python 3.11 ومنفذ 8501 — لتفادي Python 3.14 غير المتوافق مع Streamlit).
call "%~dp0run_app.bat"
