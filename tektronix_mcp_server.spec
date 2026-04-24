# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# tektronix_mcp_server.spec
# PyInstaller build specification for Tektronix MCP Server v1.3.5
#
# Place this file in C:\Users\u610842\TektronixMCP\ alongside the server.
# Build by running build.bat — do not run pyinstaller directly.
#
# Architecture decision: --onedir (not --onefile)
# --onefile extracts to a temp folder on every launch, adding 3-5 seconds
# to startup. MCP servers are launched by Claude Desktop on every session
# start, so that delay is felt constantly. --onedir extracts once and is
# fast on subsequent runs.
# =============================================================================

from PyInstaller.utils.hooks import collect_all, collect_submodules

# =============================================================================
# PACKAGE COLLECTION
# Using collect_all() rather than manually listing hiddenimports.
# collect_all() captures submodules, data files, and binaries in one call,
# which is essential for packages that use dynamic imports or entry points.
# =============================================================================

datas    = []
binaries = []
hiddenimports = []

# Packages that need full recursive collection.
# These either use dynamic imports, entry points, or have data files
# (JSON schemas, SSL certs, etc.) that must travel with the exe.
_collect_packages = [
    'mcp',          # Anthropic MCP SDK — mcp.server.fastmcp, mcp.server.stdio, etc.
    'fastmcp',      # Standalone fastmcp package (also in requirements)
    'pydantic',     # v2 uses compiled Rust extensions — collect_all handles them
    'anyio',        # Async backend — must include _backends._asyncio for Windows
    'pyvisa_py',    # Pure-Python VISA backend — registered via entry points
    'openai',       # OpenAI SDK — has many lazy-imported submodules
    'httpx',        # HTTP client used by mcp and openai
    'httpcore',     # httpx dependency — also uses dynamic imports
    'PIL',          # Pillow — image format plugins are dynamically loaded
    'certifi',      # SSL certificates — openai/httpx need this data file
    'dotenv',       # python-dotenv — included even though server reads env directly
    'jsonschema',   # JSON schema validation — used by MCP, needs format checkers
    'jsonschema_specifications',  # Ships JSON schema files as package data — MUST collect
    'referencing',  # jsonschema_specifications dependency — also has package data
    'rfc3987',      # URI validation for jsonschema — has .lark grammar files
    'rfc3987_syntax',  # RFC3987 syntax parser — MUST include .lark data files
]

for pkg in _collect_packages:
    try:
        d, b, h = collect_all(pkg)
        datas    += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"[spec] Warning: collect_all('{pkg}') failed: {e}")

# pyvisa core: collect_all handles pyvisa_py but pyvisa itself needs
# collect_submodules because its resources are loaded by string name at runtime.
hiddenimports += collect_submodules('pyvisa')

# =============================================================================
# EXPLICIT DATA FILE COLLECTION
# Some packages have data files that collect_all() misses. We add them here.
# =============================================================================

import importlib.util
import os

# rfc3987_syntax needs its .lark grammar files
try:
    spec = importlib.util.find_spec('rfc3987_syntax')
    if spec and spec.origin:
        pkg_dir = os.path.dirname(spec.origin)
        # Collect all .lark files from the package directory
        for f in os.listdir(pkg_dir):
            if f.endswith('.lark'):
                datas.append((os.path.join(pkg_dir, f), 'rfc3987_syntax'))
        print(f"[spec] Added rfc3987_syntax .lark files from {pkg_dir}")
except Exception as e:
    print(f"[spec] Warning: Could not collect rfc3987_syntax data files: {e}")

# =============================================================================
# ANALYSIS
# =============================================================================

a = Analysis(
    ['tektronix_mcp_server.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [

        # ── Windows asyncio (proactor event loop) ─────────────────────────
        # anyio on Windows uses ProactorEventLoop. Without this, asyncio
        # operations (including MCP stdio transport) silently fall back or fail.
        'asyncio.proactor_events',
        'asyncio.windows_events',
        'asyncio.windows_utils',

        # ── SSL / TLS ─────────────────────────────────────────────────────
        # openai and httpx require SSL. PyInstaller sometimes misses these.
        'ssl',
        '_ssl',

        # ── Encoding support ──────────────────────────────────────────────
        # The server explicitly re-opens stdout/stderr with UTF-8 encoding.
        # PyInstaller's bootloader needs these codec modules available.
        'encodings',
        'encodings.utf_8',
        'encodings.utf_16',
        'encodings.cp1252',
        'encodings.ascii',
        'encodings.latin_1',

        # ── Standard library items PyInstaller sometimes misses ───────────
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.base',
        'urllib.parse',
        'urllib.request',
        'urllib.error',
        'http.client',
        'http.cookiejar',
        'multiprocessing.pool',

    ],

    # Look for custom hooks in this directory (none currently, but keeps
    # the option open for future pyvisa-py entry-point hooks if needed).
    hookspath=['.'],

    # Runtime hook runs before any server code — sets TEK_INSTALL_PATH
    # and handles accidental double-click. Must be in the same directory
    # as this spec file.
    runtime_hooks=['pyinstaller_runtime_hook.py'],

    excludes=[
        # ── Wake listener packages (run on host, not in this exe) ─────────
        'speech_recognition',
        'pyaudio',
        'pyttsx3',
        'faster_whisper',
        'openwakeword',
        'pyautogui',
        'pygetwindow',
        # ── Tek PTA GUI (runs as separate application) ────────────────────
        'matplotlib',
        'reportlab',
        'tkinter',
        '_tkinter',
        # ── Heavy scientific stack (not used by the server) ───────────────
        'numpy',
        'scipy',
        'pandas',
        'sklearn',
        # ── Dev / test tools (never needed at runtime) ────────────────────
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
        'setuptools',
        'pkg_resources',
        # ── GUI frameworks (not used by the server) ───────────────────────
        'wx',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],

    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

# =============================================================================
# PYZ (Python bytecode archive)
# =============================================================================

pyz = PYZ(a.pure, a.zipped_data)

# =============================================================================
# EXE
# console=True is REQUIRED for stdio MCP transport.
# If console=False, PyInstaller redirects stdin/stdout to the GUI subsystem,
# which silently breaks the MCP pipe between Claude Desktop and the server.
# =============================================================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # Binaries go in COLLECT, not inside the exe
    name='tektronix_mcp_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                   # Compress binaries — reduces folder size ~30%
    console=True,               # MUST be True — see note above
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# =============================================================================
# COLLECT (--onedir output folder)
# Everything in dist\tektronix_mcp_server\
# =============================================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='tektronix_mcp_server',
)
