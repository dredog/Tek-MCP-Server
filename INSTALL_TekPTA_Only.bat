@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM Tek PTA - Standalone Installer (without MCP Server)
REM For users who only need the GUI test application, not Claude integration
REM ============================================================================

echo.
echo ============================================================
echo    Tek PTA - Standalone Installer
echo ============================================================
echo.

set "INSTALL_DIR=%USERPROFILE%\TektronixMCP"
set "PTA_DIR=%INSTALL_DIR%\PTA"

echo Installation directory: %INSTALL_DIR%
echo.

REM ============================================================
REM Check Python version (requires 3.9+ for matplotlib)
REM ============================================================
echo [1/5] Checking Python...

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.9 or later from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo        Found Python %PYVER%

REM Extract major.minor version
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)

REM Check Python 3.9+ requirement
if %PYMAJOR% LSS 3 (
    echo ERROR: Python 3.9+ required, found %PYVER%
    pause
    exit /b 1
)
if %PYMAJOR%==3 if %PYMINOR% LSS 9 (
    echo ERROR: Python 3.9+ required, found %PYVER%
    echo.
    echo Tek PTA requires Python 3.9 or later.
    echo Download from: https://python.org
    pause
    exit /b 1
)
echo        Python version OK

REM ============================================================
REM Create directories
REM ============================================================
echo [2/5] Creating directories...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%PTA_DIR%" mkdir "%PTA_DIR%"
if not exist "%PTA_DIR%\test_suites" mkdir "%PTA_DIR%\test_suites"
echo        Done

REM ============================================================
REM Copy PTA files
REM ============================================================
echo [3/5] Copying files...

REM Copy from source directory (where this bat file is)
copy /Y "%~dp0PTA\tek_pta.py" "%PTA_DIR%\" >nul 2>&1
copy /Y "%~dp0PTA\tek_pta_plugin_api.py" "%PTA_DIR%\" >nul 2>&1
copy /Y "%~dp0PTA\tek_pta_config.json" "%PTA_DIR%\" >nul 2>&1
copy /Y "%~dp0PTA\requirements_pta.txt" "%PTA_DIR%\" >nul 2>&1
copy /Y "%~dp0PTA\Run_TekPTA.bat" "%PTA_DIR%\" >nul 2>&1
copy /Y "%~dp0PTA\README.md" "%PTA_DIR%\" >nul 2>&1
copy /Y "%~dp0PTA\TEK_PTA_PLUGIN_DEVELOPMENT_GUIDE.md" "%PTA_DIR%\" >nul 2>&1

REM Copy test_suites folder
if exist "%~dp0PTA\test_suites" (
    xcopy /E /I /Y "%~dp0PTA\test_suites\*" "%PTA_DIR%\test_suites\" >nul 2>&1
)

echo        Done

REM ============================================================
REM Create fresh virtual environment
REM ============================================================
echo [4/5] Creating virtual environment...

REM Remove old venv if it exists
if exist "%INSTALL_DIR%\venv" (
    echo        Removing old virtual environment...
    rmdir /s /q "%INSTALL_DIR%\venv" >nul 2>&1
)

REM Create new venv
python -m venv "%INSTALL_DIR%\venv"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo        Virtual environment created

REM ============================================================
REM Install dependencies
REM ============================================================
echo [5/5] Installing dependencies...
call "%INSTALL_DIR%\venv\Scripts\activate.bat"

pip install --upgrade pip >nul 2>&1

echo        Installing packages...
pip install pyvisa pyvisa-py Pillow reportlab matplotlib >nul 2>&1

if errorlevel 1 (
    echo WARNING: Some packages may have failed to install
)
echo        Done

echo.
echo ============================================================
echo    Installation Complete!
echo ============================================================
echo.
echo Location: %PTA_DIR%
echo.
echo TO RUN:
echo   Double-click: %PTA_DIR%\Run_TekPTA.bat
echo.
echo NOTE: This is Tek PTA only (without Claude Desktop integration).
echo       For full MCP server + Tek PTA, run INSTALL.bat instead
echo       (requires Python 3.10+).
echo.
pause
