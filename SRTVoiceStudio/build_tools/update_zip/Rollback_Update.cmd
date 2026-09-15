@echo off
setlocal
title SRT Voice Studio - Rollback Update
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Rollback_Update.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo ROLLBACK FAILED. Safety checks stopped the restore or the current files were changed.
  pause
  exit /b %RC%
)
echo Rollback complete. The previous SRT Voice Studio version has been restored.
pause
exit /b 0

