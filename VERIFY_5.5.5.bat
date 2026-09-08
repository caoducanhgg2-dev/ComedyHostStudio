@echo off
setlocal EnableExtensions
set "APP=%LOCALAPPDATA%\Programs\ComedyHostStudio"
if not "%~1"=="" set "APP=%~1"
set "FAIL=0"

echo Kiem tra Comedy Host Studio 5.5.5 tai:
echo "%APP%"
echo.

if exist "%APP%\engine.py" (echo [OK] engine.py) else (echo [FAIL] engine.py & set "FAIL=1")
if exist "%APP%\engine_554_core.py" (echo [OK] engine_554_core.py) else (echo [FAIL] engine_554_core.py & set "FAIL=1")
if exist "%APP%\visual_srt_555.py" (echo [OK] visual_srt_555.py) else (echo [FAIL] visual_srt_555.py & set "FAIL=1")
if exist "%APP%\voice_catalog.json" (echo [OK] voice_catalog.json) else (echo [FAIL] voice_catalog.json & set "FAIL=1")

findstr /C:"beta5.5.5-visual-grounded" "%APP%\engine.py" >NUL 2>NUL
if errorlevel 1 (echo [FAIL] engine.py khong co marker 5.5.5 & set "FAIL=1") else echo [OK] marker 5.5.5
findstr /C:"beta5.5.4-clean-installer" "%APP%\engine_554_core.py" >NUL 2>NUL
if errorlevel 1 (echo [FAIL] core khong phai 5.5.4 Clean & set "FAIL=1") else echo [OK] core 5.5.4 Clean

echo.
if "%FAIL%"=="0" (
  echo [PASS] Cau truc cai dat 5.5.5 hop le.
  exit /b 0
) else (
  echo [FAIL] Co file/marker khong hop le. Chua nen chay app.
  pause
  exit /b 2
)
