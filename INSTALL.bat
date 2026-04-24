@echo off
REM =============================================================================
REM install.bat
REM Launches the PowerShell installer script
REM =============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
