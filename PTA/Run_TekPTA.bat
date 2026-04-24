@echo off
REM Tek PTA - Production Test Assistant Launcher
REM Uses the Tektronix MCP Server virtual environment

set "VENV_PATH=%USERPROFILE%\TektronixMCP\venv"

REM Change to the directory where this batch file lives
cd /d "%~dp0"

REM Check if venv exists
if not exist "%VENV_PATH%\Scripts\python.exe" (
    echo ERROR: Tektronix MCP virtual environment not found
    echo.
    echo Expected location: %VENV_PATH%
    echo.
    echo Please run INSTALL_TekPTA.bat first, or install the MCP server.
    echo.
    pause
    exit /b 1
)

REM Run Tek PTA using the venv's Python
"%VENV_PATH%\Scripts\python.exe" tek_pta.py

REM If there's an error, pause so you can see it
if errorlevel 1 pause
