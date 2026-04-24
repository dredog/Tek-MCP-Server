# pyinstaller_runtime_hook.py
# Runs before tektronix_mcp_server.py — used by PyInstaller only.
# This file must be in the same directory as the .spec file.
#
# Two jobs:
# 1. Detect accidental double-click and show a helpful message instead of
#    hanging on stdin.
# 2. Set TEK_INSTALL_PATH to the exe's actual directory as a safety net,
#    in case the Claude Desktop config's env block didn't set it.
#    (The server already reads this env var on line 246.)

import sys
import os
from pathlib import Path

# ── Safety net: set TEK_INSTALL_PATH before server code runs ──────────────────
# sys.executable is always the real .exe path in a frozen bundle.
# Path(__file__) inside frozen code is NOT reliable — it points to the
# temp extraction directory, which is why this hook exists.
if getattr(sys, 'frozen', False) and 'TEK_INSTALL_PATH' not in os.environ:
    os.environ['TEK_INSTALL_PATH'] = str(Path(sys.executable).parent)

# ── Friendly message if someone double-clicks the exe directly ────────────────
# Claude Desktop launches this as a subprocess with a pipe on stdin (not a tty).
# If stdin IS a tty, a human double-clicked it — show a helpful message and exit.
if getattr(sys, 'frozen', False):
    try:
        if sys.stdin and sys.stdin.isatty():
            print("=" * 60)
            print("  Tektronix MCP Server")
            print("=" * 60)
            print()
            print("  This executable is an MCP server for Claude Desktop.")
            print("  It should not be run directly.")
            print()
            print("  To install: run install.bat in this folder.")
            print("  Once installed, Claude Desktop will launch this")
            print("  automatically when it starts.")
            print()
            input("  Press Enter to exit...")
            sys.exit(0)
    except Exception:
        pass  # If stdin check fails for any reason, let the server start normally
