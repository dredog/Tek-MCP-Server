#!/usr/bin/env python3
# =============================================================================
# CRITICAL: UNBUFFERED I/O - MUST BE BEFORE ALL OTHER CODE
# =============================================================================
import sys
import os

# Force unbuffered stdout/stderr for MCP stdio transport
# This prevents response buffering that causes timeouts
os.environ['PYTHONUNBUFFERED'] = '1'

# Reopen stdout/stderr with line buffering AND UTF-8 encoding (fixes Windows cp1252 issues)
if hasattr(sys.stdout, 'fileno'):
    try:
        sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', buffering=1, closefd=False)
        sys.stderr = open(sys.stderr.fileno(), 'w', encoding='utf-8', buffering=1, closefd=False)
    except:
        pass  # May fail in some environments, that's ok

"""
Tektronix MCP Server v1.1.0
===========================
MCP server for Tektronix instrument automation with authoritative SCPI commands.

CRITICAL: NEVER invent SCPI commands. All commands must be verified in:
1. JSON files in docs/instrument_commands_json/
2. Programmer manuals in docs/programmer_manuals/
3. Python examples in docs/python_examples/
4. OpenAI vector store
5. dev.tek.com (vetted and approved)

Supported Instruments (11 databases, 20,000+ commands):
───────────────────────────────────────────────────────
OSCILLOSCOPES - Modern Series (Combined Database):
  • MSO 2/4/5/6 Series: MSO22, MSO24, MSO44/B, MSO46/B, MSO54/B, 
                        MSO56/B, MSO58/B/LP, MSO64/B, MSO66/B, 
                        MSO68/B, LPD64
  • DPO 7 Series: DPO714A, DPO714AX, DPO718A, DPO718AX
  • MDO 3 Series: MDO32, MDO34

OSCILLOSCOPES - Legacy 4-digit Series:
  • MDO4000/B/C: MDO4014B/C through MDO4104C
  • MSO/DPO4000B: MSO4014B-MSO4104B, DPO4014B-DPO4104B
  • MDO3000 Series: MDO3012 through MDO3104C
  • MSO/DPO 5000/B: MSO5034-MSO5204B, DPO5034-DPO5204B
  • DPO 7000/C: DPO7054-DPO7354C

OSCILLOSCOPES - Performance Series (5k/7k/70k Combined):
  • DPO 70000: DPO70404-DPO77002SX
  • MSO 70000: MSO70404C-MSO73304DX
  • DSA 70000: DSA70404-DSA72004

SIGNAL GENERATORS:
  • AFG31000 Series: AFG31021/22, AFG31051/52, AFG31101/02, 
                     AFG31151/52, AFG31251/52
  • AWG5200 Series: AWG5202, AWG5204, AWG5208
  • AWG70000 Series: AWG70001A/B, AWG70002A/B

AWG APPLICATION PLUG-INS:
  • High Speed Serial (HSS): PRBS patterns, jitter/noise injection,
                             ISI, S-parameter channel emulation
                             (Requires 5-HSS license on AWG5200/AWG70000)

SPECTRUM ANALYZERS & SIGNAL ANALYSIS:
  • SignalVu: SignalVu-PC, RSA306B, RSA500/600, MSO5x/6x with SignalVu

SOURCE MEASURE UNITS:
  • Keithley SMU: 2400 series, 2450/2460/2461/2470, 2600B series, 2651A

Features:
- 20,000+ SCPI commands from official documentation
- OpenAI vector store integration
- Tek PTA production test framework
- Live instrument control via PyVISA
- Wake-word voice control support (Hey Tek)
- Status indicator visible in Claude chat UI
- Local docs search includes Tek PTA source files

v1.1.0 Changes:
- Added live instrument control via PyVISA (persistent sessions)
- New tools: connect, disconnect, write, query, batch, state, screenshot
- New tools: run, stop, single, autoset (acquisition control)
- Instrument state save/restore for undo capability
- Thread-safe VISA operations with locking
- Designed for conversational debug workflow with wake-word listener

v1.0.2 Changes:
- Added tek_pta_plugin_template() tool - returns EXACT plugin structure
- Added tek_pta_plugin_checklist() tool - development checklist
- tek_search_local_docs() now warns when plugin queries detected
- tek_status() now shows plugin development tools
- Expanded plugin query detection terms
- Fixes silent plugin loading failures by ensuring correct structure

v3.8 Changes:
- Extended tek_search_local_docs to search Python source files
- Now indexes: tek_pta.py, tek_pta_plugin_api.py, test_suites/*.py
- Added file type indicators (Python vs Markdown) in search results
- Boosted relevance for plugin/suite searches
- Enables Claude to read actual implementation patterns
- Added tek_save_lessons_learned tool for capturing test development knowledge
- Added tek_list_lessons_learned tool to view saved lessons
- Lessons learned files stored in PTA/lessons_learned/ and auto-indexed

v3.7 Changes:
- Added MDO3 Series aliases: mdo32, mdo34
- Added dpo70k alias for backwards compatibility
- Added additional legacy aliases: dpo4000, mso4000
- Updated params extraction for MDO3 and MDO4000 series JSON files
- Removed dpo70k_commands.json (merged into mso_dpo_5k_7k_70k)

v3.6 Changes:
- Consolidated DPO/MSO/DSA 70000 into MSO_DPO_5k_7k_70K database
- Added aliases: dpo70000, mso70000, dsa70000, dpo7000, mso5000, dpo5000
- Added aliases: mdo4000, mso4000b, dpo4000b, mdo3000
- Removed redundant dpo70k_commands.json reference

v3.5 Changes:
- Combined MSO 2/4/5/6/7 command database (mso_2_4_5_6_7_commands.json)
- New primary instrument key: 'mso' (aliases: mso456, mso2)
- Enhanced params structure with options, types, defaults
- Better argument searching with structured parameter data
- Improved command details display

v3.4 Changes:
- Added unbuffered I/O for reliable MCP transport
- Added explicit flush after every tool response
- Added timeout protection for vector store queries
- Added singleton OpenAI client for connection reuse
- Added periodic garbage collection for long sessions
"""

import json
import re
import gc
import time
import asyncio
import functools
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Optional: OpenAI for vector store
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Optional: PyVISA for live instrument control
try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False

# Optional: PIL/Pillow for screenshot handling
try:
    from PIL import Image
    import base64
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

_request_count: int = 0
_last_gc_time: float = time.time()


def flush_output():
    """Explicitly flush stdout/stderr to prevent MCP transport buffering."""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except:
        pass


def periodic_maintenance():
    """Run periodic cleanup for long-running server health."""
    global _request_count, _last_gc_time
    _request_count += 1
    
    # Run garbage collection every 50 requests or 5 minutes
    current_time = time.time()
    if _request_count % 50 == 0 or (current_time - _last_gc_time) > 300:
        gc.collect()
        _last_gc_time = current_time
        print(f"[Maintenance] GC after {_request_count} requests", file=sys.stderr)
        flush_output()


def with_flush(func):
    """Decorator to ensure stdout/stderr flush after every tool call."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            flush_output()
            periodic_maintenance()
    return wrapper


# =============================================================================
# CONFIGURATION
# =============================================================================

INSTALL_BASE = Path(os.environ.get("TEK_INSTALL_PATH", Path(__file__).parent))
DOCS_PATH = INSTALL_BASE / "docs"
JSON_PATH = DOCS_PATH / "instrument_commands_json"
DOCS_REFERENCE_PATH = DOCS_PATH / "reference"  # Markdown documentation files
LEGACY_MAPPINGS_PATH = DOCS_REFERENCE_PATH / "legacy_command_mappings.json"  # Legacy to modern command mappings
PTA_PATH = INSTALL_BASE / "PTA"  # PTA is now at root level, read-write
PTA_BACKUPS = PTA_PATH / "backups"  # Backups inside PTA folder
PTA_SUITES_PATH = PTA_PATH / "test_suites"  # Test suite plugin files
PTA_LESSONS_PATH = PTA_PATH / "lessons_learned"  # Lessons learned from test development

# Terms that indicate user is asking about Tek PTA plugin development
# Used to trigger warnings and boost relevance in searches
PTA_PLUGIN_QUERY_TERMS = [
    # Direct Tek PTA references
    'plugin', 'pta', 'tek pta', 'tek_pta', 'tekpta',
    'production test', 'production testing',
    # Test suite terminology
    'suite', 'test_suite', 'testsuite', 'test suite',
    'run_test', 'run test',
    # Creating/building tests
    'create test', 'new test', 'write test', 'build test', 'make test',
    'create a test', 'write a test', 'build a test', 'make a test',
    'develop test', 'developing test', 'test development',
    # Automation terminology
    'automation gui', 'automation app', 'automation tool',
    'automated test', 'test automation', 'automate test',
    'measurement automation', 'scope automation', 'oscilloscope automation',
    # Plugin API classes
    'testpoint', 'test_point', 'test point',
    'testengine', 'test_engine', 'test engine', 'engine_class',
    'testsuiteplugin', 'testsuiteconfig',
    'register_suites', 'register suites',
    'generate_test_points', 'setup_instruments', 'run_single_test',
    # Scope/measurement test patterns
    'scope test', 'oscilloscope test', 'mso test', 'dpo test',
    'measurement test', 'scpi test',
    # GUI application
    'gui test', 'gui application', 'test gui', 'test app',
]

# All supported command database files with their instrument families
# CRITICAL: Model numbers must be specific and unambiguous
COMMAND_FILES = {
    # =========================================================================
    # OSCILLOSCOPES - Modern Series (Combined MSO 2/4/5/6 + DPO 7 database)
    # =========================================================================
    "mso": {
        "path": JSON_PATH / "mso_2_4_5_6_7_commands.json",
        "description": "MSO 2/4/5/6 & DPO 7 Series Oscilloscopes (Modern 2-digit models)",
        "models": [
            # MSO 2 Series
            "MSO22", "MSO24", "2 Series MSO",
            # MSO 4 Series (4 or 6 channels)
            "MSO44", "MSO44B", "MSO46", "MSO46B",
            # MSO 5 Series (4, 6, or 8 channels)
            "MSO54", "MSO54B", "MSO56", "MSO56B", "MSO58", "MSO58B", "MSO58LP",
            # MSO 6 Series (4, 6, or 8 channels)
            "MSO64", "MSO64B", "MSO66", "MSO66B", "MSO68", "MSO68B",
            # DPO 7 Series (4 or 8 channels)
            "DPO714A", "DPO714AX", "DPO718A", "DPO718AX",
            # LPD64 (Low Profile Digitizer)
            "LPD64",
        ],
        "aliases": ["mso456", "mso2", "mso4", "mso5", "mso6", "dpo7"],  # For backwards compatibility
    },
    # Legacy alias for backwards compatibility (points to same file)
    "mso456": {
        "path": JSON_PATH / "mso_2_4_5_6_7_commands.json",
        "description": "MSO 4/5/6 Series (alias for 'mso' - use 'mso' for new code)",
        "models": ["MSO44", "MSO54", "MSO64"],
        "is_alias": True,
    },
    "mso2": {
        "path": JSON_PATH / "mso_2_4_5_6_7_commands.json",
        "description": "MSO 2 Series (alias for 'mso' - use 'mso' for new code)",
        "models": ["MSO22", "MSO24"],
        "is_alias": True,
    },
    "mdo3": {
        "path": JSON_PATH / "mdo3_series_commands.json",
        "description": "MDO 3 Series Mixed Domain Oscilloscopes (MDO32, MDO34)",
        "models": [
            "MDO32", "MDO34",
            "3 Series MDO", "MDO 3 Series",
        ],
    },
    
    # =========================================================================
    # OSCILLOSCOPES - Legacy 4-digit Series
    # =========================================================================
    "mdo4000_mso4000b_dpo4000b_mdo3000": {
        "path": JSON_PATH / "mdo4000_mso4000b_dpo4000b_mdo3000_commands.json",
        "description": "MDO4000/B/C, MSO/DPO4000B, MDO3000 Series (4-digit models)",
        "models": [
            # MDO4000 Series
            "MDO4000", "MDO4000B", "MDO4000C",
            "MDO4014B", "MDO4024C", "MDO4034B", "MDO4034C", "MDO4054B", "MDO4054C",
            "MDO4104B", "MDO4104C",
            # MSO/DPO 4000B Series
            "MSO4000B", "DPO4000B",
            "MSO4014B", "MSO4034B", "MSO4054B", "MSO4104B",
            "DPO4014B", "DPO4034B", "DPO4054B", "DPO4104B",
            # MDO3000 Series (legacy, different from MDO 3 Series)
            "MDO3000",
            "MDO3012", "MDO3014", "MDO3022", "MDO3024",
            "MDO3032", "MDO3034", "MDO3052", "MDO3054",
            "MDO3102", "MDO3104", "MDO3104C",
        ],
        "aliases": ["mdo4000", "mso4000b", "dpo4000b", "mdo3000"],
    },
    # Aliases for MDO4000 family (point to same database)
    "mdo4000": {
        "path": JSON_PATH / "mdo4000_mso4000b_dpo4000b_mdo3000_commands.json",
        "description": "MDO4000 Series (alias for 'mdo4000_mso4000b_dpo4000b_mdo3000')",
        "models": ["MDO4014B", "MDO4104C"],
        "is_alias": True,
    },
    "mso4000b": {
        "path": JSON_PATH / "mdo4000_mso4000b_dpo4000b_mdo3000_commands.json",
        "description": "MSO4000B Series (alias for 'mdo4000_mso4000b_dpo4000b_mdo3000')",
        "models": ["MSO4014B", "MSO4104B"],
        "is_alias": True,
    },
    "dpo4000b": {
        "path": JSON_PATH / "mdo4000_mso4000b_dpo4000b_mdo3000_commands.json",
        "description": "DPO4000B Series (alias for 'mdo4000_mso4000b_dpo4000b_mdo3000')",
        "models": ["DPO4014B", "DPO4104B"],
        "is_alias": True,
    },
    "mdo3000": {
        "path": JSON_PATH / "mdo4000_mso4000b_dpo4000b_mdo3000_commands.json",
        "description": "MDO3000 Series (alias for 'mdo4000_mso4000b_dpo4000b_mdo3000')",
        "models": ["MDO3012", "MDO3104C"],
        "is_alias": True,
    },
    "mso_dpo_5k_7k_70k": {
        "path": JSON_PATH / "MSO_DPO_5k_7k_70K_commands.json",
        "description": "MSO/DPO 5000/7000/70000 & DSA70000 Series (Performance oscilloscopes)",
        "models": [
            # MSO/DPO 5000 Series
            "MSO5000", "MSO5000B", "DPO5000", "DPO5000B",
            "MSO5034", "MSO5034B", "MSO5054", "MSO5054B",
            "MSO5104", "MSO5104B", "MSO5204", "MSO5204B",
            "DPO5034", "DPO5034B", "DPO5054", "DPO5054B",
            "DPO5104", "DPO5104B", "DPO5204", "DPO5204B",
            # DPO 7000 Series
            "DPO7000", "DPO7000C",
            "DPO7054", "DPO7054C", "DPO7104", "DPO7104C",
            "DPO7254", "DPO7254C", "DPO7354", "DPO7354C",
            # DPO 70000 Series
            "DPO70000", "DPO70000B", "DPO70000C", "DPO70000D", 
            "DPO70000DX", "DPO70000SX",
            "DPO70404", "DPO70604", "DPO70804", "DPO71254", "DPO71604", "DPO72004",
            "DPO72304DX", "DPO72504DX", "DPO73304DX", "DPO73304SX",
            "DPO75002SX", "DPO75902SX", "DPO77002SX",
            # MSO 70000 Series
            "MSO70000", "MSO70000C", "MSO70000DX",
            "MSO70404C", "MSO70604C", "MSO70804C", "MSO71254C", "MSO71604C",
            "MSO72004C", "MSO72304DX", "MSO72504DX", "MSO73304DX",
            # DSA 70000 Series
            "DSA70000", "DSA70404", "DSA70604", "DSA70804",
            "DSA71254", "DSA71604", "DSA72004",
        ],
        "aliases": ["dpo70000", "mso70000", "dsa70000", "dpo7000", "mso5000", "dpo5000"],
    },
    # Aliases for legacy 5k/7k/70k series (point to same database)
    "dpo70000": {
        "path": JSON_PATH / "MSO_DPO_5k_7k_70K_commands.json",
        "description": "DPO70000 Series (alias for 'mso_dpo_5k_7k_70k')",
        "models": ["DPO70404", "DPO71254", "DPO73304SX"],
        "is_alias": True,
    },
    "mso70000": {
        "path": JSON_PATH / "MSO_DPO_5k_7k_70K_commands.json",
        "description": "MSO70000 Series (alias for 'mso_dpo_5k_7k_70k')",
        "models": ["MSO70404C", "MSO73304DX"],
        "is_alias": True,
    },
    "dsa70000": {
        "path": JSON_PATH / "MSO_DPO_5k_7k_70K_commands.json",
        "description": "DSA70000 Series (alias for 'mso_dpo_5k_7k_70k')",
        "models": ["DSA70404", "DSA72004"],
        "is_alias": True,
    },
    "dpo7000": {
        "path": JSON_PATH / "MSO_DPO_5k_7k_70K_commands.json",
        "description": "DPO7000 Series (alias for 'mso_dpo_5k_7k_70k')",
        "models": ["DPO7054", "DPO7354C"],
        "is_alias": True,
    },
    "mso5000": {
        "path": JSON_PATH / "MSO_DPO_5k_7k_70K_commands.json",
        "description": "MSO5000 Series (alias for 'mso_dpo_5k_7k_70k')",
        "models": ["MSO5034", "MSO5204B"],
        "is_alias": True,
    },
    "dpo5000": {
        "path": JSON_PATH / "MSO_DPO_5k_7k_70K_commands.json",
        "description": "DPO5000 Series (alias for 'mso_dpo_5k_7k_70k')",
        "models": ["DPO5034", "DPO5204B"],
        "is_alias": True,
    },
    
    # =========================================================================
    # SIGNAL GENERATORS
    # =========================================================================
    "afg31000": {
        "path": JSON_PATH / "afg31000-commands.json",
        "description": "AFG31000 Series Arbitrary Function Generators",
        "models": [
            # 25 MHz models
            "AFG31021", "AFG31022",
            # 50 MHz models
            "AFG31051", "AFG31052",
            # 100 MHz models
            "AFG31101", "AFG31102",
            # 150 MHz models
            "AFG31151", "AFG31152",
            # 250 MHz models
            "AFG31251", "AFG31252",
        ],
    },
    "awg5200": {
        "path": JSON_PATH / "awg5200_commands.json",
        "description": "AWG5200 Series Arbitrary Waveform Generators",
        "models": [
            "AWG5202",  # 2 channels
            "AWG5204",  # 4 channels
            "AWG5208",  # 8 channels
        ],
    },
    "awg70000": {
        "path": JSON_PATH / "awg70000_commands.json",
        "description": "AWG70000 Series Arbitrary Waveform Generators",
        "models": [
            "AWG70001A", "AWG70001B",  # 1 channel
            "AWG70002A", "AWG70002B",  # 2 channels
        ],
    },
    
    # =========================================================================
    # AWG APPLICATION PLUG-INS
    # =========================================================================
    "hss_plugin": {
        "path": JSON_PATH / "hss_plugin_commands.json",
        "description": "High Speed Serial Plug-in (for AWG5200/AWG70000)",
        "models": [
            # AWG5200 Series with HSS
            "AWG5202", "AWG5204", "AWG5208",
            # AWG70000 Series with HSS  
            "AWG70001A", "AWG70001B", "AWG70002A", "AWG70002B",
            # SourceXpress software
            "SourceXpress",
        ],
        "license": "5-HSS",
        "compatible_with": ["awg5200", "awg70000"],
        "features": [
            "PRBS pattern generation",
            "Random Jitter (RJ) injection",
            "Periodic Jitter (PJ/SJ) injection", 
            "Duty Cycle Distortion (DCD)",
            "ISI channel emulation",
            "S-Parameter channel modeling",
            "Pre-emphasis/De-emphasis",
            "Spread Spectrum Clocking (SSC)",
            "8B/10B encoding",
            "PAM4 modulation",
        ],
    },
    
    # =========================================================================
    # SPECTRUM ANALYZERS & SIGNAL ANALYSIS
    # =========================================================================
    "signalvu": {
        "path": JSON_PATH / "signalvu-commands.json",
        "description": "SignalVu Vector Signal Analysis Software",
        "models": [
            # Software
            "SignalVu-PC",
            # USB Real-Time Spectrum Analyzers
            "RSA306B", "RSA500", "RSA503A", "RSA507A",
            "RSA600", "RSA603A", "RSA607A",
            # MSO with SignalVu option
            "MSO54-SignalVu", "MSO56-SignalVu", "MSO58-SignalVu",
            "MSO64-SignalVu", "MSO66-SignalVu", "MSO68-SignalVu",
        ],
    },
    
    # =========================================================================
    # SOURCE MEASURE UNITS
    # =========================================================================
    "smu": {
        "path": JSON_PATH / "smu_commands.json",
        "description": "Keithley SMU Source Measure Units",
        "models": [
            # 2400 Series (legacy)
            "2400", "2401", "2410", "2420", "2425", "2430", "2440",
            # 2400 Graphical Series
            "2450", "2460", "2461", "2470",
            # 2600B Series
            "2600", "2600B", "2601B", "2602B", "2604B",
            "2611B", "2612B", "2614B",
            "2634B", "2635B", "2636B",
            # 2651A High Power
            "2651A",
        ],
    },
}

# Instrument alias mapping - maps user-friendly names to primary database keys
# This allows users to search with "dpo70000" instead of "mso_dpo_5k_7k_70k"
INSTRUMENT_ALIASES = {
    # MSO Modern series aliases -> "mso"
    "mso456": "mso",
    "mso2": "mso",
    "mso4": "mso",
    "mso5": "mso",
    "mso6": "mso",
    "dpo7": "mso",
    # MDO 3 Series aliases -> "mdo3"
    "mdo32": "mdo3",
    "mdo34": "mdo3",
    # MDO4000 family aliases -> "mdo4000_mso4000b_dpo4000b_mdo3000"
    "mdo4000": "mdo4000_mso4000b_dpo4000b_mdo3000",
    "mso4000b": "mdo4000_mso4000b_dpo4000b_mdo3000",
    "dpo4000b": "mdo4000_mso4000b_dpo4000b_mdo3000",
    "mdo3000": "mdo4000_mso4000b_dpo4000b_mdo3000",
    "dpo4000": "mdo4000_mso4000b_dpo4000b_mdo3000",
    "mso4000": "mdo4000_mso4000b_dpo4000b_mdo3000",
    # MSO/DPO 5k/7k/70k family aliases -> "mso_dpo_5k_7k_70k"
    "dpo70k": "mso_dpo_5k_7k_70k",  # Legacy key for backwards compatibility
    "dpo70000": "mso_dpo_5k_7k_70k",
    "mso70000": "mso_dpo_5k_7k_70k",
    "dsa70000": "mso_dpo_5k_7k_70k",
    "dpo7000": "mso_dpo_5k_7k_70k",
    "mso5000": "mso_dpo_5k_7k_70k",
    "dpo5000": "mso_dpo_5k_7k_70k",
    "dpo70k_7k_5k": "mso_dpo_5k_7k_70k",  # Alternative naming
}

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
VECTOR_STORE_ID = os.environ.get("TEK_VECTOR_STORE_ID", "")

# =============================================================================
# SINGLETON OPENAI CLIENT (Connection Reuse)
# =============================================================================

_openai_client: Optional[OpenAI] = None


def get_openai_client() -> Optional[OpenAI]:
    """Get or create singleton OpenAI client for connection reuse."""
    global _openai_client
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        return None
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=30.0,
            max_retries=2
        )
    return _openai_client


# =============================================================================
# INITIALIZE MCP SERVER
# =============================================================================

mcp = FastMCP("tektronix")

_commands_db: Dict[str, Dict] = {}
_commands_flat: Dict[str, List[Dict]] = {}
_total_commands: int = 0
_server_start_time: datetime = datetime.now()

# =============================================================================
# LIVE INSTRUMENT SESSION STATE
# =============================================================================

_visa_rm: Optional[Any] = None           # PyVISA ResourceManager
_visa_session: Optional[Any] = None      # Active VISA instrument session
_visa_resource_string: str = ""           # Connected resource string
_visa_idn: str = ""                      # Cached *IDN? response
_visa_lock = threading.Lock()            # Thread safety for VISA operations
_saved_instrument_state: Optional[str] = None  # Saved state for undo (*LRN? response)


def load_commands_database():
    """Load all JSON command databases."""
    global _commands_db, _commands_flat, _total_commands
    
    loaded_paths = set()  # Track loaded files to avoid duplicates from aliases
    
    for name, config in COMMAND_FILES.items():
        # Skip alias entries (they point to already-loaded files)
        if config.get("is_alias"):
            continue
            
        path = config["path"]
        
        # Skip if we've already loaded this file
        if str(path) in loaded_paths:
            continue
            
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                _commands_db[name] = data
                _commands_flat[name] = _flatten_commands(data, name)
                loaded_paths.add(str(path))
                print(f"✓ {name}: {len(_commands_flat[name]):,} commands ({config['description']})", file=sys.stderr)
                flush_output()
            except Exception as e:
                print(f"✗ {path.name}: {e}", file=sys.stderr)
                flush_output()
        else:
            print(f"⚠ {name}: File not found - {path}", file=sys.stderr)
            flush_output()
    
    _total_commands = sum(len(cmds) for cmds in _commands_flat.values())


def _flatten_commands(data: Dict, instrument_key: str) -> List[Dict]:
    """Flatten hierarchical JSON into a flat list of commands.
    
    Handles multiple JSON formats:
    1. groups -> {group_name: {commands: [...]}} (mso_commands, afg31000, signalvu, awg)
    2. commandGroups -> {group_name: {commands: [...]}} (alternative key)
    3. commands -> {scpi_name: {...}} (dpo70k flat dictionary format)
    4. metadata + commands format
    """
    flat = []
    
    # Format 1 & 2: Groups with nested commands arrays
    groups = data.get("groups", data.get("commandGroups", {}))
    if groups and isinstance(groups, dict):
        for group_name, group_data in groups.items():
            if isinstance(group_data, dict) and "commands" in group_data:
                for cmd in group_data.get("commands", []):
                    cmd_copy = cmd.copy()
                    cmd_copy["group"] = group_name
                    cmd_copy["_instrument"] = instrument_key
                    # Normalize scpi field (some files use "name" instead)
                    if "scpi" not in cmd_copy and "name" in cmd_copy:
                        # For SMU-style entries, the scpi is in a different field
                        pass  # Keep as-is, we'll handle in search
                    flat.append(cmd_copy)
    
    # Format 3: Flat commands dictionary (dpo70k style)
    commands_dict = data.get("commands", {})
    if commands_dict and isinstance(commands_dict, dict) and not flat:
        for scpi_key, cmd_data in commands_dict.items():
            if isinstance(cmd_data, dict):
                cmd_copy = cmd_data.copy()
                if "scpi" not in cmd_copy:
                    cmd_copy["scpi"] = scpi_key
                cmd_copy["_instrument"] = instrument_key
                flat.append(cmd_copy)
    
    return flat


# =============================================================================
# SEARCH FUNCTIONS
# =============================================================================

def search_commands(query: str, instrument: str = None, limit: int = 10) -> List[Dict]:
    """Search commands by keyword across all or specific instrument databases.
    
    Args:
        query: Search terms (space-separated)
        instrument: Optional instrument key to limit search (e.g., "mso", "afg31000")
        limit: Maximum results to return
    
    Returns:
        List of matching command dictionaries with _instrument and _score fields
    """
    # Handle instrument aliases (mso456, mso2, dpo7 -> mso, etc.)
    if instrument:
        instrument_lower = instrument.lower()
        instrument = INSTRUMENT_ALIASES.get(instrument_lower, instrument_lower)
    
    # Determine which instruments to search (skip alias entries to avoid duplicates)
    if instrument and instrument in _commands_flat:
        instruments = [instrument]
    else:
        # Exclude alias entries to avoid duplicate results
        instruments = [k for k in _commands_flat.keys() if not COMMAND_FILES.get(k, {}).get("is_alias")]
    
    query_lower = query.lower()
    query_terms = query_lower.split()
    
    all_results = []
    for inst in instruments:
        for cmd in _commands_flat.get(inst, []):
            score = 0
            
            # Get searchable fields
            scpi = cmd.get("scpi", cmd.get("name", "")).lower()
            desc = cmd.get("description", "").lower()
            group = cmd.get("group", "").lower()
            syntax = str(cmd.get("syntax", "")).lower()
            args = str(cmd.get("arguments", cmd.get("params", ""))).lower()
            
            # Also search in params array (new structure)
            params = cmd.get("params", [])
            params_text = ""
            if isinstance(params, list):
                for p in params:
                    if isinstance(p, dict):
                        params_text += f" {p.get('name', '')} {p.get('description', '')} {' '.join(p.get('options', []))}"
            params_text = params_text.lower()
            
            # Exact SCPI match (highest priority)
            if query_lower == scpi or query_lower == scpi.replace("?", ""):
                score += 200
            
            # SCPI contains query
            if query_lower in scpi:
                score += 100
            
            # Term matching
            for term in query_terms:
                if term in scpi:
                    score += 30
                if term in desc:
                    score += 20
                if term in group:
                    score += 15
                if term in syntax:
                    score += 10
                if term in args:
                    score += 8
                if term in params_text:
                    score += 5
            
            if score > 0:
                result = cmd.copy()
                result["_instrument"] = inst
                result["_score"] = score
                all_results.append(result)
    
    # Sort by score descending
    all_results.sort(key=lambda x: x["_score"], reverse=True)
    
    # Deduplicate by SCPI command (keep highest scoring)
    seen = set()
    unique = []
    for r in all_results:
        key = r.get("scpi", r.get("name", "")).upper()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    return unique[:limit]


def get_command_details(scpi: str, instrument: str = None) -> Optional[Dict]:
    """Get specific command details by exact SCPI command.
    
    Args:
        scpi: The SCPI command (e.g., "CH1:SCAle", "ACQuire:MODe")
        instrument: Optional instrument key to limit search
        
    Returns:
        Command dictionary or None if not found
    """
    # Handle instrument aliases
    if instrument:
        instrument_lower = instrument.lower()
        instrument = INSTRUMENT_ALIASES.get(instrument_lower, instrument_lower)
    
    # Normalize query
    scpi_upper = scpi.upper().strip()
    scpi_no_query = scpi_upper.rstrip("?")
    
    # Determine instruments to search (exclude aliases)
    if instrument and instrument in _commands_flat:
        instruments = [instrument]
    else:
        instruments = [k for k in _commands_flat.keys() if not COMMAND_FILES.get(k, {}).get("is_alias")]
    
    for inst in instruments:
        for cmd in _commands_flat.get(inst, []):
            cmd_scpi = cmd.get("scpi", cmd.get("name", "")).upper()
            # Match with or without query suffix
            if cmd_scpi == scpi_upper or cmd_scpi == scpi_no_query or cmd_scpi.rstrip("?") == scpi_no_query:
                result = cmd.copy()
                result["_instrument"] = inst
                return result
    
    return None


def list_groups(instrument: str = None) -> Dict[str, List[str]]:
    """List all command groups.
    
    Args:
        instrument: Optional instrument key to limit to one family
        
    Returns:
        Dictionary mapping instrument key to list of group names
    """
    # Handle aliases
    if instrument:
        instrument_lower = instrument.lower()
        instrument = INSTRUMENT_ALIASES.get(instrument_lower, instrument_lower)
    
    if instrument and instrument in _commands_flat:
        instruments = [instrument]
    else:
        instruments = [k for k in _commands_flat.keys() if not COMMAND_FILES.get(k, {}).get("is_alias")]
    
    result = {}
    for inst in instruments:
        groups = set()
        for cmd in _commands_flat.get(inst, []):
            group = cmd.get("group", "")
            if group:
                groups.add(group)
        result[inst] = sorted(list(groups))
    
    return result


def get_group_commands(group: str, instrument: str = None) -> List[Dict]:
    """Get all commands in a specific group.
    
    Args:
        group: Group name (case-insensitive)
        instrument: Optional instrument key to limit search
        
    Returns:
        List of command dictionaries in the group
    """
    # Handle aliases
    if instrument:
        instrument_lower = instrument.lower()
        instrument = INSTRUMENT_ALIASES.get(instrument_lower, instrument_lower)
    
    if instrument and instrument in _commands_flat:
        instruments = [instrument]
    else:
        instruments = [k for k in _commands_flat.keys() if not COMMAND_FILES.get(k, {}).get("is_alias")]
    
    group_lower = group.lower()
    
    results = []
    for inst in instruments:
        for cmd in _commands_flat.get(inst, []):
            cmd_group = cmd.get("group", "").lower()
            if cmd_group == group_lower or group_lower in cmd_group:
                result = cmd.copy()
                result["_instrument"] = inst
                results.append(result)
    
    return results


def validate_scpi_commands(text: str) -> Dict[str, Any]:
    """Extract and validate SCPI commands from text.
    
    Args:
        text: Text containing SCPI commands
        
    Returns:
        Dictionary with 'validated' and 'not_found' lists
    """
    patterns = [
        r'\b([A-Z][A-Z0-9]*(?::[A-Z][A-Z0-9]*)+(?:\?)?)\b',
        r'\b(\*[A-Z]{2,4}\??)\b',
    ]
    
    found = set()
    for pattern in patterns:
        found.update(re.findall(pattern, text.upper()))
    
    # Filter out common false positives
    false_positives = {'HTTP', 'HTTPS', 'TCP', 'USB', 'GPIB', 'LAN', 'IEEE', 
                       'ASCII', 'TCPIP', 'VISA', 'SCPI', 'NI', 'API'}
    found = {cmd for cmd in found if cmd not in false_positives}
    
    validated, not_found = [], []
    for cmd in found:
        result = get_command_details(cmd)
        if result:
            validated.append({
                "command": cmd, 
                "instrument": result.get("_instrument"),
                "description": result.get("description", "")[:100]
            })
        else:
            not_found.append(cmd)
    
    return {"validated": validated, "not_found": not_found}


def query_vector_store(query: str, timeout_seconds: float = 25.0) -> Optional[str]:
    """Query OpenAI vector store for complex procedural questions.
    
    Args:
        query: The search query
        timeout_seconds: Maximum time to wait for response (default 25s)
        
    Returns:
        Response text or None if failed/timeout
    """
    client = get_openai_client()
    if not client or not VECTOR_STORE_ID:
        return None
    
    assistant = None
    thread = None
    
    try:
        # Create thread and message
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=query)
        
        # Create assistant
        assistant = client.beta.assistants.create(
            name="Tektronix Docs",
            instructions="Search Tektronix documentation. Return SCPI commands and procedures.",
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [VECTOR_STORE_ID]}}
        )
        
        # Poll with timeout
        start_time = time.time()
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
        
        while time.time() - start_time < timeout_seconds:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run.status == "completed":
                break
            elif run.status in ["failed", "cancelled", "expired"]:
                print(f"Vector store run {run.status}", file=sys.stderr)
                return None
            time.sleep(0.5)
        else:
            # Timeout reached
            print(f"Vector store timeout after {timeout_seconds}s", file=sys.stderr)
            try:
                client.beta.threads.runs.cancel(thread_id=thread.id, run_id=run.id)
            except:
                pass
            return None
        
        # Get result
        result = None
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in messages.data:
            if msg.role == "assistant":
                for content in msg.content:
                    if content.type == "text":
                        result = content.text.value
                        break
        
        return result
        
    except Exception as e:
        print(f"Vector store error: {e}", file=sys.stderr)
        return None
        
    finally:
        # Cleanup
        try:
            if assistant:
                client.beta.assistants.delete(assistant.id)
            if thread:
                client.beta.threads.delete(thread.id)
        except:
            pass
        flush_output()


# =============================================================================
# MCP TOOL INPUT MODELS
# =============================================================================

class SearchInput(BaseModel):
    query: str = Field(description="Search keywords (e.g., 'vertical scale', 'trigger level')")
    instrument: Optional[str] = Field(default=None, description="Instrument key: mso, mdo3, mdo4000, mso_dpo_5k_7k_70k, afg31000, awg5200, awg70000, hss_plugin, signalvu, smu (aliases: mso456, dpo70k, dpo70000, etc.)")
    limit: int = Field(default=5, description="Maximum results (default: 5)")

class CommandInput(BaseModel):
    scpi: str = Field(description="The SCPI command (e.g., 'CH1:SCAle', 'ACQuire:MODe')")
    instrument: Optional[str] = Field(default=None, description="Instrument key to limit search (mso, mdo3, afg31000, etc.)")

class GroupInput(BaseModel):
    group: str = Field(description="Group name (e.g., 'Acquisition', 'Vertical', 'Trigger')")
    instrument: Optional[str] = Field(default=None, description="Instrument key to limit search (mso, mdo3, afg31000, etc.)")

class InstrumentInput(BaseModel):
    instrument: Optional[str] = Field(default=None, description="Instrument key: mso, mdo3, mdo4000, mso_dpo_5k_7k_70k, afg31000, awg5200, awg70000, hss_plugin, signalvu, smu")

class VectorSearchInput(BaseModel):
    query: str = Field(description="Natural language question about Tektronix instruments")

class ComprehensiveSearchInput(BaseModel):
    query: str = Field(description="Question about how to do something with Tektronix instruments")
    mode: str = Field(default="auto", description="Search mode: 'fast' (JSON only), 'comprehensive' (vector + validation), 'auto'")

class TemplateInput(BaseModel):
    template_type: str = Field(description="Template type: 'power_supply', 'signal_integrity', 'basic', 'waveform_capture'")


# =============================================================================
# MCP TOOLS - All decorated with @with_flush for reliable transport
# =============================================================================

@mcp.tool()
@with_flush
def tek_search_commands(query: str, instrument: str = None, limit: int = 5) -> str:
    """Search for SCPI commands by keyword or description.
    
    Use this when the user asks how to do something with the oscilloscope.
    Searches across all instrument families unless a specific one is specified.
    
    Instrument keys: mso (MSO 2/4/5/6 + DPO7), mdo3, mdo4000 (MDO4000/MSO4000B/DPO4000B/MDO3000), mso_dpo_5k_7k_70k (DPO70000/MSO70000/DPO7000/MSO5000), afg31000, awg5200, awg70000, hss_plugin, signalvu, smu
    Aliases: mso456, mso2, dpo7, mdo32, mdo34, dpo70k, dpo70000, mso70000, dpo7000, mso5000, dpo5000, mdo3000, mso4000b, dpo4000b
    Legacy aliases: mso456, mso2 (both map to 'mso')
    """
    results = search_commands(query, instrument, limit)
    
    if not results:
        return f"No commands found matching '{query}'. Try different keywords or check tek_list_instruments for available instrument databases."
    
    output = f"## Found {len(results)} commands for '{query}':\n\n"
    for cmd in results:
        scpi = cmd.get("scpi", cmd.get("name", "N/A"))
        desc = cmd.get("description", "No description")[:200]
        inst = cmd.get("_instrument", "unknown")
        group = cmd.get("group", "")
        
        output += f"### `{scpi}`\n"
        output += f"**Instrument:** {inst} | **Group:** {group}\n"
        output += f"{desc}\n"
        
        if cmd.get("syntax"):
            syntax = cmd["syntax"]
            if isinstance(syntax, list):
                output += f"**Syntax:** `{syntax[0]}`\n"
            else:
                output += f"**Syntax:** `{syntax}`\n"
        
        output += "\n---\n"
    
    return output


@mcp.tool()
@with_flush
def tek_get_command(scpi: str, instrument: str = None) -> str:
    """Get detailed information about a specific SCPI command.
    
    Args:
        scpi: The SCPI command (e.g., 'CH1:SCAle', 'ACQuire:MODe')
        instrument: Optional instrument key to limit search (mso, mdo3, afg31000, etc.)
    """
    cmd = get_command_details(scpi, instrument)
    
    if not cmd:
        return f"Command '{scpi}' not found. Use tek_search_commands to find the correct syntax."
    
    output = f"## `{cmd.get('scpi', scpi)}`\n\n"
    output += f"**Instrument:** {cmd.get('_instrument', 'unknown')}\n"
    output += f"**Group:** {cmd.get('group', 'N/A')}\n\n"
    output += f"**Description:** {cmd.get('description', 'No description')}\n\n"
    
    if cmd.get("syntax"):
        syntax = cmd["syntax"]
        if isinstance(syntax, list):
            output += "**Syntax:**\n"
            for s in syntax:
                output += f"- `{s}`\n"
        else:
            output += f"**Syntax:** `{syntax}`\n"
    
    # Show arguments (text description)
    if cmd.get("arguments"):
        output += f"\n**Arguments:**\n{cmd['arguments']}\n"
    
    # Show params (structured parameter info from new JSON format)
    params = cmd.get("params", [])
    if params and isinstance(params, list) and len(params) > 0:
        output += "\n**Parameters:**\n"
        for p in params:
            if isinstance(p, dict):
                name = p.get('name', 'value')
                ptype = p.get('type', 'unknown')
                required = "required" if p.get('required') else "optional"
                default = p.get('default', '')
                options = p.get('options', [])
                
                output += f"- **{name}** ({ptype}, {required})"
                if default:
                    output += f" [default: {default}]"
                output += "\n"
                if options:
                    output += f"  Options: `{' | '.join(str(o) for o in options)}`\n"
    
    if cmd.get("returns"):
        output += f"\n**Returns:** {cmd['returns']}\n"
    
    if cmd.get("examples") or cmd.get("example"):
        examples = cmd.get("examples") or cmd.get("example")
        if isinstance(examples, list):
            output += "\n**Examples:**\n"
            for ex in examples[:3]:  # Limit to 3 examples
                if isinstance(ex, dict):
                    output += f"- `{ex.get('scpi', '')}` - {ex.get('description', '')}\n"
                else:
                    output += f"- `{ex}`\n"
        else:
            output += f"\n**Example:** `{examples}`\n"
    
    return output


@mcp.tool()
@with_flush
def tek_list_groups(instrument: str = None) -> str:
    """List all SCPI command groups (Acquisition, Vertical, Trigger, etc.)
    
    Args:
        instrument: Optional instrument key to limit to one family
    """
    groups_dict = list_groups(instrument)
    
    output = "## Available SCPI Command Groups\n\n"
    
    for inst, groups in groups_dict.items():
        inst_info = COMMAND_FILES.get(inst, {})
        output += f"### {inst} ({inst_info.get('description', '')})\n"
        for group in groups:
            # Count commands in this group
            count = len([c for c in _commands_flat.get(inst, []) if c.get("group", "").lower() == group.lower()])
            output += f"- **{group}** ({count} commands)\n"
        output += "\n"
    
    output += "\nUse `tek_get_group_commands` to see all commands in a group."
    return output


@mcp.tool()
@with_flush
def tek_get_group_commands(group: str, instrument: str = None) -> str:
    """Get all commands in a specific group.
    
    Args:
        group: Group name (e.g., 'Acquisition', 'Vertical', 'Trigger')
        instrument: Optional instrument key to limit search
    """
    commands = get_group_commands(group, instrument)
    
    if not commands:
        return f"No commands found in group '{group}'. Use tek_list_groups to see available groups."
    
    output = f"## {group} Commands ({len(commands)} total)\n\n"
    
    # Group by instrument
    by_instrument = {}
    for cmd in commands:
        inst = cmd.get("_instrument", "unknown")
        if inst not in by_instrument:
            by_instrument[inst] = []
        by_instrument[inst].append(cmd)
    
    for inst, cmds in by_instrument.items():
        output += f"### {inst}\n"
        for cmd in cmds[:20]:  # Limit to 20 per instrument
            scpi = cmd.get("scpi", cmd.get("name", "N/A"))
            desc = cmd.get("description", "")[:80]
            output += f"- `{scpi}` - {desc}\n"
        if len(cmds) > 20:
            output += f"- ... and {len(cmds) - 20} more\n"
        output += "\n"
    
    return output


@mcp.tool()
@with_flush
def tek_list_instruments() -> str:
    """List all available instrument families and their loaded status."""
    output = "## Supported Instrument Families\n\n"
    
    # Show primary entries first
    for key, config in COMMAND_FILES.items():
        if config.get("is_alias"):
            continue
            
        loaded = key in _commands_flat and len(_commands_flat[key]) > 0
        count = len(_commands_flat.get(key, []))
        status = f"✓ {count:,} commands" if loaded else "✗ Not loaded"
        
        output += f"### {key}\n"
        output += f"**{config['description']}**\n"
        output += f"Status: {status}\n"
        
        # Show aliases
        aliases = config.get("aliases", [])
        if aliases:
            output += f"Aliases: {', '.join(aliases)}\n"
        
        # Show license requirement for plugins
        if config.get("license"):
            output += f"License: {config['license']}\n"
        
        # Show compatible instruments for plugins
        if config.get("compatible_with"):
            output += f"Compatible with: {', '.join(config['compatible_with'])}\n"
        
        output += f"Models: {', '.join(config['models'][:5])}"
        if len(config['models']) > 5:
            output += f" +{len(config['models'])-5} more"
        output += "\n\n"
    
    # Show aliases section
    output += "### Legacy Aliases\n"
    output += "These aliases are supported for backwards compatibility:\n"
    for key, config in COMMAND_FILES.items():
        if config.get("is_alias"):
            output += f"- `{key}` → maps to primary database\n"
    output += "\n"
    
    output += f"\n**Total Commands Loaded:** {_total_commands:,}\n"
    output += "\nUse instrument key (e.g., 'mso', 'afg31000') to filter searches."
    
    return output


# =============================================================================
# LOCAL DOCUMENTATION SEARCH (includes Tek PTA source files)
# =============================================================================

def search_local_docs(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search local markdown documentation AND Python source files for relevant content.
    
    Searches:
    - docs/reference/*.md - Documentation markdown files
    - docs/*.md - Root docs folder
    - PTA/tek_pta.py - Main Tek PTA application
    - PTA/tek_pta_plugin_api.py - Plugin API classes
    - PTA/test_suites/*.py - Test suite plugin examples
    """
    results = []
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    # Check for plugin/PTA-related queries to boost relevance
    is_plugin_query = any(term in query_lower for term in PTA_PLUGIN_QUERY_TERMS)
    
    # Search locations: (path, pattern, file_type, priority_boost)
    search_specs = [
        # Markdown documentation
        (DOCS_REFERENCE_PATH, "**/*.md", "markdown", 0),
        (DOCS_PATH, "*.md", "markdown", 0),
        (INSTALL_BASE, "*.md", "markdown", 0),
        # PTA folder - markdown guides AND Python source
        (PTA_PATH, "*.md", "markdown", 3 if is_plugin_query else 0),  # Plugin guides here
        # Lessons learned from previous test development sessions
        (PTA_LESSONS_PATH, "*.md", "markdown", 2),  # Slight boost for lessons learned
        # Tek PTA Python source files
        (PTA_PATH, "tek_pta.py", "python", 3 if is_plugin_query else 0),
        (PTA_PATH, "tek_pta_plugin_api.py", "python", 5 if is_plugin_query else 0),
        (PTA_SUITES_PATH, "*.py", "python", 4 if is_plugin_query else 0),
    ]
    
    seen_files = set()
    
    for search_path, pattern, file_type, priority_boost in search_specs:
        if not search_path.exists():
            continue
        
        # Handle specific file vs glob pattern
        if "*" in pattern:
            files = list(search_path.glob(pattern))
        else:
            specific_file = search_path / pattern
            files = [specific_file] if specific_file.exists() else []
        
        for source_file in files:
            # Skip duplicates, private files, and very large files
            if source_file.name in seen_files:
                continue
            if source_file.name.startswith("_") and source_file.name != "__init__.py":
                continue
            if source_file.stat().st_size > 2_000_000:  # Skip files > 2MB
                continue
            
            seen_files.add(source_file.name)
            
            try:
                content = source_file.read_text(encoding='utf-8', errors='ignore')
                content_lower = content.lower()
                
                # Calculate relevance score
                score = priority_boost
                matched_sections = []
                
                # Check for exact phrase match
                if query_lower in content_lower:
                    score += 10
                
                # Check for word matches
                for word in query_words:
                    if len(word) > 2:
                        count = content_lower.count(word)
                        if count > 0:
                            score += min(count, 5) * 2  # Cap at 10 per word
                
                # Boost for filename match
                if any(word in source_file.name.lower() for word in query_words if len(word) > 2):
                    score += 5
                
                if score <= priority_boost:  # Only priority boost, no content match
                    continue
                
                # Find relevant sections (lines with context)
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if any(word in line_lower for word in query_words if len(word) > 2):
                        # Get context (3 lines before and after for Python, 2 for markdown)
                        context_lines = 3 if file_type == "python" else 2
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        section = '\n'.join(lines[start:end])
                        if section not in matched_sections:
                            matched_sections.append(section)
                            if len(matched_sections) >= 3:  # Max 3 sections per file
                                break
                
                if matched_sections:
                    results.append({
                        "file": source_file.name,
                        "path": str(source_file),
                        "score": score,
                        "sections": matched_sections[:3],
                        "file_type": file_type,
                    })
                    
            except Exception:
                continue
    
    # Sort by score and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


@mcp.tool()
@with_flush
def tek_search_local_docs(query: str, max_results: int = 5) -> str:
    """Search local markdown documentation AND Python source files for procedures, best practices, and examples.
    
    Use this for questions about:
    - Test automation workflows and patterns
    - Best practices and lessons learned
    - Code examples and templates
    - Troubleshooting and gotchas
    - Scope setup sequences
    - SMU programming tips
    - Tek PTA plugin development
    - Test suite implementation patterns
    
    Searches these locations:
    - docs/reference/*.md - Documentation files
    - PTA/tek_pta.py - Main Tek PTA application (~3,700 lines)
    - PTA/tek_pta_plugin_api.py - TestPoint, TestStatus, TestEngineBase classes
    - PTA/test_suites/*.py - Example test suite plugins
    
    This searches the bundled documentation without requiring internet or vector store.
    
    Args:
        query: Search terms (e.g., "measurement setup", "TEST_SUITE_INFO", "run_test", "plugin")
        max_results: Maximum number of file matches to return (default 5)
    """
    results = search_local_docs(query, max_results)
    
    # Check if this is a plugin-related query (uses shared constant)
    query_lower = query.lower()
    is_plugin_query = any(term in query_lower for term in PTA_PLUGIN_QUERY_TERMS)
    
    if not results:
        return f"No documentation found matching '{query}'. Try different keywords like 'setup', 'measurement', 'trigger', 'SMU', 'jitter', 'plugin', 'test_suite', etc."
    
    output = ""
    
    # Add warning for plugin development queries
    if is_plugin_query:
        output += """⚠️ **TEST AUTOMATION REQUEST DETECTED**

**IMPORTANT: Ask the user which approach they want BEFORE writing code!**

Two options:
1. **Simple Python script** - Runs from terminal, quick to write
   → Use `tek_get_test_template("basic")` or similar
   
2. **Tek PTA GUI plugin** - Full GUI with limits, reports, operator interface
   → Use `tek_pta_plugin_template()` FIRST (plugins silently fail without correct structure!)

**Ask the user:**
> "Would you prefer a simple Python script that runs from the terminal, or a full Tek PTA GUI plugin with pass/fail limits and PDF reports?"

---

"""
    
    output += f"## Local Documentation Search: '{query}'\n\n"
    output += f"Found {len(results)} relevant document(s):\n\n"
    
    for result in results:
        # Use different icons for Python vs Markdown
        file_type = result.get('file_type', 'markdown')
        icon = "🐍" if file_type == "python" else "📄"
        type_label = "Python" if file_type == "python" else "Markdown"
        
        output += f"### {icon} {result['file']}\n"
        output += f"*Relevance score: {result['score']} | Type: {type_label}*\n\n"
        
        for i, section in enumerate(result['sections'], 1):
            # Truncate very long sections
            if len(section) > 500:
                section = section[:500] + "..."
            output += f"**Match {i}:**\n```\n{section}\n```\n\n"
        
        output += "---\n\n"
    
    output += "*Use specific SCPI commands with tek_search_commands or tek_get_command for syntax details.*"
    
    return output


@mcp.tool()
@with_flush
def tek_test_workflow() -> str:
    """Get guidance on which test automation approach to recommend.
    
    Call this when a user asks to create a test, measurement script, or automation.
    Returns guidance on what questions to ask the user to determine the best approach.
    """
    return """## Test Automation Workflow Guide

**ALWAYS ask the user which approach they want before writing code!**

### Question to Ask:
> "I can help you create this test. Which approach would you prefer?
>
> 1. **Simple Python script** - Runs from terminal, quick to write, good for one-off measurements or integration into existing systems
>
> 2. **Tek PTA GUI plugin** - Full GUI application with pass/fail limits, PDF reports, operator-friendly interface, and test logging
>
> Which would work better for your needs?"

---

### Decision Matrix

| User Need | Recommendation |
|-----------|----------------|
| Quick measurement | Simple script |
| Learning SCPI | Simple script |
| One-off test | Simple script |
| Integrate into CI/CD | Simple script |
| Production testing | Tek PTA plugin |
| Multiple test points with limits | Tek PTA plugin |
| PDF reports needed | Tek PTA plugin |
| Operator will run tests | Tek PTA plugin |
| Need pass/fail tracking | Tek PTA plugin |

---

### If User Wants Simple Script:
```
tek_get_test_template("basic")        # Frequency measurement
tek_get_test_template("power_supply") # DC + ripple
tek_get_test_template("signal_integrity") # Jitter
tek_get_test_template("waveform_capture") # Save to CSV
```

### If User Wants Tek PTA Plugin:
```
tek_pta_plugin_template()   # MUST call first - get exact structure
tek_pta_plugin_checklist()  # Review requirements
```

⚠️ **CRITICAL**: If user wants Tek PTA plugin, you MUST call `tek_pta_plugin_template()` 
and copy that structure EXACTLY. Plugins silently fail without correct structure!
"""


# =============================================================================
# TEK PTA PLUGIN DEVELOPMENT TOOLS
# =============================================================================

@mcp.tool()
@with_flush
def tek_pta_plugin_template() -> str:
    """Get the COMPLETE Tek PTA plugin template with correct structure.
    
    ⚠️ BEFORE CALLING THIS: Ask the user if they want a Tek PTA GUI plugin
    or a simple Python script! Many users just need a terminal script.
    
    Use this tool ONLY when the user confirms they want a Tek PTA GUI plugin.
    For simple terminal scripts, use tek_get_test_template() instead.
    
    This returns the exact template that includes:
    - Correct TestStatus enum values
    - Correct TestPoint dataclass with exact field order
    - Correct TestSuitePlugin dataclass (engine_class MUST be last!)
    - Correct TestEngineBase with instrument_manager parameter
    - REQUIRED register_suites() function
    
    Without using this template, plugins will SILENTLY FAIL to load.
    """
    template = '''#!/usr/bin/env python3
"""
My Custom Test Suite for Tek PTA
================================

[Description of what this test does]

Author: [Your name]
Date: [Date]
"""

import time
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


# =============================================================================
# PLUGIN API DEFINITIONS (copy these EXACTLY for portability)
# =============================================================================

class TestStatus(Enum):
    """Status of a test point - MUST match exactly!"""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "Skipped"


@dataclass
class TestPoint:
    """Represents a single test measurement point - field order matters!"""
    test_id: int
    name: str
    nominal_value: float
    unit: str
    tolerance_pct: float = 0.0
    has_limits: bool = True
    enabled: bool = True
    status: TestStatus = TestStatus.NOT_RUN
    measured_value: float = 0.0
    error_pct: float = 0.0
    lower_limit: float = 0.0
    upper_limit: float = 0.0
    screenshot_path: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class TestSuitePlugin:
    """Definition of a test suite plugin - engine_class MUST be last!"""
    name: str
    description: str
    test_type: str  # Unique identifier, e.g., "my_custom_test"
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Optional[type] = None   # MUST be last field!


class TestEngineBase:
    """Base class for custom test engines"""
    
    def __init__(self, instrument_manager):  # MUST take instrument_manager!
        self.inst = instrument_manager
        self.test_points: List[TestPoint] = []
        self.running = False
        self.output_dir = None
        self.reference_config = None
        
        # Callbacks - set by main app
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[float, str], None]] = None
        self.on_test_start: Optional[Callable[[TestPoint], None]] = None
        self.on_test_complete: Optional[Callable[[TestPoint], None]] = None
        self.on_screenshot: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[int, int], None]] = None
    
    def log(self, message: str):
        if self.on_log:
            self.on_log(message)
    
    def progress(self, percentage: float, message: str):
        if self.on_progress:
            self.on_progress(percentage, message)
    
    # Override these methods:
    def generate_test_points(self, config: Dict[str, Any]) -> List[TestPoint]:
        """Called when test suite is SELECTED (not when Run clicked)"""
        raise NotImplementedError
    
    def setup_instruments(self, config: Dict[str, Any]) -> bool:
        """Configure instruments before test run"""
        raise NotImplementedError
    
    def run_single_test(self, test_point: TestPoint, config: Dict[str, Any]) -> TestPoint:
        """Execute a single test point measurement"""
        raise NotImplementedError
    
    def run(self, config: Dict[str, Any]):
        """Main test execution loop"""
        raise NotImplementedError
    
    def cleanup(self):
        """Cleanup after test run"""
        pass
    
    def stop(self):
        """Signal the test to stop"""
        self.running = False


# =============================================================================
# YOUR CUSTOM ENGINE
# =============================================================================

class MyCustomEngine(TestEngineBase):
    def __init__(self, instrument_manager):
        super().__init__(instrument_manager)
    
    def generate_test_points(self, config: Dict[str, Any]) -> List[TestPoint]:
        """Generate test points - called when suite is SELECTED in UI"""
        self.test_points = []
        
        # Example: Create test points from config or hardcoded specs
        self.test_points.append(TestPoint(
            test_id=1,
            name="My Measurement",
            nominal_value=100.0,
            unit="mV",
            tolerance_pct=5.0,
            lower_limit=95.0,
            upper_limit=105.0,
        ))
        
        return self.test_points
    
    def setup_instruments(self, config: Dict[str, Any]) -> bool:
        """Configure scope/instruments before test run"""
        try:
            # Example scope commands:
            # self.inst.scope.write("*RST")
            # self.inst.scope.write("CH1:SCAle 100E-3")
            self.log("Instruments configured")
            return True
        except Exception as e:
            self.log(f"Setup failed: {e}")
            return False
    
    def run_single_test(self, test_point: TestPoint, config: Dict[str, Any]) -> TestPoint:
        """Execute one test point measurement"""
        try:
            # Example: Read measurement from scope
            # response = self.inst.scope.query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
            # test_point.measured_value = float(response)
            
            test_point.measured_value = 99.5  # Placeholder
            
            # Determine pass/fail
            if test_point.lower_limit <= test_point.measured_value <= test_point.upper_limit:
                test_point.status = TestStatus.PASS
            else:
                test_point.status = TestStatus.FAIL
                
        except Exception as e:
            test_point.status = TestStatus.ERROR
            test_point.extra_data['error'] = str(e)
        
        return test_point
    
    def run(self, config: Dict[str, Any]):
        """Main test execution loop"""
        self.running = True
        
        if not self.test_points:
            self.generate_test_points(config)
        
        if not self.setup_instruments(config):
            if self.on_complete:
                self.on_complete(0, len(self.test_points))
            return
        
        pass_count = 0
        fail_count = 0
        
        for i, tp in enumerate(self.test_points):
            if not self.running:
                break
            
            if not tp.enabled:
                tp.status = TestStatus.SKIPPED
                continue
            
            tp.status = TestStatus.RUNNING
            if self.on_test_start:
                self.on_test_start(tp)
            
            self.progress((i / len(self.test_points)) * 100, f"Testing: {tp.name}")
            
            tp = self.run_single_test(tp, config)
            
            if tp.status == TestStatus.PASS:
                pass_count += 1
            else:
                fail_count += 1
            
            if self.on_test_complete:
                self.on_test_complete(tp)
        
        self.cleanup()
        self.progress(100, "Complete")
        
        if self.on_complete:
            self.on_complete(pass_count, fail_count)


# =============================================================================
# PLUGIN REGISTRATION (REQUIRED!)
# =============================================================================

def register_suites():
    """
    Register test suites with Tek PTA.
    
    This function is REQUIRED for Tek PTA to discover and load the plugin!
    Must return a list of TestSuitePlugin objects.
    """
    return [
        TestSuitePlugin(
            name="My Custom Test",
            description="Description of what this test does",
            test_type="my_custom_test",  # Unique identifier
            config={
                # Default configuration values
                'param1': 100,
                'param2': 'value',
            },
            required_instruments=["Oscilloscope"],
            engine_class=MyCustomEngine,  # MUST be last field!
        ),
    ]


# =============================================================================
# STANDALONE TEST (optional but recommended)
# =============================================================================

if __name__ == "__main__":
    # Verify plugin loads correctly
    suites = register_suites()
    print(f"Registered {len(suites)} suite(s)")
    for suite in suites:
        print(f"  - {suite.name} (type: {suite.test_type})")
    
    # Test engine in simulation
    engine = MyCustomEngine(instrument_manager=None)
    engine.on_log = print
    test_points = engine.generate_test_points({})
    print(f"Generated {len(test_points)} test points")
'''
    
    return f"""## Tek PTA Plugin Template

⚠️ **CRITICAL**: Copy this template EXACTLY. Field order and structure matter!

Plugins that don't follow this structure will **silently fail to load**.

### Key Requirements:
1. `TestStatus` enum must have exactly these values
2. `TestPoint` field order must be exact  
3. `TestSuitePlugin.engine_class` must be the LAST field
4. `TestEngineBase.__init__` must take `instrument_manager` parameter
5. `register_suites()` function is REQUIRED

```python
{template}
```

### After Creating Your Plugin:
1. Save to `PTA/test_suites/your_test_name.py`
2. Run standalone: `python your_test_name.py` to verify it loads
3. Launch Tek PTA and select your test suite
"""


@mcp.tool()
@with_flush  
def tek_pta_plugin_checklist() -> str:
    """Get the Tek PTA plugin development checklist.
    
    Use this checklist when creating or reviewing any Tek PTA test suite plugin.
    Ensures all required elements are included and correctly structured.
    """
    return """## Tek PTA Plugin Development Checklist

### ✅ Before Writing Code

- [ ] **Define measurements**: What values are you measuring? (delay, rise time, frequency, amplitude, etc.)
- [ ] **Determine nominals and tolerances**: What's the expected value and acceptable range?
- [ ] **Identify instruments needed**: Oscilloscope only? AWG? SMU?
- [ ] **Plan scope configuration**: Channels, coupling, termination, bandwidth
- [ ] **Choose measurement approach**: Single acquisition or statistics-based?

### ✅ Plugin Structure (CRITICAL!)

- [ ] **Call `tek_pta_plugin_template()` first** to get correct structure
- [ ] Copy Plugin API definitions EXACTLY (TestStatus, TestPoint, TestSuitePlugin, TestEngineBase)
- [ ] `TestSuitePlugin.engine_class` is the LAST field
- [ ] `TestEngineBase.__init__` takes `instrument_manager` parameter
- [ ] `register_suites()` function exists and returns list of `TestSuitePlugin`
- [ ] Set unique `test_type` string (e.g., "my_custom_test")

### ✅ Engine Implementation

- [ ] `generate_test_points(config)`: Creates TestPoint list with test_id, name, nominal_value, unit, limits
- [ ] `setup_instruments(config)`: Configures scope channels, trigger, timebase
- [ ] `run_single_test(test_point, config)`: Reads measurement, sets status to PASS/FAIL/ERROR
- [ ] `run(config)`: Main test loop
- [ ] `cleanup()`: Disables outputs, cleans up

### ✅ Measurement Setup

- [ ] For reference waveforms: Skip ALL acquisition commands (no trigger, no ACQ:STATE RUN)
- [ ] For live channels: Configure trigger, run acquisition, wait for completion
- [ ] Check for invalid measurements (9.91E+37)
- [ ] Use correct measurement type names (HEIGHT not EYEHEIGHT, WIDTH not EYEWIDTH)

### ✅ Status and Results

- [ ] Set `tp.status` to appropriate `TestStatus` value
- [ ] Calculate `tp.error_pct` for percentage error
- [ ] Store extra data in `tp.extra_data` dict
- [ ] Print results table with proper columns

### ✅ Testing

- [ ] Run standalone: `python my_test_suite.py` to verify `register_suites()` works
- [ ] Verify SCPI commands in programmer manual
- [ ] Test with disconnected DUT to verify error handling

### 🚫 Common Mistakes That Cause Silent Failures

| Mistake | Correct | Wrong |
|---------|---------|-------|
| `engine_class` position | Last field | Any other position |
| `TestEngineBase.__init__` | Takes `instrument_manager` | Takes nothing or `self` only |
| `TestPoint.measured_value` | `float = 0.0` | `Optional[float] = None` |
| Plugin registration | `def register_suites()` | Any other function name |
| TestStatus values | Exact enum values | Different values |
"""


@mcp.tool()
@with_flush
def tek_vector_search(query: str) -> str:
    """Search the Tektronix documentation vector store for detailed procedures.
    
    Use for complex questions that need more context than SCPI syntax.
    Requires OPENAI_API_KEY and TEK_VECTOR_STORE_ID environment variables.
    """
    if not OPENAI_AVAILABLE:
        return "OpenAI package not installed. Install with: pip install openai"
    
    if not OPENAI_API_KEY or not VECTOR_STORE_ID:
        return "Vector store not configured. Set OPENAI_API_KEY and TEK_VECTOR_STORE_ID environment variables."
    
    result = query_vector_store(query)
    
    if result:
        # Validate any SCPI commands found
        validation = validate_scpi_commands(result)
        
        output = f"## Vector Store Result\n\n{result}\n\n"
        
        if validation["validated"]:
            output += "### ✓ Verified Commands\n"
            for v in validation["validated"]:
                output += f"- `{v['command']}` ({v['instrument']})\n"
        
        if validation["not_found"]:
            output += "\n### ⚠ Unverified Commands (check syntax)\n"
            for cmd in validation["not_found"]:
                output += f"- `{cmd}`\n"
        
        return output
    
    return "No results found. Try rephrasing or use tek_search_commands for direct SCPI lookup."


@mcp.tool()
@with_flush
def tek_comprehensive_search(query: str, mode: str = "auto") -> str:
    """Comprehensive search that queries both JSON database AND vector store.
    
    Best for procedural questions like "How do I measure jitter?"
    
    Modes:
    - fast: JSON database only (50-100ms)
    - comprehensive: Vector store + validation (1-3s)
    - auto: Let system decide based on query
    """
    output = f"## Comprehensive Search: '{query}'\n\n"
    
    # Always search JSON database (fast)
    json_results = search_commands(query, limit=5)
    
    if json_results:
        output += "### SCPI Commands Found\n"
        for cmd in json_results[:3]:
            scpi = cmd.get("scpi", cmd.get("name", "N/A"))
            desc = cmd.get("description", "")[:100]
            output += f"- `{scpi}` - {desc}\n"
        output += "\n"
    
    # Search local docs
    local_results = search_local_docs(query, max_results=2)
    if local_results:
        output += "### Local Documentation\n"
        for result in local_results:
            output += f"- 📄 {result['file']}\n"
        output += "\n"
    
    # Decide on vector search
    use_vector = (
        mode == "comprehensive" or 
        (mode == "auto" and len(json_results) < 3 and OPENAI_API_KEY and VECTOR_STORE_ID)
    )
    
    if use_vector:
        output += "### Vector Store Search\n"
        vector_result = query_vector_store(query)
        if vector_result:
            # Truncate if too long
            if len(vector_result) > 1000:
                vector_result = vector_result[:1000] + "...\n[truncated]"
            output += vector_result + "\n"
        else:
            output += "No additional results from vector store.\n"
    
    if not json_results and not local_results:
        output += "No results found. Try different keywords or check tek_list_instruments for available databases."
    
    return output


@mcp.tool()
@with_flush
def tek_get_test_template(template_type: str) -> str:
    """Get a Python test automation template.
    
    Available templates:
    - power_supply: DC voltage/ripple measurement
    - signal_integrity: Jitter measurement with DJA
    - basic: Simple frequency measurement
    - waveform_capture: Capture and save waveform data
    """
    templates = {
        "power_supply": _get_power_supply_template,
        "signal_integrity": _get_jitter_template,
        "basic": _get_basic_template,
        "waveform_capture": _get_waveform_template,
        "pta": _get_pta_template,
    }
    
    if template_type.lower() not in templates:
        return f"Unknown template '{template_type}'. Available: {', '.join(templates.keys())}"
    
    template = templates[template_type.lower()]()
    return f"## {template_type.title()} Test Template\n\n```python\n{template}\n```"


# =============================================================================
# LESSONS LEARNED STORAGE
# =============================================================================

@mcp.tool()
@with_flush
def tek_save_lessons_learned(
    test_name: str,
    summary: str,
    instruments: str,
    key_scpi_commands: str,
    gotchas: str,
    solutions: str,
    measurement_tips: str = "",
    additional_notes: str = ""
) -> str:
    """Save lessons learned from a Tek PTA test development session.
    
    Call this after completing a test development session to capture knowledge
    for future reference. The file will be saved to PTA/lessons_learned/ and
    automatically found by tek_search_local_docs in future sessions.
    
    Args:
        test_name: Name of the test (e.g., "AWG70002B Pulse Timing Test")
        summary: Brief description of what the test does and its purpose
        instruments: Instruments used (e.g., "MSO58B oscilloscope, AWG70002B")
        key_scpi_commands: Important SCPI commands discovered or used
        gotchas: Problems encountered during development
        solutions: How the problems were solved
        measurement_tips: Tips for accurate measurements (optional)
        additional_notes: Any other relevant information (optional)
    
    Returns:
        Confirmation message with file path
    """
    # Ensure lessons_learned directory exists
    PTA_LESSONS_PATH.mkdir(parents=True, exist_ok=True)
    
    # Generate filename from date and test name
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r'[^\w\s-]', '', test_name).strip().replace(' ', '_').lower()
    filename = f"{date_str}_{safe_name}.md"
    filepath = PTA_LESSONS_PATH / filename
    
    # Handle duplicate filenames
    counter = 1
    while filepath.exists():
        filename = f"{date_str}_{safe_name}_{counter}.md"
        filepath = PTA_LESSONS_PATH / filename
        counter += 1
    
    # Build markdown content
    content = f"""# Lessons Learned: {test_name}

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}  
**Test Name:** {test_name}

## Summary
{summary}

## Instruments Used
{instruments}

## Key SCPI Commands
{key_scpi_commands}

## Gotchas / Problems Encountered
{gotchas}

## Solutions
{solutions}
"""
    
    if measurement_tips:
        content += f"""
## Measurement Tips
{measurement_tips}
"""
    
    if additional_notes:
        content += f"""
## Additional Notes
{additional_notes}
"""
    
    content += f"""
---
*Generated by Tek MCP Server v1.0.2*
"""
    
    try:
        filepath.write_text(content, encoding='utf-8')
        return f"""✓ Lessons learned saved successfully!

**File:** `{filepath}`

This knowledge will be automatically available in future sessions via `tek_search_local_docs`.

To find this later, search for keywords like:
- "{test_name}"
- Instrument names
- SCPI commands mentioned
"""
    except Exception as e:
        return f"ERROR: Failed to save lessons learned: {e}"


@mcp.tool()
@with_flush
def tek_list_lessons_learned() -> str:
    """List all saved lessons learned files.
    
    Shows all lessons learned documents from previous test development sessions.
    Use tek_search_local_docs to search within these files.
    """
    if not PTA_LESSONS_PATH.exists():
        return "No lessons learned directory found. Complete a test development session and save lessons to create it."
    
    files = sorted(PTA_LESSONS_PATH.glob("*.md"), reverse=True)
    
    if not files:
        return "No lessons learned files found yet. Complete a test development session and save lessons learned."
    
    output = f"## Lessons Learned Library\n\n"
    output += f"**Location:** `{PTA_LESSONS_PATH}`\n"
    output += f"**Total Files:** {len(files)}\n\n"
    
    for f in files[:20]:  # Show most recent 20
        # Extract title from first line
        try:
            first_line = f.read_text(encoding='utf-8').split('\n')[0]
            title = first_line.replace('# Lessons Learned: ', '').strip()
        except:
            title = f.stem
        
        size = f.stat().st_size
        output += f"- **{f.name}** ({size:,} bytes)\n  {title}\n"
    
    if len(files) > 20:
        output += f"\n... and {len(files) - 20} more files\n"
    
    output += "\n*Use `tek_search_local_docs` to search within these files.*"
    
    return output


# =============================================================================
# LEGACY COMMAND MIGRATION LOOKUP
# =============================================================================

_legacy_mappings: Optional[Dict] = None

def load_legacy_mappings() -> Dict:
    """Load legacy command mappings from JSON file."""
    global _legacy_mappings
    
    if _legacy_mappings is not None:
        return _legacy_mappings
    
    if LEGACY_MAPPINGS_PATH.exists():
        try:
            with open(LEGACY_MAPPINGS_PATH, 'r', encoding='utf-8') as f:
                _legacy_mappings = json.load(f)
                return _legacy_mappings
        except Exception as e:
            print(f"[Warning] Could not load legacy mappings: {e}", file=sys.stderr)
    
    _legacy_mappings = {"mappings": []}
    return _legacy_mappings


def search_legacy_mappings(query: str) -> List[Dict]:
    """Search legacy command mappings for a command or keyword."""
    data = load_legacy_mappings()
    mappings = data.get("mappings", [])
    
    query_lower = query.lower().strip().lstrip(":")
    query_words = set(query_lower.replace(":", " ").split())
    
    results = []
    for mapping in mappings:
        legacy = mapping.get("legacy", "").lower().lstrip(":")
        modern = mapping.get("modern", "").lower().lstrip(":")
        category = mapping.get("category", "").lower()
        notes = mapping.get("notes", "").lower()
        
        score = 0
        
        # Exact legacy command match (highest priority)
        if query_lower == legacy or query_lower == legacy.replace("<n>", "1"):
            score = 100
        # Query is substring of legacy command
        elif query_lower in legacy:
            score = 50
        # Legacy command contains query
        elif any(word in legacy for word in query_words if len(word) > 2):
            score = 30
        # Search in modern command
        elif query_lower in modern:
            score = 20
        # Search in category or notes
        elif any(word in category or word in notes for word in query_words if len(word) > 2):
            score = 10
        
        if score > 0:
            results.append({
                **mapping,
                "_score": score
            })
    
    # Sort by score
    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:10]


@mcp.tool()
@with_flush
def tek_legacy_command_lookup(command: str) -> str:
    """Look up modern equivalent of a legacy SCPI command.
    
    Use this when migrating code from older oscilloscopes:
    - MSO/DPO 5000/7000/70000 Series
    - DSA 70000 Series
    - Earlier MSO 4/5/6 Series firmware
    
    Args:
        command: Legacy SCPI command to look up (e.g., ':MATH:MATH1:POSITION', 'cursor', 'dpojet')
    
    Returns:
        Modern command equivalent with migration notes
    """
    results = search_legacy_mappings(command)
    
    if not results:
        return f"""## Legacy Command Lookup: `{command}`

**No direct mapping found.**

This could mean:
1. The command is already modern syntax
2. The command doesn't exist in the legacy mapping database
3. The command may work as-is (DPO 7 Series has built-in backwards compatibility)

**Suggestions:**
- Try `tek_search_commands` to find the modern command
- Check the DPO 7 Series Programmer Manual
- The scope may automatically translate the command"""

    output = f"## Legacy Command Lookup: `{command}`\n\n"
    output += f"Found {len(results)} mapping(s):\n\n"
    
    for i, result in enumerate(results, 1):
        legacy = result.get("legacy", "N/A")
        modern = result.get("modern", "N/A")
        category = result.get("category", "General")
        notes = result.get("notes", "")
        
        output += f"### {i}. {category}\n"
        output += f"| | |\n|---|---|\n"
        output += f"| **Legacy** | `{legacy}` |\n"
        output += f"| **Modern** | `{modern}` |\n"
        if notes:
            output += f"| **Notes** | {notes} |\n"
        output += "\n"
    
    output += """---
**Migration Tips:**
- The DPO 7 Series has built-in backwards compatibility - legacy commands may work automatically
- Use `tek_search_commands` to explore the modern command's full syntax and options
- See the Migration Guide in docs/reference/legacy_to_modern_scpi_migration.md
"""
    
    return output


# =============================================================================
# LIVE INSTRUMENT CONTROL TOOLS
# =============================================================================

def _get_visa_rm():
    """Get or create singleton PyVISA ResourceManager."""
    global _visa_rm
    if _visa_rm is None:
        if not PYVISA_AVAILABLE:
            return None
        _visa_rm = pyvisa.ResourceManager()
    return _visa_rm


def _ensure_connected() -> bool:
    """Check if we have an active instrument connection."""
    return _visa_session is not None


@mcp.tool()
@with_flush
def tek_instrument_discover() -> str:
    """Discover available VISA instruments on the network.
    
    Lists all instruments found by the VISA resource manager.
    Use one of the returned resource strings with tek_instrument_connect().
    """
    if not PYVISA_AVAILABLE:
        return "ERROR: PyVISA not installed. Install with: pip install pyvisa pyvisa-py"
    
    rm = _get_visa_rm()
    if not rm:
        return "ERROR: Could not initialize VISA resource manager."
    
    try:
        resources = rm.list_resources()
        if not resources:
            return """## No VISA Instruments Found

Possible reasons:
- No instruments connected or powered on
- Instruments not on the same network/subnet
- VISA driver not installed (try TekVISA or NI-VISA)
- Firewall blocking port 4000 (LAN instruments)

**Tips:**
- For LAN: Ensure scope and PC are on same subnet
- For USB: Check USB cable and drivers
- Try specifying directly: `tek_instrument_connect("TCPIP::192.168.1.100::INSTR")`
"""
        
        output = f"## Discovered {len(resources)} VISA Instrument(s)\n\n"
        for i, res in enumerate(resources, 1):
            output += f"{i}. `{res}`\n"
        
        output += "\nUse `tek_instrument_connect` with one of these resource strings."
        return output
        
    except Exception as e:
        return f"ERROR discovering instruments: {e}"


@mcp.tool()
@with_flush
def tek_instrument_connect(resource_string: str, timeout_ms: int = 30000) -> str:
    """Connect to a Tektronix instrument via VISA.
    
    Opens a persistent session that stays open across tool calls.
    Automatically queries *IDN? to identify the instrument.
    
    Args:
        resource_string: VISA resource (e.g., "TCPIP::192.168.1.100::INSTR", "USB::...::INSTR")
        timeout_ms: Communication timeout in milliseconds (default: 30000)
    """
    global _visa_session, _visa_resource_string, _visa_idn
    
    if not PYVISA_AVAILABLE:
        return "ERROR: PyVISA not installed. Install with: pip install pyvisa pyvisa-py"
    
    # Close existing session if open
    if _visa_session is not None:
        try:
            _visa_session.close()
        except:
            pass
        _visa_session = None
        _visa_resource_string = ""
        _visa_idn = ""
    
    rm = _get_visa_rm()
    if not rm:
        return "ERROR: Could not initialize VISA resource manager."
    
    try:
        with _visa_lock:
            session = rm.open_resource(resource_string)
            session.timeout = timeout_ms
            
            # Configure for clean communication
            session.write("*CLS")
            session.write("HEADer OFF")
            session.write("VERBose OFF")
            
            # Identify the instrument
            idn = session.query("*IDN?").strip()
            
            _visa_session = session
            _visa_resource_string = resource_string
            _visa_idn = idn
        
        # Parse IDN for friendly output
        parts = idn.split(",")
        manufacturer = parts[0].strip() if len(parts) > 0 else "Unknown"
        model = parts[1].strip() if len(parts) > 1 else "Unknown"
        serial = parts[2].strip() if len(parts) > 2 else "N/A"
        firmware = parts[3].strip() if len(parts) > 3 else "N/A"
        
        return f"""## ✅ Connected to Instrument

**Model:** {manufacturer} {model}
**Serial:** {serial}
**Firmware:** {firmware}
**Resource:** `{resource_string}`
**Timeout:** {timeout_ms}ms

Session is persistent — all subsequent commands will use this connection.
Use `tek_instrument_query` and `tek_instrument_write` to communicate.
"""
        
    except Exception as e:
        _visa_session = None
        _visa_resource_string = ""
        _visa_idn = ""
        return f"""## ❌ Connection Failed

**Resource:** `{resource_string}`
**Error:** {e}

**Troubleshooting:**
- Verify the IP address/resource string
- Check that the instrument is powered on and connected
- Try `tek_instrument_discover()` to find available instruments
- Ensure no other application has an exclusive lock on the instrument
"""


@mcp.tool()
@with_flush
def tek_instrument_disconnect() -> str:
    """Disconnect from the current instrument and close the VISA session."""
    global _visa_session, _visa_resource_string, _visa_idn, _saved_instrument_state
    
    if _visa_session is None:
        return "No instrument connected."
    
    resource = _visa_resource_string
    try:
        with _visa_lock:
            _visa_session.close()
    except:
        pass
    finally:
        _visa_session = None
        _visa_resource_string = ""
        _visa_idn = ""
        _saved_instrument_state = None
    
    return f"✅ Disconnected from `{resource}`."


@mcp.tool()
@with_flush
def tek_instrument_write(command: str) -> str:
    """Send a SCPI command (set) to the connected instrument.
    
    Use for commands that configure the instrument (no return value).
    For commands that return data, use tek_instrument_query instead.
    
    Args:
        command: SCPI command to send (e.g., "CH1:SCAle 500E-3", "ACQ:STATE RUN")
    """
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    try:
        with _visa_lock:
            _visa_session.write(command)
        return f"✓ Sent: `{command}`"
    except Exception as e:
        return f"ERROR sending `{command}`: {e}"


@mcp.tool()
@with_flush
def tek_instrument_query(command: str) -> str:
    """Send a SCPI query to the connected instrument and return the response.
    
    Use for commands that return data (ending with '?').
    
    Args:
        command: SCPI query to send (e.g., "CH1:SCAle?", "*IDN?", "MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
    """
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    try:
        with _visa_lock:
            response = _visa_session.query(command).strip()
        return f"**Query:** `{command}`\n**Response:** `{response}`"
    except Exception as e:
        return f"ERROR querying `{command}`: {e}"


@mcp.tool()
@with_flush
def tek_instrument_write_batch(commands: str) -> str:
    """Send multiple SCPI commands to the connected instrument as a batch.
    
    Commands should be separated by newlines or semicolons.
    Waits for *OPC? after each command for synchronization.
    
    Args:
        commands: Multiple SCPI commands, one per line or semicolon-separated.
                  Example: "CH1:SCAle 500E-3\\nCH1:TERMinator 50\\nCH1:BANdwidth 200E6"
    """
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    # Parse commands from newlines or semicolons
    cmd_list = []
    for line in commands.replace(";", "\n").split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            cmd_list.append(line)
    
    if not cmd_list:
        return "ERROR: No valid commands found in input."
    
    results = []
    errors = []
    
    try:
        with _visa_lock:
            for cmd in cmd_list:
                try:
                    if cmd.endswith("?"):
                        response = _visa_session.query(cmd).strip()
                        results.append(f"✓ `{cmd}` → `{response}`")
                    else:
                        _visa_session.write(cmd)
                        results.append(f"✓ `{cmd}`")
                except Exception as e:
                    errors.append(f"✗ `{cmd}` → {e}")
            
            # Sync at the end
            try:
                _visa_session.query("*OPC?")
            except:
                pass
    except Exception as e:
        return f"ERROR during batch execution: {e}"
    
    output = f"## Batch Execution: {len(cmd_list)} commands\n\n"
    output += f"**Succeeded:** {len(results)} | **Failed:** {len(errors)}\n\n"
    
    for r in results:
        output += f"{r}\n"
    for e in errors:
        output += f"{e}\n"
    
    return output


@mcp.tool()
@with_flush
def tek_instrument_state() -> str:
    """Read back the current state of the connected oscilloscope.
    
    Queries key settings: channels, vertical scale/offset, horizontal,
    trigger, acquisition mode, and active measurements.
    Useful for confirming instrument configuration after changes.
    """
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    def safe_query(cmd: str, default: str = "N/A") -> str:
        try:
            return _visa_session.query(cmd).strip()
        except:
            return default
    
    output = f"## Instrument State\n\n"
    output += f"**Instrument:** {_visa_idn}\n"
    output += f"**Resource:** `{_visa_resource_string}`\n\n"
    
    with _visa_lock:
        # Horizontal settings
        output += "### Timebase\n"
        hor_scale = safe_query("HOR:SCAle?")
        hor_mode = safe_query("HOR:MODe?")
        rec_len = safe_query("HOR:MODE:RECOrdlength?")
        sample_rate = safe_query("HOR:SAMPLERate?")
        output += f"- **Scale:** {hor_scale} s/div\n"
        output += f"- **Mode:** {hor_mode}\n"
        output += f"- **Record Length:** {rec_len} points\n"
        output += f"- **Sample Rate:** {sample_rate} S/s\n\n"
        
        # Channel settings (check which are on)
        output += "### Channels\n"
        for ch in range(1, 9):
            try:
                state = _visa_session.query(f"DISplay:WAVEView1:CH{ch}:STATE?").strip()
                if state == "1":
                    scale = safe_query(f"CH{ch}:SCAle?")
                    offset = safe_query(f"CH{ch}:OFFSet?")
                    coupling = safe_query(f"CH{ch}:COUPling?")
                    term = safe_query(f"CH{ch}:TERMinator?")
                    bw = safe_query(f"CH{ch}:BANdwidth?")
                    clipping = safe_query(f"CH{ch}:CLIPping?")
                    
                    output += f"- **CH{ch}:** ON | {scale} V/div | Offset: {offset}V"
                    output += f" | {coupling} | {'50Ω' if term == '50' else '1MΩ'}"
                    output += f" | BW: {bw}"
                    if clipping == "1":
                        output += " | ⚠️ **CLIPPING!**"
                    output += "\n"
            except:
                break  # No more channels
        
        # Trigger
        output += "\n### Trigger\n"
        trig_type = safe_query("TRIGger:A:TYPe?")
        trig_source = safe_query("TRIGger:A:EDGE:SOURce?")
        trig_level = safe_query("TRIGger:A:LEVel?")
        trig_slope = safe_query("TRIGger:A:EDGE:SLOpe?")
        output += f"- **Type:** {trig_type} | **Source:** {trig_source}\n"
        output += f"- **Level:** {trig_level}V | **Slope:** {trig_slope}\n\n"
        
        # Acquisition
        output += "### Acquisition\n"
        acq_mode = safe_query("ACQ:MODe?")
        acq_state = safe_query("ACQ:STATE?")
        acq_stop = safe_query("ACQ:STOPA?")
        output += f"- **Mode:** {acq_mode} | **State:** {'Running' if acq_state == '1' else 'Stopped'}\n"
        output += f"- **Stop After:** {acq_stop}\n\n"
        
        # Active measurements
        output += "### Measurements\n"
        has_measurements = False
        for m in range(1, 9):
            try:
                mtype = _visa_session.query(f"MEASUrement:MEAS{m}:TYPe?").strip()
                if mtype and mtype != "0" and "UNDEFINED" not in mtype.upper():
                    source = safe_query(f"MEASUrement:MEAS{m}:SOURCE?")
                    value = safe_query(f"MEASUrement:MEAS{m}:RESUlts:CURRentacq:MEAN?")
                    output += f"- **MEAS{m}:** {mtype} on {source} = {value}\n"
                    has_measurements = True
            except:
                break
        
        if not has_measurements:
            output += "- No active measurements\n"
    
    return output


@mcp.tool()
@with_flush
def tek_instrument_save_state() -> str:
    """Save the current instrument state for later restoration (undo).
    
    Captures the full instrument configuration. Use tek_instrument_restore_state()
    to revert to this saved state.
    """
    global _saved_instrument_state
    
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    try:
        with _visa_lock:
            # Use *LRN? to capture full setup if available, otherwise use SET?
            try:
                state = _visa_session.query("*LRN?")
            except:
                try:
                    state = _visa_session.query("SET?")
                except:
                    state = None
        
        if state:
            _saved_instrument_state = state
            return f"✅ Instrument state saved ({len(state):,} bytes). Use `tek_instrument_restore_state()` to revert."
        else:
            return "WARNING: Could not capture instrument state. *LRN? and SET? both failed."
            
    except Exception as e:
        return f"ERROR saving state: {e}"


@mcp.tool()
@with_flush
def tek_instrument_restore_state() -> str:
    """Restore a previously saved instrument state (undo).
    
    Reverts the instrument to the configuration captured by tek_instrument_save_state().
    """
    global _saved_instrument_state
    
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    if not _saved_instrument_state:
        return "ERROR: No saved state to restore. Use tek_instrument_save_state() first."
    
    try:
        with _visa_lock:
            # Send saved state back to instrument
            # *LRN? output is typically a series of SCPI commands separated by semicolons
            commands = _saved_instrument_state.split(";")
            for cmd in commands:
                cmd = cmd.strip()
                if cmd and not cmd.endswith("?"):
                    try:
                        _visa_session.write(cmd)
                    except:
                        pass  # Some commands may not be writable
            _visa_session.query("*OPC?")
        
        return "✅ Instrument state restored to saved configuration."
        
    except Exception as e:
        return f"ERROR restoring state: {e}"


@mcp.tool()
@with_flush
def tek_instrument_screenshot(filename: str = "") -> str:
    """Capture a screenshot from the connected oscilloscope.
    
    Saves the scope display as a PNG file. Useful for remote debugging
    to see exactly what's on screen.
    
    Args:
        filename: Optional filename (default: auto-generated with timestamp)
    """
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scope_screenshot_{timestamp}.png"
    
    # Ensure .png extension
    if not filename.lower().endswith(".png"):
        filename += ".png"
    
    filepath = INSTALL_BASE / filename
    
    try:
        with _visa_lock:
            # Configure screenshot format
            _visa_session.write("SAVe:IMAGe:FILEFormat PNG")
            _visa_session.write("HARDCopy:INKSaver OFF")
            
            # Capture screenshot data
            _visa_session.write("SAVe:IMAGe:COMPosition DEFault")
            
            # Use hardcopy to get image data
            _visa_session.write("HARDCopy START")
            
            # Read binary data
            img_data = _visa_session.read_raw()
        
        # Save to file
        with open(filepath, 'wb') as f:
            f.write(img_data)
        
        size_kb = len(img_data) / 1024
        return f"""## 📸 Screenshot Captured

**File:** `{filepath}`
**Size:** {size_kb:.1f} KB

Screenshot saved from {_visa_idn.split(',')[1].strip() if ',' in _visa_idn else 'instrument'}.
"""
        
    except Exception as e:
        return f"""## Screenshot capture failed

**Error:** {e}

**Alternative approach:** Try these commands manually:
```
tek_instrument_write("SAVe:IMAGe \\"C:/Temp/screenshot.png\\"")
```
Then retrieve the file from the instrument's filesystem.
"""


@mcp.tool()
@with_flush
def tek_instrument_autoset() -> str:
    """Run autoset on the connected oscilloscope.
    
    Automatically configures vertical, horizontal, and trigger settings
    based on the input signal. Waits for completion.
    """
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    try:
        with _visa_lock:
            _visa_session.write("AUTOS EXECUTE")
        
        # Autoset takes a few seconds
        time.sleep(5)
        
        with _visa_lock:
            _visa_session.query("*OPC?")
        
        return "✅ Autoset complete. Use `tek_instrument_state()` to see the resulting configuration."
        
    except Exception as e:
        return f"ERROR during autoset: {e}"


@mcp.tool()
@with_flush
def tek_instrument_run() -> str:
    """Start acquisition (equivalent to pressing RUN button)."""
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    try:
        with _visa_lock:
            _visa_session.write("ACQ:STATE RUN")
        return "✅ Acquisition running."
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
@with_flush
def tek_instrument_stop() -> str:
    """Stop acquisition (equivalent to pressing STOP button)."""
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    try:
        with _visa_lock:
            _visa_session.write("ACQ:STATE STOP")
        return "✅ Acquisition stopped."
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
@with_flush
def tek_instrument_single() -> str:
    """Execute a single acquisition (equivalent to pressing SINGLE button).
    
    Sets stop-after to SEQUENCE, runs, and waits for completion.
    """
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."
    
    try:
        with _visa_lock:
            _visa_session.write("ACQ:STOPA SEQ")
            _visa_session.write("ACQ:STATE RUN")
            _visa_session.query("*WAI;*OPC?")
        return "✅ Single acquisition complete."
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
@with_flush
def tek_status() -> str:
    """Check Tektronix MCP server status - shows in Claude's chat UI."""
    uptime = datetime.now() - _server_start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    output = f"## 🔬 Tektronix MCP Server v1.1.0\n\n"
    output += f"**Status:** ✅ Running\n"
    output += f"**Uptime:** {hours}h {minutes}m {seconds}s\n"
    output += f"**Total Commands:** {_total_commands:,}\n"
    output += f"**Requests Handled:** {_request_count}\n\n"
    
    # Instrument connection status
    output += "### Live Instrument Connection\n"
    if _visa_session is not None:
        output += f"- **Connected:** ✅ `{_visa_resource_string}`\n"
        output += f"- **Instrument:** {_visa_idn}\n"
        if _saved_instrument_state:
            output += f"- **Saved State:** ✅ (undo available)\n"
    else:
        output += f"- **Connected:** ❌ No instrument\n"
        output += f"- **PyVISA:** {'✅ Available' if PYVISA_AVAILABLE else '❌ Not installed'}\n"
    output += "\n"
    
    output += "### Loaded Databases\n"
    for key, cmds in _commands_flat.items():
        if cmds:
            desc = COMMAND_FILES.get(key, {}).get("description", "")
            output += f"- **{key}**: {len(cmds):,} commands ({desc})\n"
    
    output += f"\n**Local Documentation:** {len(list(DOCS_REFERENCE_PATH.glob('**/*.md')) if DOCS_REFERENCE_PATH.exists() else [])} markdown files\n"
    output += f"**Vector Store:** {'✅ Configured' if OPENAI_API_KEY and VECTOR_STORE_ID else '❌ Not configured'}\n"
    
    output += """
### Test Automation Tools
When user asks to create a test, **ask which approach they want first**:
- `tek_test_workflow()` - Guidance on which approach to recommend

**Simple Scripts** (terminal):
- `tek_get_test_template("basic"|"power_supply"|"signal_integrity"|"waveform_capture")`

**Tek PTA GUI Plugins**:
- `tek_pta_plugin_template()` - Get correct plugin structure (**REQUIRED!**)
- `tek_pta_plugin_checklist()` - Development checklist

### Live Instrument Control
- `tek_instrument_discover()` - Find instruments on network
- `tek_instrument_connect(resource)` - Open persistent session
- `tek_instrument_disconnect()` - Close session
- `tek_instrument_write(cmd)` - Send SCPI command
- `tek_instrument_query(cmd)` - Send query, get response
- `tek_instrument_write_batch(cmds)` - Send multiple commands
- `tek_instrument_state()` - Read full instrument state
- `tek_instrument_run/stop/single()` - Acquisition control
- `tek_instrument_autoset()` - Run autoset
- `tek_instrument_screenshot()` - Capture display
- `tek_instrument_save_state()` / `tek_instrument_restore_state()` - Undo support
"""
    
    return output


# =============================================================================
# TEMPLATE GENERATORS
# =============================================================================

def _get_basic_template() -> str:
    return '''"""Basic Frequency Measurement - Verified SCPI"""
import pyvisa
import time

def main():
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource("TCPIP::192.168.1.100::INSTR")
    scope.timeout = 30000
    
    # Always start with these
    scope.write("*CLS")
    scope.write("HEADer OFF")
    scope.write("VERBose OFF")
    
    # Reset and configure
    scope.write("*RST")
    scope.query("*OPC?")
    scope.write("HEADer OFF")  # Reset clears this
    
    # Enable channel
    scope.write("DISplay:WAVEView1:CH1:STATE ON")
    
    # Auto-setup
    scope.write("AUTOS EXECUTE")
    time.sleep(5)
    
    # Add frequency measurement
    scope.write("MEASU:ADDMEAS FREQUENCY")
    scope.write("MEASU:MEAS1:SOURCE CH1")
    scope.write("MEASU:MEAS1:STATE ON")
    scope.query("*OPC?")
    
    # Acquire and measure
    scope.write("ACQ:STOPA SEQ")
    scope.write("ACQ:STATE RUN")
    scope.query("*WAI;*OPC?")
    
    freq = float(scope.query("MEASU:MEAS1:RESUlts:CURRentacq:MEAN?"))
    print(f"Frequency: {freq/1e6:.6f} MHz")
    
    scope.close()

if __name__ == "__main__":
    main()
'''


def _get_power_supply_template() -> str:
    return '''"""Power Supply Test - DC + Ripple from measurement_workflow_Andre.md"""
import pyvisa
import time

def main():
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource("TCPIP::192.168.1.100::INSTR")
    scope.timeout = 30000
    
    scope.write("*CLS")
    scope.write("HEADer OFF")
    scope.write("VERBose OFF")
    scope.write("*RST")
    scope.query("*OPC?")
    scope.write("HEADer OFF")
    
    scope.write("DISplay:WAVEView1:CH1:STATE ON")
    scope.write("CH1:TERMinator 1E6")  # 1M for power rail
    scope.write("CH1:BANdwidth 20E6")
    scope.write("AUTOS EXECUTE")
    time.sleep(5)
    
    # DC coupling for mean, AC for ripple
    scope.write("ACQ:STOPA SEQ")
    scope.write("MEASU:ADDMEAS MEAN")
    scope.write("MEASU:MEAS1:SOURCE CH1")
    scope.write("MEASU:MEAS1:STATE ON")
    scope.write("MEASU:ADDMEAS PK2PK")
    scope.write("MEASU:MEAS2:SOURCE CH1")
    scope.write("MEASU:MEAS2:STATE ON")
    scope.write("MEASU:MEAS1:POPUlation:LIMIT:VALue 1000")
    scope.write("MEASU:MEAS1:POPUlation:LIMIT:STATE ON")
    scope.query("*OPC?")
    
    scope.write("ACQ:STATE RUN"); scope.query("*WAI;*OPC?")
    
    dc = float(scope.query("MEASU:MEAS1:RESUlts:ALLAcqs:MEAN?"))
    ripple = float(scope.query("MEASU:MEAS2:RESUlts:ALLAcqs:MEAN?"))
    
    expected, tol = 5.0, 5.0
    err = abs(dc - expected) / expected * 100
    print(f"DC: {dc:.4f}V, Ripple: {ripple*1000:.2f}mV, Error: {err:.2f}%")
    print(f"Result: {'PASS' if err <= tol else 'FAIL'}")
    scope.close()

if __name__ == "__main__": main()
'''


def _get_jitter_template() -> str:
    return '''"""Jitter Measurement - From measurement_workflow_Andre.md
CRITICAL: 100+ UIs at 100 samples/UI minimum"""
import pyvisa, time

def main():
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource("TCPIP::192.168.1.100::INSTR")
    scope.timeout = 60000
    
    scope.write("*CLS"); scope.write("HEADer OFF"); scope.write("VERBose OFF")
    
    if "DJA" not in scope.query("*OPT?").upper():
        print("WARNING: DJA license may be required")
    
    scope.write("*RST"); scope.query("*OPC?"); scope.write("HEADer OFF")
    scope.write("DISplay:WAVEView1:CH1:STATE ON")
    scope.write("AUTOS EXECUTE"); time.sleep(5)
    
    # Configure for jitter - MUST set MAN mode first!
    data_rate = 1e9  # 1 Gbps
    scope.write("HOR:MODE MAN")
    scope.write(f"HOR:MODE:SAMPLERATE {data_rate * 100}")
    scope.write(f"HOR:MODE:RECORDLENGTH {100 * 100}")
    scope.query("*OPC?")
    
    scope.write("ACQ:STOPA SEQ")
    scope.write("MEASU:DELETEALL")
    scope.write("MEASU:ADDMEAS JITTERSUMMARY")
    scope.write("MEASU:MEAS1:SOURCE CH1")
    scope.write("MEASU:MEAS1:STATE ON")
    scope.query("*OPC?")
    
    scope.write("ACQ:STATE RUN"); scope.query("*WAI;*OPC?")
    
    for sub in ["DATARATE", "TIE", "RJ", "DJDIRAC", "TJBER"]:
        try:
            val = float(scope.query(f'MEASU:MEAS1:SUBGROUP:RESULTS:ALLACQS:MEAN? "{sub}"'))
            if val != 9.9e37:
                unit = "bps" if "RATE" in sub else "ps"
                val = val if "RATE" in sub else val * 1e12
                print(f"{sub}: {val:.3f} {unit}")
        except: print(f"{sub}: N/A")
    scope.close()

if __name__ == "__main__": main()
'''


def _get_waveform_template() -> str:
    return '''"""Waveform Capture to CSV"""
import pyvisa, csv, time
from datetime import datetime

def main():
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource("TCPIP::192.168.1.100::INSTR")
    scope.timeout = 30000
    
    scope.write("*CLS"); scope.write("HEADer OFF"); scope.write("VERBose OFF")
    scope.write("*RST"); scope.query("*OPC?"); scope.write("HEADer OFF")
    scope.write("DISplay:WAVEView1:CH1:STATE ON")
    scope.write("AUTOS EXECUTE"); time.sleep(5)
    scope.write("ACQ:STOPA SEQ"); scope.write("ACQ:STATE RUN"); scope.query("*WAI;*OPC?")
    
    if scope.query("CH1:CLIPping?").strip() == "1":
        print("WARNING: Signal clipping!")
    
    scope.write("DATA:SOURCE CH1"); scope.write("DATA:ENCdg ASCII"); scope.write("DATA:START 1")
    reclen = int(scope.query("HOR:MODE:RECORDLENGTH?"))
    scope.write(f"DATA:STOP {reclen}")
    
    xincr = float(scope.query("WFMOutpre:XINcr?"))
    pt_off = int(scope.query("WFMOutpre:PT_Off?"))
    ymult = float(scope.query("WFMOutpre:YMUlt?"))
    yoff = float(scope.query("WFMOutpre:YOFf?"))
    yzero = float(scope.query("WFMOutpre:YZEro?"))
    
    raw = [int(v) for v in scope.query("CURVE?").strip().split(',')]
    voltage = [(v - yoff) * ymult + yzero for v in raw]
    time_axis = [(i - pt_off) * xincr for i in range(len(raw))]
    
    fn = f"waveform_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with open(fn, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Time (s)', 'Voltage (V)'])
        for t, v in zip(time_axis, voltage):
            w.writerow([f'{t:.12e}', f'{v:.9e}'])
    print(f"Saved {len(raw)} points to {fn}")
    scope.close()

if __name__ == "__main__": main()
'''


def _get_pta_template() -> str:
    return '''"""Tek PTA Compatible Test Module Template
Tek PTA cuts development time by 90%+ for production testing."""
import pyvisa, time
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class TestResult(Enum):
    PASS = "PASS"; FAIL = "FAIL"; ERROR = "ERROR"

@dataclass
class TestOutput:
    result: TestResult
    value: float
    units: str
    low_limit: Optional[float] = None
    high_limit: Optional[float] = None
    error: Optional[str] = None

class FrequencyTest:
    name = "Frequency Accuracy"
    expected_freq = 1e6
    tolerance_pct = 1.0
    
    def __init__(self, addr): self.addr = addr; self.scope = None
    
    def setup(self):
        rm = pyvisa.ResourceManager()
        self.scope = rm.open_resource(self.addr)
        self.scope.timeout = 30000
        self.scope.write("*CLS"); self.scope.write("HEADer OFF")
        return True
    
    def execute(self) -> TestOutput:
        try:
            self.scope.write("*RST"); self.scope.query("*OPC?")
            self.scope.write("HEADer OFF")
            self.scope.write("DISplay:WAVEView1:CH1:STATE ON")
            self.scope.write("AUTOS EXECUTE"); time.sleep(5)
            self.scope.write("ACQ:STOPA SEQ")
            self.scope.write("MEASU:ADDMEAS FREQUENCY")
            self.scope.write("MEASU:MEAS1:SOURCE CH1")
            self.scope.write("MEASU:MEAS1:STATE ON")
            self.scope.query("*OPC?")
            self.scope.write("ACQ:STATE RUN"); self.scope.query("*WAI;*OPC?")
            
            freq = float(self.scope.query("MEASU:MEAS1:RESUlts:ALLAcqs:MEAN?"))
            low = self.expected_freq * (1 - self.tolerance_pct/100)
            high = self.expected_freq * (1 + self.tolerance_pct/100)
            
            return TestOutput(
                result=TestResult.PASS if low <= freq <= high else TestResult.FAIL,
                value=freq, units="Hz", low_limit=low, high_limit=high
            )
        except Exception as e:
            return TestOutput(result=TestResult.ERROR, value=0, units="Hz", error=str(e))
    
    def cleanup(self):
        if self.scope: self.scope.close()

if __name__ == "__main__":
    test = FrequencyTest("TCPIP::192.168.1.100::INSTR")
    if test.setup():
        r = test.execute()
        print(f"{test.name}: {r.result.value} ({r.value:.6e} {r.units})")
        test.cleanup()
'''


# =============================================================================
# MAIN
# =============================================================================

def main():
    global _server_start_time
    _server_start_time = datetime.now()
    
    print("\n" + "=" * 60, file=sys.stderr)
    print("🔬 Tektronix MCP Server v1.1.0", file=sys.stderr)
    print("   - Combined MSO 2/4/5/6/7 command database", file=sys.stderr)
    print("   - Local docs search includes Tek PTA source", file=sys.stderr)
    print("   - Live instrument control via PyVISA", file=sys.stderr)
    print("   - Unbuffered I/O for reliable transport", file=sys.stderr)
    print("   - Vector store timeout protection (25s)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    flush_output()
    
    load_commands_database()
    
    print(f"\n📊 Total: {_total_commands:,} commands across {len(_commands_flat)} instrument families", file=sys.stderr)
    
    if OPENAI_API_KEY and VECTOR_STORE_ID:
        print(f"✓ Vector store: {VECTOR_STORE_ID[:20]}...", file=sys.stderr)
    else:
        print("✗ Vector store not configured", file=sys.stderr)
    
    if PYVISA_AVAILABLE:
        print("✓ PyVISA available for live instrument control", file=sys.stderr)
    else:
        print("✗ PyVISA not installed (instrument control disabled)", file=sys.stderr)
    
    print("\n🚀 Server ready\n" + "=" * 60, file=sys.stderr)
    flush_output()
    
    mcp.run()


if __name__ == "__main__":
    main()
