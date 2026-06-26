@echo off
setlocal enabledelayedexpansion
title Tektronix MCP Server - Build Tool

REM =============================================================================
REM build.bat
REM Builds the PyInstaller distributable for Tektronix MCP Server.
REM Run this from C:\Users\u610842\TektronixMCP\ (alongside the .spec file).
REM Output: dist\TektronixMCP_v1.4.5\  — zip this folder and share it.
REM
REM Files copied into the distribution (alphabetical by section):
REM
REM   docs\instrument_commands_json\*     SCPI JSON databases (server loads at startup)
REM   docs\python_examples\*              Golden example scripts (not searched, for reference)
REM   docs\reference\**                   All reference files — *.md, *.xml, *.json, *.pdf
REM                                       Server searches **/*.md recursively
REM   docs\*.md                           Root-level docs markdown (server searches these)
REM   PTA\lessons_learned\*               Session lessons (server searches *.md)
REM   PTA\test_suites\*                   Plugin examples (server searches *.py)
REM
REM NOT copied (not needed at runtime):
REM   docs\programmer_manuals\*.pdf       Too large; server does not load them
REM   PTA\backups\                        Build artifacts
REM   PTA\tek_pta.py                      PTA GUI runs separately, not via the MCP exe
REM   PTA\tek_pta_plugin_api.py           Same — GUI only
REM =============================================================================

REM ── Version — update this when server version changes ────────────────────────
set VERSION=1.4.5
set DIST_NAME=TektronixMCP_v%VERSION%

echo.
echo ============================================================
echo   Tektronix MCP Server v%VERSION% - Build Script
echo ============================================================
echo.

REM ── Verify we are in the right directory ─────────────────────────────────────
if not exist "tektronix_mcp_server.py" (
    echo ERROR: tektronix_mcp_server.py not found.
    echo Run this script from the TektronixMCP root directory.
    echo Example: cd C:\Users\u610842\TektronixMCP
    pause & exit /b 1
)
if not exist "tektronix_mcp_server.spec" (
    echo ERROR: tektronix_mcp_server.spec not found.
    pause & exit /b 1
)
if not exist "pyinstaller_runtime_hook.py" (
    echo ERROR: pyinstaller_runtime_hook.py not found.
    pause & exit /b 1
)

REM ── Check for requirements-docker.txt ────────────────────────────────────────
if not exist "requirements-docker.txt" (
    echo ERROR: requirements-docker.txt not found.
    echo This file contains the minimal dependencies for the MCP server build.
    echo It should be in the same directory as tektronix_mcp_server.py
    pause & exit /b 1
)

REM ── Check Python ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    echo Install Python 3.10+ and make sure it is on your PATH.
    pause & exit /b 1
)
echo Python: OK
python --version

REM ── Install build dependencies ────────────────────────────────────────────────
echo.
echo Installing build requirements...
pip install pyinstaller --quiet
pip install -r requirements-docker.txt --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Check your internet connection.
    pause & exit /b 1
)
echo Dependencies: OK

REM ── Clean previous dist only (keep build/ cache for faster rebuilds) ─────────
echo.
echo Cleaning previous dist...
if exist "dist"               rmdir /s /q "dist"
if exist "%DIST_NAME%.zip"    del /q "%DIST_NAME%.zip"
REM NOTE: build/ is intentionally kept — PyInstaller reuses its analysis cache.
REM       First build takes 2-5 min; subsequent builds ~30-60s with cache.
REM       To force a full rebuild: rmdir /s /q build

REM ── Run PyInstaller ───────────────────────────────────────────────────────────
echo.
echo Building executable...
echo   (First build: 2-5 min.  Cached rebuild: ~30-60s)
echo.
pyinstaller --noconfirm tektronix_mcp_server.spec

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   BUILD FAILED — check output above for errors.
    echo   Common causes:
    echo     - Missing package: run pip install [package]
    echo     - Import error: check excludes in tektronix_mcp_server.spec
    echo     - Stale cache: try rmdir /s /q build and rebuild
    echo ============================================================
    pause & exit /b 1
)

REM ── Rename PyInstaller output to versioned folder ─────────────────────────────
REM PyInstaller creates: dist\tektronix_mcp_server\
REM We rename it to:     dist\TektronixMCP_v1.4.5\
echo.
echo Packaging distribution folder...
rename "dist\tektronix_mcp_server" "%DIST_NAME%"
if errorlevel 1 (
    echo ERROR: Could not rename dist\tektronix_mcp_server
    pause & exit /b 1
)

set DIST_DIR=dist\%DIST_NAME%

REM =============================================================================
REM Copy docs — three separate operations to match exactly what the server needs
REM =============================================================================
echo.
echo Copying documentation...

REM 1. SCPI JSON databases — server loads ALL of these at startup.
REM    Missing even one will cause that instrument family to show 0 commands.
if exist "docs\instrument_commands_json" (
    xcopy /s /e /i /q "docs\instrument_commands_json" "%DIST_DIR%\docs\instrument_commands_json\"
    echo   [OK] docs\instrument_commands_json\
) else (
    echo   [WARN] docs\instrument_commands_json not found - SCPI lookup will fail!
)

REM 2. Root-level docs markdown files.
REM    Server searches docs\*.md — these must be present.
if exist "docs\*.md" (
    xcopy /q "docs\*.md" "%DIST_DIR%\docs\"
    echo   [OK] docs\*.md
) else (
    echo   [WARN] No *.md files found in docs\ root
)

REM 3. Reference folder — full recursive copy.
REM    Server searches docs\reference\**\*.md recursively, which includes
REM    pi_translator\ subfolder. Also copies .xml, .json, and .pdf files
REM    (not searched but part of the reference set — legacy_command_mappings.json
REM    is loaded separately by the legacy command translation tool).
if exist "docs\reference" (
    xcopy /s /e /i /q "docs\reference" "%DIST_DIR%\docs\reference\"
    echo   [OK] docs\reference\ (recursive)
) else (
    echo   [WARN] docs\reference\ not found
)

REM 4. Python examples — NOT searched by the server, but golden example scripts
REM    are useful for FAE recipients to have on hand.
if exist "docs\python_examples" (
    xcopy /s /e /i /q "docs\python_examples" "%DIST_DIR%\docs\python_examples\"
    echo   [OK] docs\python_examples\
) else (
    echo   [INFO] docs\python_examples\ not found - skipping (optional)
)

REM NOTE: docs\programmer_manuals\ is intentionally NOT copied.
REM       PDFs can be hundreds of MB and the server does not load them.

REM =============================================================================
REM Copy PTA content
REM =============================================================================
echo.
echo Copying PTA content...

REM test_suites: server searches PTA\test_suites\*.py
if exist "PTA\test_suites" (
    xcopy /s /e /i /q "PTA\test_suites" "%DIST_DIR%\PTA\test_suites\"
    echo   [OK] PTA\test_suites\
)

REM lessons_learned: server searches PTA\lessons_learned\*.md
if exist "PTA\lessons_learned" (
    xcopy /s /e /i /q "PTA\lessons_learned" "%DIST_DIR%\PTA\lessons_learned\"
    echo   [OK] PTA\lessons_learned\
) else (
    mkdir "%DIST_DIR%\PTA\lessons_learned"
    echo   [OK] PTA\lessons_learned\ (created empty)
)

REM =============================================================================
REM Copy installer and user-facing files
REM =============================================================================
echo.
echo Copying installer files...

REM Copy install.bat (handle both uppercase and lowercase names)
if exist "install.bat" (
    copy /y "install.bat" "%DIST_DIR%\install.bat" >nul
    echo   [OK] install.bat
) else if exist "INSTALL.bat" (
    copy /y "INSTALL.bat" "%DIST_DIR%\install.bat" >nul
    echo   [OK] INSTALL.bat -^> install.bat
) else (
    echo   [WARN] install.bat not found
)

REM Copy install.ps1 (the actual PowerShell installer)
if exist "install.ps1" (
    copy /y "install.ps1" "%DIST_DIR%\install.ps1" >nul
    echo   [OK] install.ps1
) else (
    echo   [WARN] install.ps1 not found - install.bat will fail!
)

REM Copy .env.example (handle with or without leading dot)
if exist ".env.example" (
    copy /y ".env.example" "%DIST_DIR%\.env.example" >nul
    echo   [OK] .env.example
) else if exist "env.example" (
    copy /y "env.example" "%DIST_DIR%\.env.example" >nul
    echo   [OK] env.example -^> .env.example
) else (
    echo   [WARN] .env.example not found
)

REM Copy README_INSTALL.txt
if exist "README_INSTALL.txt" (
    copy /y "README_INSTALL.txt" "%DIST_DIR%\README_INSTALL.txt" >nul
    echo   [OK] README_INSTALL.txt
) else (
    echo   [WARN] README_INSTALL.txt not found
)

REM =============================================================================
REM Done
REM =============================================================================
echo.
echo ============================================================
echo   BUILD COMPLETE
echo.
echo   Distribution folder: dist\%DIST_NAME%\
echo.
echo   Contents summary:
echo     exe + _internal\    PyInstaller bundle (Python runtime + packages)
echo     docs\instrument_commands_json\   SCPI databases
echo     docs\*.md           Root docs (searched by server)
echo     docs\reference\     Reference files (*.md searched by server)
echo     docs\python_examples\   Golden example scripts
echo     PTA\test_suites\    Plugin examples (searched by server)
echo     PTA\lessons_learned\    Session lessons (searched by server)
echo     install.bat         Recipient runs this — that's it
echo.
echo   To share: zip dist\%DIST_NAME% and send it.
echo ============================================================
pause
