@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo Building Oxford to Notion installer...

set "MAKENSIS="
for %%I in (makensis.exe) do set "MAKENSIS=%%~$PATH:I"
if not defined MAKENSIS if exist "%USERPROFILE%\scoop\apps\nsis\current\Bin\makensis.exe" set "MAKENSIS=%USERPROFILE%\scoop\apps\nsis\current\Bin\makensis.exe"
if not defined MAKENSIS if exist "%ProgramFiles(x86)%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not defined MAKENSIS if exist "%ProgramFiles%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"

if not defined MAKENSIS (
    echo Error: NSIS was not found.
    echo Install NSIS first, then run this script again.
    if /i not "%~1"=="--no-pause" pause
    exit /b 1
)

call build_app.bat --no-pause
if errorlevel 1 exit /b 1

if not exist "release" mkdir "release"
"%MAKENSIS%" /V2 installer.nsi
if errorlevel 1 (
    echo.
    echo Installer build failed.
    if /i not "%~1"=="--no-pause" pause
    exit /b 1
)

set "SETUP_FILE=release\Oxford-to-Notion-Setup-1.0.0.exe"
powershell -NoProfile -Command ^
  "$file = Get-Item '%SETUP_FILE%'; " ^
  "$hash = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower(); " ^
  "Set-Content -Encoding ascii -Path ($file.FullName + '.sha256') -Value ($hash + '  ' + $file.Name)"

echo.
echo Installer build complete:
echo %~dp0%SETUP_FILE%
echo.
echo The installer does not contain .env or any Notion token.
if /i not "%~1"=="--no-pause" pause
