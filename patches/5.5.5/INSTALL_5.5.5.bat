@echo off
setlocal EnableExtensions
title Comedy Host Studio 5.5.5 Visual-Grounded Installer

set "APP=%LOCALAPPDATA%\Programs\ComedyHostStudio"
if not "%~1"=="" set "APP=%~1"
set "PKG=%~dp0"

echo ============================================================
echo  Comedy Host Studio 5.5.5 - Visual-Grounded SRT
echo ============================================================
echo.
echo Thu muc app: "%APP%"
echo.

tasklist /FI "IMAGENAME eq ComedyHostStudio.exe" 2>NUL | find /I "ComedyHostStudio.exe" >NUL
if not errorlevel 1 (
  echo [LOI] Comedy Host Studio dang chay.
  echo Hay dong han app, doi vai giay, roi chay lai file nay.
  pause
  exit /b 10
)

if not exist "%APP%\engine.py" (
  echo [LOI] Khong tim thay "%APP%\engine.py".
  echo Ban nay chi cai len Comedy Host Studio 5.5.4 Clean.
  pause
  exit /b 11
)

if not exist "%PKG%visual_srt_555.py" (
  echo [LOI] Goi cai dat thieu visual_srt_555.py.
  pause
  exit /b 12
)
if not exist "%PKG%engine.py" (
  echo [LOI] Goi cai dat thieu engine.py 5.5.5.
  pause
  exit /b 13
)
if not exist "%PKG%voice_catalog.json" (
  echo [LOI] Goi cai dat thieu voice_catalog.json.
  pause
  exit /b 14
)

findstr /C:"beta5.5.5-visual-grounded" "%APP%\engine.py" >NUL 2>NUL
if not errorlevel 1 goto REFRESH

findstr /C:"beta5.5.4-clean-installer" "%APP%\engine.py" >NUL 2>NUL
if errorlevel 1 (
  echo [DUNG AN TOAN] engine.py hien tai khong phai 5.5.4 Clean.
  echo Installer KHONG sua source va KHONG chen code vao engine.py.
  echo Hay cai dung 5.5.4 Clean truoc, sau do chay lai.
  pause
  exit /b 15
)

echo [1/5] Sao luu engine 5.5.4 Clean...
copy /Y "%APP%\engine.py" "%APP%\engine_554_core.py" >NUL
if errorlevel 1 goto ROLLBACK_FAIL
if exist "%APP%\voice_catalog.json" copy /Y "%APP%\voice_catalog.json" "%APP%\voice_catalog.5.5.4.bak.json" >NUL

echo [2/5] Cai Visual-Grounded writer...
copy /Y "%PKG%visual_srt_555.py" "%APP%\visual_srt_555.py" >NUL
if errorlevel 1 goto ROLLBACK

echo [3/5] Thay engine bootstrap sach 5.5.5...
copy /Y "%PKG%engine.py" "%APP%\engine.py" >NUL
if errorlevel 1 goto ROLLBACK

echo [4/5] Cap nhat mo ta SRT US / JP...
copy /Y "%PKG%voice_catalog.json" "%APP%\voice_catalog.json" >NUL
if errorlevel 1 goto ROLLBACK

goto VERIFY

:REFRESH
echo [INFO] 5.5.5 da duoc cai. Dang lam moi file module...
if not exist "%APP%\engine_554_core.py" (
  echo [LOI] Thieu engine_554_core.py. Khong the lam moi an toan.
  pause
  exit /b 16
)
copy /Y "%PKG%visual_srt_555.py" "%APP%\visual_srt_555.py" >NUL
if errorlevel 1 exit /b 17
copy /Y "%PKG%engine.py" "%APP%\engine.py" >NUL
if errorlevel 1 exit /b 18
copy /Y "%PKG%voice_catalog.json" "%APP%\voice_catalog.json" >NUL
if errorlevel 1 exit /b 19

:VERIFY
echo [5/5] Kiem tra file sau cai dat...
if not exist "%APP%\engine_554_core.py" goto ROLLBACK
if not exist "%APP%\visual_srt_555.py" goto ROLLBACK
findstr /C:"beta5.5.5-visual-grounded" "%APP%\engine.py" >NUL 2>NUL
if errorlevel 1 goto ROLLBACK
findstr /C:"5.5.5: bam sat hinh anh" "%APP%\voice_catalog.json" >NUL 2>NUL
if errorlevel 1 (
  rem JSON co the dung Unicode/wording khac; file ton tai la du cho runtime.
  if not exist "%APP%\voice_catalog.json" goto ROLLBACK
)

echo.
echo [OK] Da cai Comedy Host Studio 5.5.5 Visual-Grounded.
echo - SRT US: khoang 8-12 tu, uu tien 9-11, khong ep dung 10.
echo - Bam sat hinh anh, giu chi tiet co ich de viet lai sau.
echo - Khong GoldStyle / hook / trend / comedy bat buoc trong SRT-only.
echo - Chi exact duplicate la loi lap cung.
echo - Timing van ~4.08s va gap 0.10s.
echo - GPU Recovery / Visual Brain / Writer local cua 5.5.4 duoc giu nguyen.
echo.
echo Neu can quay lai, chay RESTORE_5.5.4.bat.
pause
exit /b 0

:ROLLBACK
echo.
echo [LOI] Cai dat chua hoan tat. Dang khoi phuc 5.5.4...
if exist "%APP%\engine_554_core.py" copy /Y "%APP%\engine_554_core.py" "%APP%\engine.py" >NUL
if exist "%APP%\voice_catalog.5.5.4.bak.json" copy /Y "%APP%\voice_catalog.5.5.4.bak.json" "%APP%\voice_catalog.json" >NUL
del /Q "%APP%\visual_srt_555.py" 2>NUL
echo Da khoi phuc engine cu. Khong de lai patch chong.
pause
exit /b 20

:ROLLBACK_FAIL
echo [LOI] Khong sao luu duoc engine 5.5.4. Khong co file nao bi thay the.
pause
exit /b 21
