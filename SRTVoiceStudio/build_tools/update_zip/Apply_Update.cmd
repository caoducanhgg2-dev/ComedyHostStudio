@echo off
setlocal
title SRT Voice Studio - ZIP Update
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Apply_Update.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo UPDATE FAILED. No file is overwritten when the baseline checksum is wrong.
  pause
  exit /b %RC%
)
echo Update complete. Open SRT Voice Studio normally.
pause
exit /b 0
