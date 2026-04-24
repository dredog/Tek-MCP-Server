@echo off
REM ============================================================================
REM Tek PTA Shortcut Installer
REM Creates shortcuts in Start Menu AND Desktop for Tek PTA
REM ============================================================================

echo.
echo ============================================================
echo         Tek PTA Shortcut Installer
echo ============================================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "VENV_PATH=%USERPROFILE%\TektronixMCP\venv"
set "ICON_PATH=%SCRIPT_DIR%\Tek_Logo_1947.ico"

REM Check if tek_pta.py exists
if not exist "%SCRIPT_DIR%\tek_pta.py" (
    echo ERROR: tek_pta.py not found in %SCRIPT_DIR%
    echo Please run this script from the Tek PTA folder.
    pause
    exit /b 1
)

REM Check if venv exists
if not exist "%VENV_PATH%\Scripts\pythonw.exe" (
    echo ERROR: Virtual environment not found at %VENV_PATH%
    echo Please run INSTALL.bat or INSTALL_TekPTA_Only.bat first.
    pause
    exit /b 1
)

echo Script directory: %SCRIPT_DIR%
echo Python location:  %VENV_PATH%\Scripts\pythonw.exe

REM Check for icon
if exist "%ICON_PATH%" (
    echo Icon file:        %ICON_PATH%
) else (
    echo Icon file:        Not found
)

echo.
echo Creating shortcuts...

REM Create VBS script
set "VBS_FILE=%TEMP%\create_tekpta_shortcuts.vbs"

> "%VBS_FILE%" (
    echo Set WshShell = WScript.CreateObject^("WScript.Shell"^)
    echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
    echo.
    echo StartMenuPath = "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Tek PTA.lnk"
    echo Set Shortcut1 = WshShell.CreateShortcut^(StartMenuPath^)
    echo Shortcut1.TargetPath = "%VENV_PATH%\Scripts\pythonw.exe"
    echo Shortcut1.Arguments = """%SCRIPT_DIR%\tek_pta.py"""
    echo Shortcut1.WorkingDirectory = "%SCRIPT_DIR%"
    echo Shortcut1.Description = "Tektronix Production Test Assistant"
)

if exist "%ICON_PATH%" (
    >> "%VBS_FILE%" echo Shortcut1.IconLocation = "%ICON_PATH%"
)

>> "%VBS_FILE%" (
    echo Shortcut1.Save
    echo If fso.FileExists^(StartMenuPath^) Then
    echo     WScript.Echo "[OK] Start Menu: " ^& StartMenuPath
    echo Else
    echo     WScript.Echo "[FAIL] Start Menu shortcut"
    echo End If
    echo.
    echo DesktopPath = WshShell.SpecialFolders^("Desktop"^)
    echo DesktopShortcut = DesktopPath ^& "\Tek PTA.lnk"
    echo Set Shortcut2 = WshShell.CreateShortcut^(DesktopShortcut^)
    echo Shortcut2.TargetPath = "%VENV_PATH%\Scripts\pythonw.exe"
    echo Shortcut2.Arguments = """%SCRIPT_DIR%\tek_pta.py"""
    echo Shortcut2.WorkingDirectory = "%SCRIPT_DIR%"
    echo Shortcut2.Description = "Tektronix Production Test Assistant"
)

if exist "%ICON_PATH%" (
    >> "%VBS_FILE%" echo Shortcut2.IconLocation = "%ICON_PATH%"
)

>> "%VBS_FILE%" (
    echo Shortcut2.Save
    echo If fso.FileExists^(DesktopShortcut^) Then
    echo     WScript.Echo "[OK] Desktop: " ^& DesktopShortcut
    echo Else
    echo     WScript.Echo "[FAIL] Desktop shortcut"
    echo End If
)

cscript //nologo "%VBS_FILE%"
del "%VBS_FILE%" 2>nul

echo.
echo ============================================================
echo Done! You can now launch Tek PTA from Desktop or Start Menu.
echo ============================================================
echo.
pause
