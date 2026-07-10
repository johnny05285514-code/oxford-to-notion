@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist "dist\Oxford to Notion.exe" (
    echo The desktop app has not been built yet. Building it now...
    call build_app.bat
    if errorlevel 1 exit /b 1
)

set "APP_DIR=%LOCALAPPDATA%\Programs\Oxford to Notion"
set "CONFIG_DIR=%APPDATA%\Oxford to Notion"
set "APP_EXE=%APP_DIR%\Oxford to Notion.exe"

if not exist "%APP_DIR%" mkdir "%APP_DIR%"
copy /Y "dist\Oxford to Notion.exe" "%APP_EXE%" >nul

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if exist ".env" if not exist "%CONFIG_DIR%\.env" copy ".env" "%CONFIG_DIR%\.env" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$shell = New-Object -ComObject WScript.Shell; " ^
  "$shortcut = $shell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Oxford to Notion.lnk'); " ^
  "$shortcut.TargetPath = '%APP_EXE%'; " ^
  "$shortcut.WorkingDirectory = '%APP_DIR%'; " ^
  "$shortcut.Description = 'Import Oxford Learner''s Dictionaries entries into Notion'; " ^
  "$shortcut.Save()"

if errorlevel 1 (
    echo Installation failed while creating the desktop shortcut.
    pause
    exit /b 1
)

echo.
echo Installed successfully. Open "Oxford to Notion" from your desktop.
pause
