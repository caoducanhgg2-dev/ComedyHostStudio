@echo off
setlocal EnableExtensions
title Comedy Host Studio 5.5.6 Visual Quality + Stability

set "APP=%LOCALAPPDATA%\Programs\ComedyHostStudio"
if not "%~1"=="" set "APP=%~1"
set "PKG=%~dp0"

echo ============================================================
echo  Comedy Host Studio 5.5.6 - Visual Quality + Stability
echo ============================================================
echo.
echo Thu muc app: "%APP%"
echo.

tasklist /FI "IMAGENAME eq ComedyHostStudio.exe" 2>NUL | find /I "ComedyHostStudio.exe" >NUL
if not errorlevel 1 (
  echo [LOI] Comedy Host Studio dang chay.
  echo Dong han app, doi vai giay, roi chay lai file nay.
  pause
  exit /b 10
)

if not exist "%APP%\engine.py" (
  echo [LOI] Khong tim thay engine.py trong thu muc app.
  pause
  exit /b 11
)

for %%F in (engine_556.py visual_srt_556.py visual_rules_556.py runtime_stability_556.py memory_guard_556.py) do (
  if not exist "%PKG%%%F" (
    echo [LOI] Goi cai dat thieu %%F.
    pause
    exit /b 12
  )
)

rem Accept 5.5.5 wrapper or clean 5.5.4 source. Never use f/g/h patch chain.
if not exist "%APP%\engine_554_core.py" (
  findstr /C:"beta5.5.4-clean-installer" "%APP%\engine.py" >NUL 2>NUL
  if errorlevel 1 (
    echo [DUNG AN TOAN] Khong tim thay 5.5.4 Clean core / 5.5.5 clean wrapper.
    echo Khong co file nao bi thay doi.
    pause
    exit /b 13
  )
  echo [1/6] Luu core 5.5.4 Clean...
  copy /Y "%APP%\engine.py" "%APP%\engine_554_core.py" >NUL || goto FAIL
) else (
  echo [1/6] Da tim thay engine_554_core.py sach.
)

echo [2/6] Sao luu engine hien tai...
copy /Y "%APP%\engine.py" "%APP%\engine.before_5.5.6.bak.py" >NUL || goto FAIL

echo [3/6] Cai Visual SRT 5.5.6...
copy /Y "%PKG%visual_srt_556.py" "%APP%\visual_srt_556.py" >NUL || goto ROLLBACK
copy /Y "%PKG%visual_rules_556.py" "%APP%\visual_rules_556.py" >NUL || goto ROLLBACK

echo [4/6] Cai Runtime Stability + Memory Guard...
copy /Y "%PKG%runtime_stability_556.py" "%APP%\runtime_stability_556.py" >NUL || goto ROLLBACK
copy /Y "%PKG%memory_guard_556.py" "%APP%\memory_guard_556.py" >NUL || goto ROLLBACK

echo [5/6] Thay engine bootstrap 5.5.6...
copy /Y "%PKG%engine_556.py" "%APP%\engine.py" >NUL || goto ROLLBACK

echo [6/6] Kiem tra sau cai dat...
findstr /C:"beta5.5.6-visual-quality-stability" "%APP%\engine.py" >NUL 2>NUL || goto ROLLBACK
if not exist "%APP%\memory_guard_556.py" goto ROLLBACK
if not exist "%APP%\visual_rules_556.py" goto ROLLBACK

echo.
echo [OK] Da cai 5.5.6.
echo - SRT: dung hinh anh va giu chi tiet huu ich; khong ep 10 tu.
echo - 8-12 tu la dep; 7-14 binh thuong; 15-18 duoc phep khi can chi tiet.
echo - Bat fragment / cau cut dut; fallback khong cat raw evidence thanh manh cau.
echo - Video tiep theo: giai phong model cu truoc khi dung lai GPU.
echo - Memory Guard: giam Ollama batch khi RAM he thong thap de tranh HTTP 500.
echo - Khong dung VideoScriptAI, 5.5.3f/g/h hay PowerShell chen source.
echo.
pause
exit /b 0

:ROLLBACK
echo.
echo [LOI] Cai dat chua hoan tat. Dang khoi phuc engine truoc 5.5.6...
if exist "%APP%\engine.before_5.5.6.bak.py" copy /Y "%APP%\engine.before_5.5.6.bak.py" "%APP%\engine.py" >NUL
echo Da rollback engine. Cac module 5.5.6 khong duoc engine cu nap va co the de nguyen an toan.
pause
exit /b 20

:FAIL
echo [LOI] Khong tao duoc backup/core. Khong tiep tuc cai dat.
pause
exit /b 21
