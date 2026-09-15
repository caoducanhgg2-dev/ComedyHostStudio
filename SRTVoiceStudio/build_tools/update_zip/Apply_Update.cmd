@echo off
setlocal
title SRT Voice Studio - ZIP Update
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Apply_Update.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo UPDATE FAILED. Read the error above. Keep all backup files.
  echo If automatic restore failed, close the app and run Restore_Previous.cmd.
  pause
  exit /b %RC%
)
echo Update complete. Open SRT Voice Studio normally.
pause
exit /b 0
