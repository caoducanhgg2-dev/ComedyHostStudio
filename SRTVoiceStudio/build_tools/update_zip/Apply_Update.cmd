@echo off
setlocal
title SRT Voice Studio - ZIP Update
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Apply_Update.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo UPDATE FAILED. Safety checks stopped the update and transaction rollback restored changed files.
  pause
  exit /b %RC%
)
echo Update complete. A persistent rollback snapshot was kept for the previous version.
echo Run Rollback_Update.cmd from this folder if the new version has a problem.
pause
exit /b 0
