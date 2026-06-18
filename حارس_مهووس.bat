@echo off
chcp 65001 >nul
title 🛡️ حارس مهووس الذكي

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║     🛡️  حارس مهووس الذكي — Guardian             ║
echo ║     يراقب التطبيق ويعيد تشغيله تلقائياً          ║
echo ╚══════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: منع السكون أثناء التشغيل
powershell -Command "& {[System.Runtime.InteropServices.Marshal]::SystemDefaultCharSize; Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public class PowerState { [DllImport(\"kernel32.dll\")] public static extern uint SetThreadExecutionState(uint esFlags); }'; [PowerState]::SetThreadExecutionState(0x80000003)}" 2>nul

echo [%time%] 🚀 جاري تشغيل حارس مهووس...
echo.

:loop
python guardian.py
echo.
echo [%time%] ⚠️ الحارس توقف! إعادة التشغيل خلال 5 ثوانٍ...
timeout /t 5 /nobreak >nul
goto loop
