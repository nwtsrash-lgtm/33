@echo off
cd /d "%~dp0"

echo === Step 1: Firewall ===
netsh advfirewall firewall add rule name="Mahwous" dir=in action=allow protocol=TCP localport=8502 >nul 2>&1
echo Done.

echo === Step 2: Check Python ===
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed!
    pause
    exit /b
)

echo === Step 3: Install ===
pip install streamlit --quiet --disable-pip-version-check 2>nul
pip install -r requirements.txt --quiet --disable-pip-version-check 2>nul

echo === Step 4: Start ===
echo.
echo ====================================
echo   Open browser: http://localhost:8502
echo ====================================
echo.

start http://localhost:8502
streamlit run app.py --server.address 0.0.0.0 --server.port 8502 --server.fileWatcherType none --server.headless true

echo.
echo App stopped.
pause
