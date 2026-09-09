@echo off
setlocal EnableExtensions
title Comedy Host Studio 5.5.7 Visual Continuity

set "APP=%LOCALAPPDATA%\Programs\ComedyHostStudio"
if not "%~1"=="" set "APP=%~1"
set "PKG=%~dp0"

echo ============================================================
echo  Comedy Host Studio 5.5.7 - Visual Continuity + Fast
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

for %%F in (engine_557.py visual_srt_557.py visual_priority_557.py visual_srt_556.py visual_rules_556.py runtime_stability_556.py memory_guard_556.py) do (
  if not exist "%PKG%%%F" (
    echo [LOI] Goi cai dat thieu %%F.
    pause
    exit /b 12
  )
)

rem Keep the preserved clean 5.5.4 core. Accept a clean 5.5.6 install or direct 5.5.4 core.
if not exist "%APP%\engine_554_core.py" (
  findstr /C:"beta5.5.4-clean-installer" "%APP%\engine.py" >NUL 2>NUL
  if errorlevel 1 (
    echo [DUNG AN TOAN] Khong tim thay 5.5.4 Clean core / 5.5.6 clean install.
    echo Khong co file nao bi thay doi.
    pause
    exit /b 13
  )
  echo [1/7] Luu core 5.5.4 Clean...
  copy /Y "%APP%\engine.py" "%APP%\engine_554_core.py" >NUL || goto FAIL
) else (
  echo [1/7] Da tim thay engine_554_core.py sach.
)

echo [2/7] Sao luu engine hien tai...
copy /Y "%APP%\engine.py" "%APP%\engine.before_5.5.7.bak.py" >NUL || goto FAIL

echo [3/7] Cai Visual Continuity writer...
copy /Y "%PKG%visual_srt_557.py" "%APP%\visual_srt_557.py" >NUL || goto ROLLBACK
copy /Y "%PKG%visual_priority_557.py" "%APP%\visual_priority_557.py" >NUL || goto ROLLBACK
copy /Y "%PKG%visual_srt_556.py" "%APP%\visual_srt_556.py" >NUL || goto ROLLBACK
copy /Y "%PKG%visual_rules_556.py" "%APP%\visual_rules_556.py" >NUL || goto ROLLBACK

echo [4/7] Giu Runtime Stability + Memory Guard...
copy /Y "%PKG%runtime_stability_556.py" "%APP%\runtime_stability_556.py" >NUL || goto ROLLBACK
copy /Y "%PKG%memory_guard_556.py" "%APP%\memory_guard_556.py" >NUL || goto ROLLBACK

echo [5/7] Thay engine bootstrap 5.5.7...
copy /Y "%PKG%engine_557.py" "%APP%\engine.py" >NUL || goto ROLLBACK

echo [6/7] Kiem tra source sau cai dat...
findstr /C:"beta5.5.7-visual-continuity-fast" "%APP%\engine.py" >NUL 2>NUL || goto ROLLBACK
findstr /C:"5.5.7-visual-continuity" "%APP%\visual_srt_557.py" >NUL 2>NUL || goto ROLLBACK
if not exist "%APP%\visual_priority_557.py" goto ROLLBACK

echo [7/7] Hoan tat.
echo.
echo [OK] Da cai 5.5.7 Visual Continuity + Fast.
echo - Chan ro ri TIME/frame/timestamp/so ky thuat vao SRT.
echo - Moi caption uu tien 1 cau tu nhien, co chi tiet hinh anh huu ich.
echo - Khong lap lai boi canh khong thay doi o cac caption lien tiep.
echo - Uu tien chi tiet moi/khac biet khi fallback thay vi boi canh tinh.
echo - 8-12 tu la dep; 7-14 binh thuong; 15-18 duoc phep khi can chi tiet.
echo - Exact duplicate sua tung caption, khong huy ca SRT.
echo - Giu Memory Guard, GPU handoff va clean video lien tiep cua 5.5.6.
echo - Khong dung VideoScriptAI, 5.5.3f/g/h hay PowerShell chen source.
echo.
pause
exit /b 0

:ROLLBACK
echo.
echo [LOI] Cai dat chua hoan tat. Dang khoi phuc engine truoc 5.5.7...
if exist "%APP%\engine.before_5.5.7.bak.py" copy /Y "%APP%\engine.before_5.5.7.bak.py" "%APP%\engine.py" >NUL
echo Da rollback engine. Cac module moi khong duoc engine cu nap va co the de nguyen an toan.
pause
exit /b 20

:FAIL
echo [LOI] Khong tao duoc backup/core. Khong tiep tuc cai dat.
pause
exit /b 21
