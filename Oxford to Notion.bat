@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo Oxford Dictionary to Notion
echo Enter q or leave blank to exit.
echo.

:prompt
set "WORD="
set /p "WORD=Enter one English word: "

if "%WORD%"=="" (
    exit /b 0
)

if /i "%WORD%"=="q" exit /b 0

echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" "%WORD%"
echo.
goto prompt
