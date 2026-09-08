@echo off
setlocal EnableExtensions
title Restore Comedy Host Studio 5.5.4 Clean
set "APP=%LOCALAPPDATA%\Programs\ComedyHostStudio"
if not "%~1"=="" set "APP=%~1"

tasklist /FI "IMAGENAME eq ComedyHostStudio.exe" 2>NUL | find /I "ComedyHostStudio.exe" >NUL
if not errorlevel 1 (
  echo [LOI] Hay dong Comedy Host Studio truoc khi khoi phuc.
  pause
  exit /b 10
)

if not exist "%APP%\engine_554_core.py" (
  echo [LOI] Khong tim thay engine_554_core.py. Khong co backup 5.5.4 de khoi phuc.
  pause
  exit /b 11
)

copy /Y "%APP%\engine_554_core.py" "%APP%\engine.py" >NUL
if errorlevel 1 (
  echo [LOI] Khong khoi phuc duoc engine.py.
  pause
  exit /b 12
)
if exist "%APP%\voice_catalog.5.5.4.bak.json" copy /Y "%APP%\voice_catalog.5.5.4.bak.json" "%APP%\voice_catalog.json" >NUL
del /Q "%APP%\visual_srt_555.py" 2>NUL

findstr /C:"beta5.5.4-clean-installer" "%APP%\engine.py" >NUL 2>NUL
if errorlevel 1 (
  echo [CANH BAO] engine da duoc khoi phuc nhung marker 5.5.4 khong duoc tim thay.
  echo Hay giu file engine_554_core.py va gui log neu app khong mo.
) else (
  echo [OK] Da khoi phuc 5.5.4 Clean.
)
pause
exit /b 0
