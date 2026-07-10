@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo Building Oxford to Notion desktop app...

if not exist ".venv\Scripts\python.exe" (
    echo Error: .venv was not found. Run setup.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "Oxford to Notion" ^
    gui.py

if errorlevel 1 (
    echo.
    echo Build failed. Please check the messages above.
    pause
    exit /b 1
)

echo.
echo Build complete:
echo %~dp0dist\Oxford to Notion.exe
echo.
echo Your private .env file was not included in the executable.
pause
