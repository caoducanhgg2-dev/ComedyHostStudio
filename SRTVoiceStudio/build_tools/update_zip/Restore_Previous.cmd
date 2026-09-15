@echo off
setlocal
title SRT Voice Studio - Restore Previous Version
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Restore_Previous.ps1"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo RESTORE FAILED. Keep the backup and report the error above.
pause
exit /b %RC%
