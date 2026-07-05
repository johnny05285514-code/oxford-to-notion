@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo Oxford to Notion setup
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found.
    echo Please install Python 3.11 or newer from https://www.python.org/downloads/
    echo During installation, tick "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

python --version
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
    echo.
    echo [ERROR] Python 3.11 or newer is required.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Installing dependencies from requirements.txt...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo Check your network connection and try again.
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo.
    echo Creating .env from .env.example...
    copy ".env.example" ".env" >nul
)

echo.
echo Setup finished.
echo.
echo Next step:
echo 1. Open .env
echo 2. Fill in NOTION_TOKEN
echo 3. Fill in NOTION_DATABASE_ID with your Notion database URL or ID
echo 4. Double-click "Oxford to Notion.bat" to import words
echo.

set /p OPEN_ENV=Open .env now? (y/n): 
if /i "%OPEN_ENV%"=="y" (
    notepad .env
)

echo.
pause
