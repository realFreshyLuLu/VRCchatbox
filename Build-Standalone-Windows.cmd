@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY=py -3"
%PY% --version >nul 2>nul
if errorlevel 1 set "PY=python"
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Install Python 3.10+ first to BUILD the standalone version.
  pause
  exit /b 1
)
if not exist .buildvenv\Scripts\python.exe (
  %PY% -m venv .buildvenv
  if errorlevel 1 goto bad
)
set "PYEXE=.buildvenv\Scripts\python.exe"
"%PYEXE%" -m pip install --upgrade pip
"%PYEXE%" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto bad
"%PYEXE%" -m PyInstaller --noconfirm --clean --onedir --console --name VRCChatbox --icon "VRCChatbox.ico" --paths "HTML osc chat" --add-data "HTML osc chat\templates;templates" --add-data "HTML osc chat\static;static" "HTML osc chat\osc_viewer.py"
if errorlevel 1 goto bad
for %%F in (README.md README.en.md README.ja.md README.ko.md) do copy "%%F" "dist\VRCChatbox\%%F" >nul
copy "使用说明.txt" "dist\VRCChatbox\使用说明.txt" >nul
copy "LICENSE" "dist\VRCChatbox\LICENSE" >nul
copy "NOTICE.md" "dist\VRCChatbox\NOTICE.md" >nul
copy "版本更新.md" "dist\VRCChatbox\版本更新.md" >nul
echo.
echo [OK] Standalone build: dist\VRCChatbox\VRCChatbox.exe
echo Include matching source and licenses when publishing binaries.
echo Distribute the entire dist\VRCChatbox folder, NOT just the EXE.
pause
exit /b 0
:bad
echo [ERROR] Standalone build failed.
pause
exit /b 1
