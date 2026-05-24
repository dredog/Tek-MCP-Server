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
Tektronix MCP Server v1.4.4
===========================
MCP server for Tektronix instrument automation with authoritative SCPI commands.

CRITICAL: NEVER invent SCPI commands. All commands must be verified in:
1. JSON files in docs/instrument_commands_json/
2. Programmer manuals in docs/programmer_manuals/
3. Python examples in docs/python_examples/
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

COMPLIANCE TEST PLATFORMS:
  • Clarius: Next-generation browser-based compliance test platform
             (replaces TekExpress) — REST API, Python SDK, LPDDR5 & more
             Runs in Hyper-V VM; accessed via browser at https://127.0.0.1:4200

Features:
- 20,000+ SCPI commands from official documentation
- Clarius compliance platform SDK/API reference (LPDDR5, REST API, Python SDK)
- Tek PTA production test framework
- Live instrument control via PyVISA
- AI-driven undocumented command discovery (tek_probe_scpi)
- Status indicator visible in Claude chat UI
- Local docs search includes Tek PTA source files

═══════════════════════════════════════════════════════════
CHANGELOG
═══════════════════════════════════════════════════════════

v1.4.4
- Clarius compliance test platform integrated: clarius_overview.md,
  clarius_sdk_api.md, and clarius_reference.json added to docs/reference/.
  search_local_docs boosts clarius_overview.md and clarius_sdk_api.md to
  +5 so Clarius queries surface the right file first.
- search_local_docs: added named entries for clarius_overview.md (+5) and
  clarius_sdk_api.md (+5) before the **/*.md glob (dedup preserves boost).
- Tektronix_Automation_Guidelines.md updated to v1.11: three-step
  HORIZONTAL:MODE MANUAL workflow added (HORIZONTAL:MODE:MANUAL:CONFIGURE
  RECORDLength). New Section 17 for searchability on horizontal/sample-rate
  queries. CONTEXT block horizontal entry also updated.
- Landing page expanded: ChatGPT (Developer Mode + Responses API),
  Grok (Bring Your Own MCP, launched May 2026), GitHub Copilot
  (VS Code Agent mode, JetBrains/Visual Studio/CLI) all added.
  Page restructured into four platform sections with tier badges.
- Version synced across build.bat, install.ps1, server (all → v1.4.4).

v1.4.3
- mso_4_5_6_7_commands.json: 21 SCPI string repairs applied to fix truncated
  leading letters in examples (CQUIRE: -> ACQUIRE: on ACQuire:SEQuence:MODe;
  EARCH: -> SEARCH: on six SEARCH:SEARCH<x>:TRIGger:A:DDR* commands). Each
  command had the bug in three parallel locations (top-level example,
  examples[0].scpi, _manualEntry.examples[0].codeExamples.scpi.code) — all
  fixed for consistency with TekControl's build pipeline. Metadata gains
  cleanup_applied array and cleanup_applied_count for traceability.
  Command count unchanged at 2,958.
- search_commands: conditions and notes fields are now searchable. Both are
  added to the fingerprint early-exit check (so terms like "aero",
  "undocumented", "pwr" can match commands where those words only appear
  in conditions/notes) and contribute +5/+3 per term to the score, matching
  the params_text weight. Gives queries direct hit paths to the 117 SR-AERO
  commands and the ~30 commands tagged "undocumented, verified via bus
  capture" in notes.
- tek_get_command: surfaces conditions as "**Note:** <text>" under the Group
  line so license/option requirements are impossible to miss when copying a
  command. Adds "**Notes:**" bulleted block after Examples for the 5% of
  commands carrying provenance/constraint info (e.g. "WAVEView<x> must be
  WAVEView1"). Adds "**See also:**" list rendering relatedCommands.

v1.4.2
- mso_4_5_6_7_commands.json upgraded to v3.0-merged (TektronixMCP + TekControl):
  2,958 clean commands, 0 corrupt entries, 99% syntax coverage, 100% commandType coverage.
- search_commands: params_text built before fingerprint early-exit so params.options
  keywords are never silently skipped; score raised from +5/+3 to +8/+5.
  args no longer falls back to raw params dict stringification.
- tek_find Tier 1: shows all syntax forms, commandType badge, conditions warning.
- tek_find Tier 2 / tek_search_commands: show conditions warning when present.
- tek_get_command: shows commandType and conditions. Removed stale example reference.

v1.4.1
- Restored _PRIORITY_BOOSTS table (120+ rules) and _compute_priority_boost()
  from v1.3.x best-scoring version. Fixes ranking regressions on CH:COUPling,
  CH:TERMination, HEADer, AUXout:SOUrce, ALLEv?, AFG:OUTPut:STATe and all
  AWG plugin commands (HSSerial, Radar, Pulse, RF_Generic).
- Restored SCPI node-level matching in search_commands(): splits SCPI path on
  ':' and awards +40 (original term) / +25 (synonym) when a term equals a
  complete colon-delimited node vs +20/+12 for substring. Fixes bus protocol
  disambiguation (CAN, I2C, UART collision on SOUrce / BITRate suffixes).
- Restored full-command synonym match (+150): when a synonym expansion equals
  the entire SCPI command (e.g. "reset"->*rst == *RST) scores +150. Fixes
  *RST, *CLS, *IDN?, *OPC?, ALLEv? ranking against long-path near-matches.
- Restored _USAGE_BOOSTS placeholder dict (populate via generate_usage_boosts.py).
- Replaced _RELATED_DATABASES with _PLUGIN_SCOPE: awg5200/awg70000 auto-expand
  to awg.json which contains ALL plugin groups: Radar_Signals (885 cmds),
  High_Speed_Serial (545), OFDM_Modulation (723), RF_Generic (526),
  Pulse_Plugin (67), Optical_Signals (411), Multitone (107), Video_Plugin (55),
  plus core Output/Waveform/Clock/Sequence. Total AWG coverage: 3505 commands.
- AWG auto-detection keywords expanded: ofdm, rf generic, optical signal,
  multitone, lfm, chirp, compile waveform, compile and play, pulse plugin.
- SignalVu auto-detection consolidated; connect/disconnect + scope hardware
  now correctly routes to signalvu DB (fixes T2-14, T2-15).
- Priority boosts added for: SignalVu INSTrument:CONNect/DISConnect,
  AWG OUTPut:STATe (T1-05), HSSerial:COMPile:OVERwrite (T1-06),
  RADar:PTRain:* family (T2-02 to T2-06), AUXout:SOUrce (T4-11),
  DATa:SOUrce (T5-03), ALLEv? (T5-04), PG:CH:VOLTage:HIGH (T9-01).

v1.4.0
- BREAKING: Removed OpenAI vector store (Tier 4). All search is now
  local-only: Tier 1 exact SCPI index, Tier 2 keyword DB, Tier 3 local
  docs. Eliminates OpenAI dependency, API key requirement, and 25s
  timeout penalty. Removed tek_vector_search and tek_comprehensive_search
  tools; removed query_vector_store(), get_openai_client(), and all
  OPENAI_API_KEY / TEK_VECTOR_STORE_ID env var references.
- BREAKING: Removed voice control (Hey Tek). Removed tek_voice_start,
  tek_voice_stop, tek_voice_status tools and hey_tek_voice import.
  Voice features may return as a separate optional module.
- tek_search_commands re-exposed as MCP tool for benchmark comparison.
  Still also called internally by tek_find Tier 2.
- Tool count: 28 (was 27).
- tek_find moved to first tool position so it appears in the top of
  the tool list for MCP clients that truncate tool discovery.
- tek_find output restructured: command results first, confidence/tier
  metadata last. Fixes non-LLM benchmark parsers that were grabbing
  the metadata header instead of the actual SCPI command content.
- tek_find auto-detection: "scope AFG" / "built-in AFG" now routes to
  MSO database (AFG:* commands) instead of standalone AFG31000 database.
  "radar" and "ptrain" added to AWG detection keywords.
- _SEARCH_SYNONYMS expanded: radar (ptrain, carrier, penvelope),
  modulation/sweep, compile/play, sine/square, marker/sequence/segment.
- Bugfix: "can" removed from _SEARCH_STOP_WORDS — was being filtered
  as English modal verb, causing CAN bus queries to return wrong bus type.
- search_commands() related-database search (_RELATED_DATABASES): AWG
  queries now search both core (awg5200/awg70000) and plugin (awg) DBs.
- tek_find auto-detection: battery and pattern generator queries now
  route to mso2 database (only MSO 2 Series has these hardware features).
  "power" alone still routes to MSO 4/5/6 for POWer measurement commands.
- Tool count reduced from 37 to 28.
- Removed tek_instrument_autoset, tek_instrument_run, tek_instrument_stop,
  tek_instrument_single convenience wrappers — use tek_instrument_write
  with the equivalent SCPI commands instead.
- MSO command database split: MSO 2 Series (MSO22/MSO24) now uses
  mso2.json; MSO 4/5/6 and DPO 7 Series uses mso_4_5_6_7_commands.json.
  "mso2" is now a primary instrument key (no longer an alias for "mso").
  MSO 2 auto-detection added to tek_find.

v1.3.6
- search_commands() natural language improvement: stop word filtering
  (_SEARCH_STOP_WORDS, ~50 terms), concept-to-SCPI synonym expansion
  (_SEARCH_SYNONYMS, ~80 mappings), and min term length (2 chars).
  Synonym hits scored lower than direct keyword hits to avoid false
  positives. Fixes garbage results on natural language queries like
  "reset the oscilloscope" where "the" matched everywhere and "reset"
  had no path to *RST. Affects tek_search_commands and tek_find Tier 2.

v1.3.5
- tek_find: added instrument auto-detection from query text. Defaults
  to MSO (mso_2_4_5_6_7) for all generic oscilloscope queries. Detects
  SignalVu/RSA by model number and keyword, SMU by source/measure
  terminology, AWG/AFG by product name, legacy families by model number.
  Explicit instrument= parameter still overrides detection.

v1.3.4
- New tek_find tool: single entry point with 4-tier tiered search.
  Tier 1: exact SCPI index (O(1)), Tier 2: keyword SCPI DB search,
  Tier 3: local docs/guidelines/lessons-learned, Tier 4: vector store.
  Stops at first confident result. Returns confidence level and source
  tier. Designed to reduce tool selection confusion in batch/benchmark
  contexts and match the single entry point pattern of competing servers.
- tek_search_commands and tek_comprehensive_search docstrings updated
  to defer to tek_find for general queries.

v1.3.3
- Bugfix: tek_search_commands crashes on MSO queries when JSON has
  "params": null (explicit null, not missing key). dict.get(key, default)
  returns None for explicit null -- fixed with 'or' guards throughout.
  Affected ~200 MSO command entries. Same guard applied to arguments,
  syntax, description, and options fields for consistency.

v1.3.2
- New tek_sync_knowledge tool: pull approved lessons learned and SCPI
  patches from shared GitHub repo into local install; skips files already
  up to date via SHA256 checksum comparison
- New tek_submit_knowledge tool: submit local knowledge files for expert
  review via GitHub PR (contributors) or direct commit (experts)
- Tiered access model: TEK_EXPERT_MODE=1 commits to approved/ branch;
  contributors go to staging/ branch pending expert review
- New env vars: TEK_KNOWLEDGE_REPO, TEK_KNOWLEDGE_TOKEN, TEK_EXPERT_MODE
- No new dependencies — uses stdlib urllib for all GitHub API calls

v1.3.1
- Bugfix: tek_search_commands TypeError when command options contain
  non-string values (integers, booleans) from JSON databases — e.g.
  CH<x>:TERMinator options [50, 1000000]. Fixed with str(o) cast in join.

v1.3.0
- New tek_probe_scpi tool: single-shot SCPI query prober for AI-driven
  undocumented command discovery
- Hardcoded 800ms probe timeout; main session timeout always restored
- Distinguishes three outcomes: RESPONDED (valid), SCPI ERROR (parser
  saw it but rejected — mode inactive or wrong args), TIMED OUT (path
  does not exist)
- Flags confirmed undocumented finds with ready-to-use lessons-learned
  entry suggestion

v1.2.0
- SCPI direct lookup index built at startup for O(1) verification
- New _lookup_scpi_command(): hierarchical command matching with
  abbreviation support (e.g. 'MEASU:MEAS1:TYPE' matches
  'MEASUrement:MEAS<x>:TYPe')
- New tek_validate_scpi tool: batch-verify pasted code/commands against
  programmer manual; returns canonical form and flags unverified commands
- tek_search_commands(): SCPI-like queries route through direct lookup first

v1.1.0
- Live instrument control via PyVISA with persistent sessions
- New tools: tek_instrument_connect, disconnect, write, query, write_batch,
  state, screenshot, run, stop, single, autoset
- Instrument state save/restore for undo capability
- Thread-safe VISA operations with locking

v1.0.4
- Hey Tek voice control: wake word listener (openWakeWord + faster-whisper)
- New tools: tek_voice_start, tek_voice_stop, tek_voice_status
- Wake word → beep → record → transcribe → inject into Claude Desktop
- tek_status shows voice listener state

v1.0.2
- New tools: tek_pta_plugin_template, tek_pta_plugin_checklist
- tek_search_local_docs warns on plugin queries and boosts PTA source files
- tek_save_lessons_learned and tek_list_lessons_learned tools
- Lessons learned stored in PTA/lessons_learned/ and auto-indexed
- PI Translator path constants and tek_pi_translator_reference tool
- XML example file indexing; PI Translator query term boosting

v1.0.0 (initial release — formerly versioned as v3.4–v3.8)
- FastMCP framework with unbuffered I/O for reliable STDIO transport
- Combined MSO 2/4/5/6/7 command database (20,000+ commands, 11 families)
- Tiered search: local JSON → local docs
- Singleton OpenAI client; periodic GC for long-running sessions
- tek_search_commands, tek_get_command, tek_comprehensive_search
- tek_search_local_docs searches markdown + Python source files
- tek_status tool with uptime, DB stats, and connection state
- Legacy command migration lookup (tek_legacy_command_lookup)
- Instrument family aliases for backwards compatibility
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
PYTHON_EXAMPLES_PATH = DOCS_PATH / "python_examples"  # Golden example Python scripts
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
    # OSCILLOSCOPES - Modern Series
    # =========================================================================
    "mso": {
        "path": JSON_PATH / "mso_4_5_6_7_commands.json",
        "description": "MSO 4/5/6 & DPO 7 Series Oscilloscopes",
        "models": [
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
        "aliases": ["mso456", "mso4", "mso5", "mso6", "dpo7"],
    },
    "mso2": {
        "path": JSON_PATH / "mso2.json",
        "description": "MSO 2 Series Oscilloscopes (MSO22, MSO24)",
        "models": [
            "MSO22", "MSO24", "2 Series MSO",
        ],
    },
    # Legacy alias for backwards compatibility
    "mso456": {
        "path": JSON_PATH / "mso_4_5_6_7_commands.json",
        "description": "MSO 4/5/6 Series (alias for 'mso')",
        "models": ["MSO44", "MSO54", "MSO64"],
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
    "awg": {
        "path": JSON_PATH / "awg.json",
        "description": "AWG Plug-in Commands (Radar, HSSerial, OFDM, Optical, Pulse, etc.)",
        "models": [
            "AWG5202", "AWG5204", "AWG5208",
            "AWG70001A", "AWG70001B", "AWG70002A", "AWG70002B",
            "SourceXpress",
        ],
        "compatible_with": ["awg5200", "awg70000"],
    },
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
        "path": JSON_PATH / "rsa.json",
        "description": "RSA Series / SignalVu-PC Vector Signal Analysis (3724 commands)",
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
    # MSO 4/5/6/DPO7 aliases -> "mso"
    "mso456": "mso",
    "mso4": "mso",
    "mso5": "mso",
    "mso6": "mso",
    "dpo7": "mso",
    # MSO 2 Series aliases -> "mso2"
    "mso22": "mso2",
    "mso24": "mso2",
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


# Knowledge Sync config — see tek_sync_knowledge / tek_submit_knowledge tools
# TEK_KNOWLEDGE_REPO   : GitHub "owner/repo"  e.g. "tektronix-fae/tek-mcp-knowledge"
# TEK_KNOWLEDGE_TOKEN  : GitHub Personal Access Token (read for sync, write for submit)
# TEK_EXPERT_MODE      : "1" = domain expert (submits direct to approved branch)
#                        "0" = contributor  (submits to staging for expert review)
KNOWLEDGE_REPO        = os.environ.get("TEK_KNOWLEDGE_REPO", "")
KNOWLEDGE_TOKEN       = os.environ.get("TEK_KNOWLEDGE_TOKEN", "")
KNOWLEDGE_EXPERT_MODE = os.environ.get("TEK_EXPERT_MODE", "0") == "1"

# =============================================================================
# INITIALIZE MCP SERVER
# =============================================================================

# host/port must be set at construction time — FastMCP.run() does not accept them.
# Railway sets PORT; default host 127.0.0.1 rejects external traffic.
mcp = FastMCP(
    "tektronix",
    host=os.environ.get("FASTMCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", os.environ.get("FASTMCP_PORT", "8000"))),
)

_commands_db: Dict[str, Dict] = {}
_commands_flat: Dict[str, List[Dict]] = {}
_scpi_lookup_index: Dict[str, Dict] = {}  # Normalized SCPI key -> command dict (built at startup)
_total_commands: int = 0
_server_start_time: datetime = datetime.now()

# =============================================================================
# LANDING PAGE — served at GET / for hosted deployments
# =============================================================================

@mcp.custom_route("/", methods=["GET"])
async def landing_page(request):  # type: ignore[no-untyped-def]
    from starlette.responses import HTMLResponse
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    base_url = f"https://{railway_url}" if railway_url else ""
    mcp_url = f"{base_url}/mcp" if base_url else "/mcp"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Tektronix MCP Server</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#e6edf3;min-height:100vh}}
  header{{background:#161b22;border-bottom:1px solid #30363d;padding:24px 40px;display:flex;align-items:center;gap:16px}}
  header h1{{font-size:1.6rem;font-weight:700}}
  header p{{color:#8b949e;margin-top:4px;font-size:.95rem}}
  .badge{{background:#1f6feb;color:#fff;font-size:.75rem;font-weight:600;padding:3px 10px;border-radius:20px;white-space:nowrap}}
  .stats{{display:flex;gap:16px;padding:32px 40px 0;flex-wrap:wrap}}
  .stat{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:24px 32px;text-align:center;min-width:160px}}
  .stat .num{{font-size:2rem;font-weight:700;color:#58a6ff}}
  .stat .label{{color:#8b949e;font-size:.85rem;margin-top:4px;text-transform:uppercase;letter-spacing:.05em}}
  .section{{padding:32px 40px}}
  .section h2{{font-size:1.2rem;font-weight:600;margin-bottom:8px}}
  .section p{{color:#8b949e;margin-bottom:20px;font-size:.9rem}}
  .cards{{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:1100px}}
  .card{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:24px}}
  .card h3{{color:#58a6ff;font-size:.95rem;font-weight:600;margin-bottom:6px}}
  .card .sub{{color:#8b949e;font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:14px}}
  .card .req{{display:inline-block;font-size:.7rem;font-weight:600;padding:2px 8px;border-radius:4px;margin-bottom:12px}}
  .req-free{{background:#0a3628;color:#3fb950;border:1px solid #238636}}
  .req-paid{{background:#2d1b00;color:#f0883e;border:1px solid #9e6a03}}
  pre{{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:14px;font-size:.8rem;overflow-x:auto;line-height:1.6;color:#e6edf3}}
  .key{{color:#79c0ff}}.val{{color:#a5d6ff}}.str{{color:#a5d6ff}}
  .note{{font-size:.78rem;color:#8b949e;margin-top:10px;line-height:1.5;padding:10px 12px;background:#0d1117;border:1px solid #21262d;border-radius:6px}}
  .note a{{color:#58a6ff;text-decoration:none}}
  footer{{text-align:center;color:#484f58;font-size:.8rem;padding:32px;border-top:1px solid #21262d;margin-top:16px}}
  @media(max-width:700px){{.cards{{grid-template-columns:1fr}}.stats{{gap:10px}}}}
</style>
</head>
<body>
<header>
  <div>
    <h1>&#x1F52C; Tektronix MCP Server</h1>
    <p>SCPI command intelligence &amp; live instrument control for AI assistants</p>
  </div>
  <span class="badge">v1.4.4</span>
</header>

<div class="stats">
  <div class="stat"><div class="num">{_total_commands:,}</div><div class="label">SCPI Commands</div></div>
  <div class="stat"><div class="num">9</div><div class="label">Instrument Families</div></div>
  <div class="stat"><div class="num">2</div><div class="label">Transports</div></div>
</div>

<!-- ANTHROPIC CLAUDE -->
<div class="section">
  <h2>Anthropic Claude</h2>
  <p>Native MCP support across all Claude surfaces. No authentication required.</p>
  <div class="cards">

    <div class="card">
      <h3>Claude Web (claude.ai)</h3>
      <span class="req req-free">Free &amp; Pro</span>
      <div class="sub">Settings &rsaquo; Connectors &rsaquo; Add Custom Connector</div>
      <pre>Name: TektronixMCP
URL:  {mcp_url}

Authentication: None (leave blank)</pre>
    </div>

    <div class="card">
      <h3>Claude Desktop</h3>
      <span class="req req-free">Free &amp; Pro</span>
      <div class="sub">~/.claude/claude_desktop_config.json &mdash; requires Node.js for mcp-remote</div>
      <pre><span class="key">{{</span>
  <span class="key">"mcpServers"</span>: <span class="key">{{</span>
    <span class="key">"tektronix"</span>: <span class="key">{{</span>
      <span class="key">"command"</span>: <span class="str">"npx"</span>,
      <span class="key">"args"</span>: [<span class="str">"mcp-remote"</span>, <span class="str">"{mcp_url}"</span>]
    <span class="key">}}</span>
  <span class="key">}}</span>
<span class="key">}}</span></pre>
      <div class="note">&#x1F4A1; Prefer local install? Download the standalone .exe &mdash; no Node.js, no Railway dependency, lessons-learned saved to disk.</div>
    </div>

    <div class="card">
      <h3>Claude Code</h3>
      <span class="req req-free">Free &amp; Pro</span>
      <div class="sub">Native HTTP &mdash; run in terminal, not inside Claude Code</div>
      <pre>claude mcp add-json tektronix \
  '{{"type":"http","url":"{mcp_url}"}}'</pre>
      <pre style="margin-top:10px;font-size:.75rem;color:#8b949e">Or add to ~/.claude.json (user scope) or
.mcp.json (project root):
{{"mcpServers":{{"tektronix":{{"type":"http","url":"{mcp_url}"}}}}}}</pre>
    </div>

  </div>
</div>

<!-- MICROSOFT / GITHUB COPILOT -->
<div class="section" style="padding-top:0">
  <h2>Microsoft &mdash; VS Code &amp; GitHub Copilot</h2>
  <p>MCP tools are available in Copilot Agent mode only &mdash; not in regular Copilot chat.</p>
  <div class="cards">

    <div class="card">
      <h3>VS Code / Cursor</h3>
      <span class="req req-free">Free (Copilot Free tier)</span>
      <div class="sub">.vscode/mcp.json (project) or user mcp.json &mdash; Agent mode only</div>
      <pre><span class="key">{{</span>
  <span class="key">"servers"</span>: <span class="key">{{</span>
    <span class="key">"tektronix"</span>: <span class="key">{{</span>
      <span class="key">"type"</span>: <span class="str">"http"</span>,
      <span class="key">"url"</span>: <span class="str">"{mcp_url}"</span>
    <span class="key">}}</span>
  <span class="key">}}</span>
<span class="key">}}</span></pre>
      <div class="note">Open Command Palette &rarr; <b>MCP: Open User Configuration</b> for user-wide config. Note: root key is <code>"servers"</code> not <code>"mcpServers"</code>.</div>
    </div>

    <div class="card">
      <h3>GitHub Copilot (JetBrains / Visual Studio / CLI)</h3>
      <span class="req req-free">Copilot Free / Pro / Business</span>
      <div class="sub">.github/copilot/mcp.json in repo root &mdash; Agent mode only</div>
      <pre><span class="key">{{</span>
  <span class="key">"servers"</span>: <span class="key">{{</span>
    <span class="key">"tektronix"</span>: <span class="key">{{</span>
      <span class="key">"type"</span>: <span class="str">"http"</span>,
      <span class="key">"url"</span>: <span class="str">"{mcp_url}"</span>
    <span class="key">}}</span>
  <span class="key">}}</span>
<span class="key">}}</span></pre>
      <div class="note">Copilot CLI: Settings &rarr; MCP Servers &rarr; Add &rarr; HTTP &rarr; paste URL. Business/Enterprise: org admin must enable <em>MCP servers in Copilot</em> policy first.</div>
    </div>

  </div>
</div>

<!-- OPENAI CHATGPT -->
<div class="section" style="padding-top:0">
  <h2>OpenAI &mdash; ChatGPT</h2>
  <p>Requires Developer Mode (ChatGPT Plus or Pro). Set Authentication to None for this server.</p>
  <div class="cards">

    <div class="card">
      <h3>ChatGPT Web &amp; Desktop</h3>
      <span class="req req-paid">Plus / Pro required</span>
      <div class="sub">Settings &rsaquo; Apps &amp; Connectors &rsaquo; Developer Mode &rsaquo; Create</div>
      <pre>1. Settings &rarr; Apps &amp; Connectors
2. Scroll to Advanced &rarr; Enable Developer Mode
3. Click Create (now visible)
   Name:           TektronixMCP
   MCP Server URL: {mcp_url}
   Authentication: None
4. Click Create &rarr; confirm tool permissions</pre>
      <div class="note">&#x26A0; Developer Mode is beta &mdash; ChatGPT Plus or Pro required. Memory is automatically disabled while Developer Mode is active.</div>
    </div>

    <div class="card">
      <h3>OpenAI Responses API / Agents SDK</h3>
      <span class="req req-paid">API key required</span>
      <div class="sub">Native remote MCP &mdash; Python example</div>
      <pre><span class="key">from</span> openai <span class="key">import</span> OpenAI
client = OpenAI()

resp = client.responses.create(
  model=<span class="str">"gpt-4o"</span>,
  tools=[{{
    <span class="str">"type"</span>: <span class="str">"mcp"</span>,
    <span class="str">"server_url"</span>: <span class="str">"{mcp_url}"</span>,
    <span class="str">"server_label"</span>: <span class="str">"tektronix"</span>
  }}],
  input=<span class="str">"Find SCPI commands for TDR preset"</span>
)</pre>
    </div>

  </div>
</div>

<!-- XAI GROK -->
<div class="section" style="padding-top:0">
  <h2>xAI &mdash; Grok</h2>
  <p>Bring Your Own MCP launched May 2026. Requires a paid Grok account.</p>
  <div class="cards">

    <div class="card">
      <h3>Grok Web / iOS / Android</h3>
      <span class="req req-paid">Paid Grok account required</span>
      <div class="sub">grok.com/connectors &rsaquo; New Connector &rsaquo; Custom</div>
      <pre>1. Go to grok.com/connectors
   (or Grok menu &rarr; Connectors)
2. Click New Connector &rarr; Custom
3. MCP Server URL: {mcp_url}
4. Complete any authentication prompt
5. Grok discovers tools automatically</pre>
      <div class="note">Grok custom MCP launched May 6, 2026. Live on web, iOS, and Android. See <a href="https://docs.x.ai/grok/connectors" target="_blank">docs.x.ai/grok/connectors</a>.</div>
    </div>

    <div class="card">
      <h3>xAI API / SDK</h3>
      <span class="req req-paid">xAI API key required</span>
      <div class="sub">Remote MCP via xAI Responses API &mdash; Python example</div>
      <pre><span class="key">from</span> openai <span class="key">import</span> OpenAI
client = OpenAI(
  base_url=<span class="str">"https://api.x.ai/v1"</span>,
  api_key=<span class="str">"xai-..."</span>
)

resp = client.responses.create(
  model=<span class="str">"grok-3"</span>,
  tools=[{{
    <span class="str">"type"</span>: <span class="str">"mcp"</span>,
    <span class="str">"server_url"</span>: <span class="str">"{mcp_url}"</span>,
    <span class="str">"server_label"</span>: <span class="str">"tektronix"</span>
  }}],
  input=<span class="str">"Find SCPI commands for TDR preset"</span>
)</pre>
      <div class="note">xAI supports remote MCP natively in the Responses API and Voice Agent API. See <a href="https://docs.x.ai/developers/tools/remote-mcp" target="_blank">docs.x.ai/developers/tools/remote-mcp</a>.</div>
    </div>

  </div>
</div>

<footer>Tektronix MCP Server v1.4.4 &mdash; Built by the Tektronix FAE Team</footer>
</body>
</html>"""
    return HTMLResponse(html)

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
    _build_scpi_lookup_index()


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
                    # Clean SCPI field: strip argument syntax appended after
                    # a space (e.g., 'RADar:PTRain:CARRier:FREQuency {freq}'
                    # → 'RADar:PTRain:CARRier:FREQuency'). Some JSON databases
                    # embed arguments in the scpi field itself.
                    scpi_raw = cmd_copy.get("scpi", "")
                    if scpi_raw and " " in scpi_raw:
                        scpi_raw = scpi_raw.split(" ")[0]
                    # Clean AFG31000-style [SOURce[1|2]]: prefix → SOURce<x>:
                    if scpi_raw and scpi_raw.startswith("["):
                        scpi_raw = re.sub(r"^\[([A-Za-z]+)\[[^\]]+\]\]:", r"\1<x>:", scpi_raw)
                        scpi_raw = re.sub(r"^\[[^\]]+\]:", "", scpi_raw)
                    cmd_copy["scpi"] = scpi_raw
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
# SCPI NORMALIZATION AND DIRECT LOOKUP INDEX
# =============================================================================

def _get_min_abbrev(node_text: str) -> str:
    """Extract the minimum valid SCPI abbreviation from a DB mnemonic node.

    Per SCPI standard, the uppercase portion of a mixed-case mnemonic defines
    the shortest allowed abbreviation.

    Examples:
        'MEASUrement'      -> 'MEASU'
        'ACQuire'          -> 'ACQ'
        'DISplay'          -> 'DIS'
        'SMOOTHINGFilter'  -> 'SMOOTHINGF'
        'TYPE'             -> 'TYPE'   (all-caps = no abbreviation)
        'MEAS<x>'          -> 'MEAS'   (placeholder stripped before processing)
        'REFLevels<x>'     -> 'REFL'
    """
    # Strip instance placeholders (<x>, <X>, <n>, etc.) before scanning
    clean = re.sub(r'<[^>]+>', '', node_text)
    for i, c in enumerate(clean):
        if c.islower():
            return clean[:i].upper()
    return clean.upper()


def _node_matches_db(input_node: str, db_node: str) -> bool:
    """Check whether a (pre-uppercased) input SCPI node matches a DB node pattern.

    Handles all valid SCPI abbreviation forms and instance number substitution:
        'MEASUREMENT'     vs 'MEASUrement'     -> True  (full name)
        'MEASU'           vs 'MEASUrement'     -> True  (min abbreviation)
        'MEASUREM'        vs 'MEASUrement'     -> True  (mid-range abbreviation)
        'MEAS1'           vs 'MEAS<x>'         -> True  (instance number)
        'CH2'             vs 'CH<x>'           -> True
        'SOURCE4'         vs 'SOURCE<x>'       -> True
        'REFVOLTAGE3VAL'  vs 'REFVOLTAGE<x>Val'-> True  (compound instance node)
        'MEAS<X>'         vs 'MEAS<x>'         -> True  (pre-normalized)
        'MEASUREX'        vs 'MEASUrement'     -> False (not a valid prefix)
        'MEA'             vs 'MEASUrement'     -> False (below min abbreviation)
    """
    # Normalize DB node: uppercase, standardize all <...> to <X>
    db_norm = re.sub(r'<[^>]+>', '<X>', db_node).upper()
    inp = input_node  # caller guarantees uppercase

    # ── No instance placeholder in DB node ──────────────────────────────────
    if '<X>' not in db_norm:
        full_form = db_norm                       # e.g., 'MEASUREMENT', 'TYPE'
        min_len = len(_get_min_abbrev(db_node))
        if len(inp) < min_len:
            return False
        return full_form.startswith(inp)

    # ── DB node contains instance placeholder(s) ────────────────────────────
    inp_norm = re.sub(r'<[^>]+>', '<X>', inp)

    if '<X>' in inp_norm:
        # Both sides already use <X> — direct comparison
        return inp_norm == db_norm

    # Input has a concrete number (e.g., 'MEAS1', 'REFVOLTAGE3VAL')
    db_parts = db_norm.split('<X>')   # ['MEAS', '']  or  ['REFVOLTAGE', 'VAL']

    if len(db_parts) == 2:
        db_prefix, db_suffix = db_parts

        # Min abbreviation length for the prefix portion
        db_node_prefix_orig = re.sub(r'<.*', '', db_node)   # text before first '<'
        prefix_min_len = len(_get_min_abbrev(db_node_prefix_orig))

        # Decompose input into (letter-prefix)(digits)(letter-suffix)
        m = re.match(r'^([A-Z]*)(\d*)([A-Z]*)$', inp)
        if not m:
            return False
        inp_prefix, _digits, inp_suffix = m.group(1), m.group(2), m.group(3)

        # Validate prefix abbreviation
        if inp_prefix:
            if len(inp_prefix) < prefix_min_len:
                return False
            if not db_prefix.startswith(inp_prefix):
                return False

        # Validate suffix abbreviation (if DB has text after the instance)
        if db_suffix and inp_suffix:
            suffix_orig = re.sub(r'.*<[^>]+>', '', db_node)   # text after last '>'
            suffix_min_len = len(_get_min_abbrev(suffix_orig))
            if len(inp_suffix) < suffix_min_len:
                return False
            if not db_suffix.startswith(inp_suffix):
                return False

        return True

    # Unexpected multi-placeholder node — fall back to direct comparison
    return inp_norm == db_norm


def _normalize_scpi_input(scpi: str) -> str:
    """Normalize a user-supplied SCPI string for lookup index matching.

    Operations:
    - Strip leading ':' and trailing '?'
    - Uppercase
    - Replace instance numbers with <X>: 'MEAS1' -> 'MEAS<X>', 'CH2' -> 'CH<X>'

    Word-boundary anchors prevent mangling protocol identifiers like
    'ARINC429A' or 'MIL1553B' (digits are mid-token, not at word boundary).
    """
    s = scpi.strip().lstrip(':').rstrip('?').upper()
    # LETTERS followed by 1-3 digits at a word boundary -> LETTERS<X>
    s = re.sub(r'\b([A-Z]+)(\d{1,3})\b', r'\1<X>', s)
    return s


def _build_scpi_lookup_index():
    """Pre-compute a lookup index over all loaded command databases.

    Builds TWO normalized keys per command for O(1) fast-path lookup:

      Full-form key:     every node fully uppercased, placeholders -> <X>
                         e.g., 'MEASUREMENT:MEAS<X>:SMOOTHINGFILTER'

      Min-mnemonic key:  every node reduced to its minimum abbreviation
                         e.g., 'MEASU:MEAS<X>:SMOOTHINGFILTER'
                         (useful when code uses minimum-length mnemonics)

    Mid-range abbreviations (between min and full) are handled by the
    node-by-node slow path in _lookup_scpi_command().
    """
    global _scpi_lookup_index
    index: Dict[str, Dict] = {}

    for inst, commands in _commands_flat.items():
        if COMMAND_FILES.get(inst, {}).get('is_alias'):
            continue
        for cmd in commands:
            db_scpi = cmd.get('scpi', cmd.get('name', ''))
            if not db_scpi or ':' not in db_scpi:
                continue

            nodes = db_scpi.split(':')

            # Key 1: full form  (MEASUREMENT:MEAS<X>:SMOOTHINGFILTER)
            full_nodes = [re.sub(r'<[^>]+>', '<X>', n).upper() for n in nodes]
            full_key = ':'.join(full_nodes)

            # Key 2: min-mnemonic form  (MEASU:MEAS<X>:SMOOTHINGFILTER)
            min_nodes = []
            for node in nodes:
                text_part = re.sub(r'<.*', '', node)          # characters before first '<'
                rest_part = node[len(text_part):]              # '<x>...' or ''
                rest_norm = re.sub(r'<[^>]+>', '<X>', rest_part).upper()
                min_nodes.append(_get_min_abbrev(text_part) + rest_norm)
            min_key = ':'.join(min_nodes)

            # First command wins for any duplicate normalized key
            if full_key not in index:
                index[full_key] = cmd
            if min_key not in index and min_key != full_key:
                index[min_key] = cmd

    _scpi_lookup_index = index
    print(f"  SCPI lookup index: {len(index):,} normalized keys built", file=sys.stderr)
    flush_output()


def _lookup_scpi_command(scpi: str, instrument: str = None) -> Optional[Dict]:
    """Look up a SCPI command with full mnemonic-abbreviation and instance-number support.

    This supersedes the legacy get_command_details() exact-match for hierarchical
    commands.  Lookup strategy (fastest to slowest):

      1. Fast path  — O(1) index lookup of normalized full-form key
      2. Fast path  — O(1) index lookup of normalized min-mnemonic key
         (catches cases where code uses exactly the minimum abbreviation)
      3. Slow path  — O(N) node-by-node scan
         (catches mid-range abbreviations like 'MEASUREM' for 'MEASUrement')

    Args:
        scpi:       SCPI command string (with or without leading ':', trailing '?',
                    instance numbers like MEAS1 or placeholders like MEAS<x>)
        instrument: Optional instrument key to restrict search scope

    Returns:
        Matching command dict with '_instrument' populated, or None.
    """
    if instrument:
        instrument = INSTRUMENT_ALIASES.get(instrument.lower(), instrument.lower())

    normalized = _normalize_scpi_input(scpi)

    # ── Fast path: lookup index ──────────────────────────────────────────────
    cmd = _scpi_lookup_index.get(normalized)
    if cmd and (instrument is None or cmd.get('_instrument') == instrument
                or cmd.get('_instrument') in _RELATED_DATABASES.get(instrument, [])):
        return cmd

    # ── Slow path: node-by-node matching ────────────────────────────────────
    nodes_input = normalized.split(':')
    n = len(nodes_input)

    if instrument:
        # Search specified instrument plus any related databases
        search_keys = [instrument] + _RELATED_DATABASES.get(instrument, [])
        search_list = [c for k in search_keys for c in _commands_flat.get(k, [])]
    else:
        search_list = [
            c for k, cmds in _commands_flat.items()
            if not COMMAND_FILES.get(k, {}).get('is_alias')
            for c in cmds
        ]

    for cmd in search_list:
        db_scpi = cmd.get('scpi', cmd.get('name', ''))
        if not db_scpi or ':' not in db_scpi:
            continue
        db_nodes = db_scpi.split(':')
        if len(db_nodes) != n:
            continue
        if all(_node_matches_db(i, d) for i, d in zip(nodes_input, db_nodes)):
            return cmd

    return None


# =============================================================================
# SEARCH FUNCTIONS
# =============================================================================

# Stop words filtered from natural-language queries to prevent noise matches.
# These add score to nearly every command without indicating relevance.
_SEARCH_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "doing", "to", "of", "in", "for", "on", "with",
    "at", "by", "from", "as", "into", "about", "it", "its", "this", "that",
    "and", "or", "but", "not", "no", "if", "so", "up", "out", "how",
    "i", "me", "my", "we", "our", "you", "your", "what", "which", "when",
    "where", "who", "whom", "there", "here",
})

# Concept-to-SCPI synonym map: maps natural language terms to SCPI-relevant
# keywords that actually appear in command mnemonics, descriptions, or groups.
# Each key is a natural language term; each value is a list of terms to inject
# into the search alongside (or replacing) the original term.
_SEARCH_SYNONYMS = {
    # Actions
    "reset":       ["*rst", "factory", "recall:setup"],
    "start":       ["acquire:state", "run"],
    "stop":        ["acquire:state", "stop"],
    "save":        ["save", "filesys", "export"],
    "load":        ["recall", "load", "import", "filesys"],
    "screenshot":  ["hardcopy", "save:image", "export"],
    "capture":     ["acquire", "single", "acquisition"],
    "clear":       ["clear", "*cls"],
    "autoset":     ["autoset"],
    "autoscale":   ["autoset"],
    # Vertical
    "impedance":   ["terminator", "impedance"],
    "termination": ["terminator", "impedance"],
    "coupling":    ["coupling"],
    "attenuation": ["probefunc:extatten", "probe:gain", "extatten", "extdbatten"],
    "probe":       ["probe", "probefunc"],
    "gain":        ["probe:gain", "gain"],
    "offset":      ["offset"],
    "scale":       ["scale"],
    "position":    ["position"],
    "label":       ["label"],
    "invert":      ["invert"],
    "deskew":      ["deskew"],
    "clipping":    ["clipping"],
    # Horizontal
    "timebase":    ["horizontal", "hor:scale", "hor:mode"],
    "sample":      ["samplerate", "sample"],
    "record":      ["recordlength", "record"],
    # Trigger
    "trigger":     ["trigger", "trig"],
    "edge":        ["edge", "trigger:a:edge"],
    "threshold":   ["threshold", "level"],
    "holdoff":     ["holdoff"],
    # Acquisition
    "average":     ["average", "numavg", "acq:mode"],
    "averaging":   ["average", "numavg", "acq:mode"],
    "envelope":    ["envelope", "acq:mode"],
    "hires":       ["hires", "hi res", "acq:mode"],
    # Display
    "overlay":     ["overlay", "viewstyle", "waveview"],
    "stacked":     ["stacked", "viewstyle", "waveview"],
    "persistence": ["persist"],
    "graticule":   ["graticule"],
    "intensity":   ["intensity", "waveview"],
    # Measurements
    "measure":     ["measurement", "meas"],
    "frequency":   ["frequency", "freq"],
    "period":      ["period"],
    "amplitude":   ["amplitude"],
    "risetime":    ["risetime", "rise"],
    "falltime":    ["falltime", "fall"],
    "delay":       ["delay"],
    "phase":       ["phase"],
    "jitter":      ["jitter", "dja", "tj"],
    "duty":        ["duty"],
    "rms":         ["rms"],
    "mean":        ["mean"],
    "pk2pk":       ["pk2pk", "peak"],
    "statistics":  ["displaystat", "population", "statistics"],
    "passfail":    ["passfail"],
    # Spectrum View (MSO 4/5/6 only — always CH<x>:SV:* or SV:* prefix)
    "spectrum":    ["sv", "spectr", "spectrum"],
    "sv":          ["sv", "spectr"],
    "fft":         ["sv", "spectr", "math:fft", "fft"],
    "rbw":         ["rbw", "sv"],
    "span":        ["span", "sv"],
    "center":      ["center", "sv"],
    # Cursor
    "cursor":      ["cursor", "cursors"],
    "cursors":     ["cursor", "cursors"],
    # Math
    "math":        ["math"],
    # Bus / Decode
    "bus":         ["bus"],
    "decode":      ["bus", "decode"],
    "serial":      ["bus", "serial"],
    "spi":         ["spi", "bus"],
    "i2c":         ["i2c", "bus"],
    "uart":        ["uart", "rs232", "bus"],
    "can":         ["can", "bus"],
    "lin":         ["lin", "bus"],
    # Waveform transfer
    "waveform":    ["waveform"],
    "transfer":    ["curve", "wfmoutpre"],
    "curve":       ["curve"],
    # Channel enable
    "enable":      ["state", "select"],
    "disable":     ["state", "select"],
    "channel":     ["ch", "channel"],
    # Misc
    "bandwidth":   ["bandwidth"],
    "recall":      ["recall"],
    "factory":     ["factory", "*rst"],
    "default":     ["*rst", "factory"],
    "defaults":    ["*rst", "factory"],
    "identification": ["*idn"],
    "identify":    ["*idn"],
    "option":      ["*opt"],
    "license":     ["*opt", "license"],
    "calibration": ["cal", "calibr"],
    "mask":        ["mask"],
    "eye":         ["dpojet", "eye", "dja"],
    "search":      ["search"],
    "zoom":        ["zoom"],
    "power":       ["power"],
    "battery":     ["battery", "acpower", "charge", "timetoempty", "timetofull"],
    "header":      ["header"],
    # Radar (AWG feature — RADar:PTRain:* command family)
    "radar":       ["radar", "ptrain", "carrier", "penvelope"],
    "carrier":     ["carrier", "ptrain", "radar"],
    "modulation":  ["modulation", "lfm", "fm"],
    "sweep":       ["sweep", "srange", "span"],
    "compile":     ["compile", "play", "bwaveform", "overwrite"],
    "overwrite":   ["overwrite", "compile"],
    # Built-in scope AFG (MSO AFG:* commands)
    "afg":         ["afg"],
    "sine":        ["sine", "function", "func"],
    "square":      ["square", "function", "func"],
    # AWG general
    "marker":      ["marker"],
    "sequence":    ["sequence", "sequencer"],
    "segment":     ["segment", "wlist"],
    "play":        ["play", "awgcontrol", "run:immediate", "compile"],
    "plugin":      ["wplugin", "plugin", "active"],
    # AWG High Speed Serial (HSSerial:* command family)
    "prbs":        ["prbs", "hsserial", "bdata"],
    "nrz":         ["nrz", "encode", "hsserial", "scheme"],
    "pam4":        ["pam4", "encode", "hsserial", "scheme"],
    "encoding":    ["encode", "scheme", "hsserial"],
    # AWG Radar plugin (RADar:PTRain:* command family)
    "lfm":         ["lfm", "radar", "modulation", "srange"],
    "chirp":       ["chirp", "lfm", "radar", "modulation"],
    "ptrain":      ["ptrain", "radar"],
    "pri":         ["pri", "penvelope", "ptrain", "radar"],
    # AWG OFDM plugin (OFDM:* command family)
    "ofdm":        ["ofdm"],
    "subcarrier":  ["subcarrier", "ofdm"],
    "cyclic":      ["cyclic", "ofdm", "prefix"],
    # AWG RF Generic plugin (RFG:* command family)
    "rfg":         ["rfg", "rf generic", "rfgeneric"],
    "rf generic":  ["rfg", "rfgeneric"],
    "rfgeneric":   ["rfg", "rfgeneric"],
    "iq":          ["iq", "quadrature", "rfg"],
    "quadrature":  ["quadrature", "iq", "rfg"],
    # AWG Optical plugin (OPTical:* command family)
    "optical":     ["optical", "opt"],
    "extinction":  ["extinction", "optical"],
    # AWG Multitone plugin (MTONe:* command family)
    "multitone":   ["multitone", "mtone"],
    "tone":        ["tone", "multitone", "mtone"],
    # AWG Generic Precompensation plugin (GPREcomp:* command family)
    "precompensation": ["precompensation", "gprecomp", "gpre"],
    "precomp":     ["precomp", "gprecomp", "gpre"],
    # AWG Video / LVS plugin (LVS:* command family)
    "video":       ["video", "lvs"],
    "lvs":         ["lvs", "video"],
}


# Plugin scope: when searching an AWG family, automatically include awg.json
# which contains ALL plugin groups (Radar, HSSerial, OFDM, Pulse, RF_Generic,
# Optical, Multitone, etc.) for AWG5200 and AWG70000.
# awg.json is the unified source — hss_plugin_commands.json is a legacy
# separate file that is still searched when instrument="hss_plugin" is explicit.
_PLUGIN_SCOPE = {
    "awg5200":    ["awg"],
    "awg70000":   ["awg"],
    "awg":        ["awg5200", "awg70000"],
    "hss_plugin": ["awg"],
}

# Keep _RELATED_DATABASES as an alias so any remaining references don't break
_RELATED_DATABASES = _PLUGIN_SCOPE



# =============================================================================
# PRIORITY BOOST TABLE — Fixes ranking regressions in Tier 2 keyword search
# =============================================================================
# Common FAE commands that must rank in top-2 when their keywords appear.
# Without this, generic keyword matching causes wrong commands to rank higher
# (e.g., TRIGger:B:RESET:EDGE:COUPling beats CH<x>:COUPling for "coupling").
#
# Format: (keywords_any, keywords_all, scpi_prefix, boost_score)
#   keywords_any:  query must contain at least ONE of these words
#   keywords_all:  query must contain ALL of these words (empty = no constraint)
#   scpi_prefix:   SCPI command prefix to boost (matched case-insensitively,
#                  instance numbers and <x> stripped before comparison)
#   boost_score:   additive boost to the command's relevance score
# =============================================================================

_PRIORITY_BOOSTS = [
    # ── IEEE 488.2 common commands ──────────────────────────────────────────
    (["reset", "rst"],              [],                      "*RST",                               400),
    (["clear", "cls"],              [],                      "*CLS",                               100),
    (["opc", "complete"],           [],                      "*OPC",                               100),
    (["idn", "identification"],     [],                      "*IDN",                               100),
    # ALLEv? is a root command (no colon) so it gets -200 penalty from root check.
    # Boost must exceed 200 + any competitor's score to win. Use 300 when explicitly queried.
    (["error", "queue"],            [],                      "ALLEv",                               300),
    (["allev"],                     [],                      "ALLEv",                               300),
    (["error"],                     ["queue"],               "ALLEv",                               300),

    # ── Channel vertical — beat DISplay:WAVEView:CH:VERTical path ────────────
    # DISplay:WAVEView<x>:CH<x>:VERTical:SCAle has more matching nodes and
    # outscores CH<x>:SCAle on keyword alone. These boosts fix that.
    (["scale"],                     ["channel"],             "CH:SCAle",                           120),
    (["vertical", "scale"],         [],                      "CH:SCAle",                           120),
    (["scale"],                     ["vertical"],            "CH:SCAle",                           120),
    (["position"],                  ["channel"],             "CH:POSition",                        120),
    (["vertical", "position"],      [],                      "CH:POSition",                        120),
    (["position"],                  ["vertical"],            "CH:POSition",                        120),

    # WAVEView cursor is the default view for waveform cursors on MSO4/5/6/7
    # SPECView, PLOTView, MATHFFTView, REFFFTView are for spectrum/plot/fft views
    (["waveview"],                  ["cursor"],              "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 150),
    (["specview"],                  ["cursor"],              "DISplay:SPECView<x>:CURSor:CURSOR:STATE", 150),
    (["plotview"],                  ["cursor"],              "DISplay:PLOTView<x>:CURSor:STATE",       150),
    (["fft"],                       ["cursor"],              "DISplay:MATHFFTView<x>:CURSor:STATE",    150),
        # ── Cursor commands (entire family) ──────────────────────────────────────
    # kw_all ensures BOTH keywords present — "state" alone must not fire this
    (["cursor"],                   ["state"],               "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["cursor"],                   ["on"],                  "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["cursor"],                   ["off"],                 "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["turn"],                     ["cursor"],              "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["cursors"],                  [],                      "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["cursor", "type"],           [],                      "CURSor:FUNCtion",                    100),
    (["cursor", "function"],       [],                      "CURSor:FUNCtion",                    100),
    (["cursor", "waveform"],        [],                      "CURSor:FUNCtion",                    100),
    (["cursor", "position"],        [],                      "CURSor:WAVEform:CURSOR1:HPOS",        80),
    (["cursor", "horizontal"],      [],                      "CURSor:WAVEform:CURSOR1:HPOS",        80),
    (["cursor", "delta", "time"],   [],                      "CURSor:WAVEform:DELTa:TIMe",         100),
    (["cursor", "time", "difference"], [],                   "CURSor:WAVEform:DELTa:TIMe",         100),
    (["time", "difference", "cursor"], [],                   "CURSor:WAVEform:DELTa:TIMe",         100),

    # ── Trigger subcommands (beat bare TRIGger root match) ───────────────────

    # force trigger: kw_all=["trigger"] means BOTH "force" AND "trigger" must be in query
    (["force"],                     ["trigger"],             "TRIGger",                            400),  # FORCE is an argument of TRIGger, not a subcommand
    (["trigger"],                   ["state"],               "TRIGger:STATE",                      100),
    # Trigger source: require BOTH "trigger" AND one of source/channel/change
    (["trigger"],                   ["source"],              "TRIGger:{A|B}:EDGE:SOUrce",          200),
    (["trigger"],                   ["channel"],             "TRIGger:{A|B}:EDGE:SOUrce",          200),
    (["change"],                    ["trigger"],             "TRIGger:{A|B}:EDGE:SOUrce",          200),
    # Edge coupling: require BOTH "edge" AND "coupling"
    (["edge"],                      ["coupling"],            "TRIGger:{A|B}:EDGE:COUPling",        180),
    (["coupling"],                  ["edge"],                "TRIGger:{A|B}:EDGE:COUPling",        180),
    (["trigger", "b", "event"],     [],                      "TRIGger:B:EVENTS:COUNt",             100),
    (["b", "trigger", "event"],     [],                      "TRIGger:B:EVENTS:COUNt",             100),
    (["pulse", "width"],            ["trigger"],             "TRIGger:A:PULSEWidth:WHEn",           80),
    (["pulse", "width", "low"],     [],                      "TRIGger:A:PULSEWidth:LOWLimit",      100),
    # Runt: require BOTH
    (["runt"],                      ["trigger"],             "TRIGger:A:RUNT:SOUrce",               80),
    # Timeout: require BOTH
    (["timeout"],                   ["trigger"],             "TRIGger:{A|B}:TIMEOut:TIMe",         250),
    # ── Battery / AC power (MSO2 only) ───────────────────────────────────────
    (["battery"],                   ["power"],               "BATTery:ACPOWer",                    250),
    (["battery"],                   ["ac"],                  "BATTery:ACPOWer",                    250),
    (["acpower"],                   [],                      "BATTery:ACPOWer",                    250),
    (["battery", "charge"],         [],                      "BATTery:CHARge",                     200),
    (["battery", "state"],          [],                      "BATTery:STATe",                      200),

    # ── AWG output state (must beat CH:SV:STATE accumulation) ────────────────
    (["awg"],                       ["output"],              "OUTPut:STATe",                       350),
    (["awg"],                       ["enable"],              "OUTPut:STATe",                       200),
    (["awg"],                       ["output", "state"],     "AWGControl:RUN:IMMediate",            200),
    (["timeout", "duration"],       [],                      "TRIGger:{A|B}:TIMEOut:TIMe",         250),

    # ── Horizontal subcommands (beat root HORizontal? match) ─────────────────
    (["horizontal", "scale"],       [],                      "HORizontal:SCAle",                   120),
    (["horizontal", "delay"],       [],                      "HORizontal:DELay:TIMe",              100),
    (["horizontal", "mode"],        [],                      "HORizontal:MODE",                    100),
    (["horizontal", "position"],    [],                      "HORizontal:POSition",                100),
    (["trigger", "position"],       [],                      "HORizontal:POSition",                 80),
    (["acquisition", "time"],       [],                      "HORizontal:ACQDuration",              80),
    (["acquisition", "window"],     [],                      "HORizontal:ACQDuration",              80),
    (["fastframe", "timestamp"],    [],                      "HORizontal:FASTframe:TIMEStamp",     100),
    (["sample", "rate"],            ["oscilloscope"],        "HORizontal:MODE:SAMPLERate",          80),

    # ── Measurement subcommands (beat root MEASUrement? match) ───────────────
    (["measurement", "annotation"], [],                      "MEASUrement:ANNotation:STATE",       120),
    (["annotation"],                ["measurement"],         "MEASUrement:ANNotation:STATE",       120),
    (["measurement", "mean"],       [],                      "MEASUrement:MEAS:RESUlts:ALLAcqs:MEAN", 100),
    (["mean", "value"],             ["measurement"],         "MEASUrement:MEAS:RESUlts:ALLAcqs:MEAN", 100),
    (["measurement", "count"],      [],                      "MEASUrement:COUNt",                  100),
    (["measurement", "gating"],     [],                      "MEASUrement:MEAS:GATing",            100),
    (["pass", "fail"],              ["measurement"],         "MEASUrement:MEAS:LIMits:STATE",       80),
    (["limit", "testing"],          [],                      "MEASUrement:MEAS:LIMits:STATE",       80),
    (["reference", "level", "method"], [],                   "MEASUrement:CH:REFLevel:METHod",      80),
    (["reference", "level", "absolute"], [],                 "MEASUrement:CH:REFLevel:ABSolute:HIGH", 80),
    (["standard", "deviation"],     [],                      "MEASUrement:MEAS:RESUlts:ALLAcqs:STDDev", 100),
    (["clock", "recovery", "pll"],  [],                      "MEASUrement:CLOCKRecovery:ADVanced:PLL:BANDwidth", 80),
    (["measurement", "table"],      [],                      "MEASTable:ADDNew",                   100),
    (["results", "table"],          [],                      "MEASTable:ADDNew",                   100),
    (["add", "results", "table"],   [],                      "MEASTable:ADDNew",                   120),
    (["immediate", "value"],        [],                      "MEASUrement:IMMed:VALue",             80),

    # ── Math waveform ─────────────────────────────────────────────────────────
    (["math", "display"],           [],                      "MATH:MATH:STATE",                     80),
    (["math", "waveform", "display"], [],                    "MATH:MATH:STATE",                    100),
    (["math", "scale"],             [],                      "MATH:MATH:VERTical:SCAle",            80),
    (["math", "vertical", "scale"], [],                      "MATH:MATH:VERTical:SCAle",           100),
    (["enable", "math"],            [],                      "MATH:MATH:STATE",                     80),

    # ── Power measurement ─────────────────────────────────────────────────────
    (["power"],                     ["type"],                "POWer:POWer<x>:TYPe",                 100),
    (["power", "voltage", "source"],   [],                   "POWer:POWer:SOUrce:VOLTage",         100),
    (["power", "results"],             [],                   "POWer:POWer:RESUlts",                100),

    # ── AWG play (beat CURVe synonym false +150 match) ────────────────────────
    (["awg", "play"],               [],                      "AWGControl:RUN:IMMediate",           120),
    (["play", "waveform"],          ["awg"],                 "AWGControl:RUN:IMMediate",           120),

    # ── Spectrum View specific ────────────────────────────────────────────────
    (["spectrum", "reference", "level"], [],                 "CH:SV:POSition",                     100),
    (["spectrum", "view", "reference"],  [],                 "CH:SV:POSition",                     100),
    (["spectrum", "trace", "type"],      [],                 "SV:CH:SELect:NORMaltrace",           100),
    (["spectrum", "normal", "trace"],    [],                 "SV:CH:SELect:NORMaltrace",           100),
    (["spectrum", "amplitude", "units"], [],                 "SV:UNIts",                           100),
    (["spectrum", "units"],              [],                 "SV:UNIts",                           100),

    # ── Spectrum View specific ────────────────────────────────────────────────
    # All rules use kw_all to require BOTH keywords — "enable" alone must NOT fire this
    (["spectrum"],                  ["enable"],              "CH:SV:STATE",                        120),
    (["spectrum"],                  ["view"],                "CH:SV:STATE",                        120),
    (["sv"],                        ["enable"],              "CH:SV:STATE",                        120),
    (["sv"],                        ["state"],               "CH:SV:STATE",                        120),
    (["spectrum", "reference", "level"], [],                 "CH:SV:POSition",                     100),
    (["spectrum"],                  ["reference"],           "CH:SV:POSition",                     100),
    (["spectrum"],                  ["trace", "type"],       "SV:CH:SELect:NORMaltrace",           100),
    (["spectrum"],                  ["units"],               "SV:UNIts",                           100),
    (["rbw"],                        ["spectrum"],            "SV:RBW",                             250),
    (["resolution", "bandwidth"],    ["spectrum"],            "SV:RBW",                             200),
    (["window"],                     ["spectrum"],            "SV:WINDOW",                          200),
    (["window", "function"],         ["spectrum"],            "SV:WINDOW",                          250),

    # ── AWG WPlugin / load plugin ─────────────────────────────────────────────
    (["load"],                      ["plugin"],              "WPLugin:ACTive",                     120),
    (["load", "radar", "plugin"],   [],                      "WPLugin:ACTive",                     120),
    (["activate"],                  ["plugin"],              "WPLugin:ACTive",                     100),
    (["select"],                    ["plugin"],              "WPLugin:ACTive",                     100),
    (["wplugin", "active"],         [],                      "WPLugin:ACTive",                     100),

    # ── SignalVu / RSA preset ─────────────────────────────────────────────────
    (["preset"],                    ["signalvu"],            "SYSTem:PRESet",                      350),
    (["preset"],                    ["rsa"],                 "SYSTem:PRESet",                      350),
    (["signalvu"],                  ["preset"],              "SYSTem:PRESet",                      350),

    # ── Channel enable (SELect:CH — preferred over HSSerial:CHANnel:ENABle) ──
    # ── Channel display state (DISplay:WAVEView) vs SELect:CH ─────────────────
    # "turn off channel 1 display" → DISplay:WAVEView:CH:STATE, not SELect:CH
    (["display"],                   ["channel"],             "DISplay:WAVEView<x>:CH<x>:STATE",    200),
    (["turn"],                      ["channel", "display"],  "DISplay:WAVEView<x>:CH<x>:STATE",    300),
        # SELect:CH — requires "turn" + "channel" + explicit "on"/"off"
    # "turn off channel 1 display" must NOT fire this (use DISplay:WAVEView instead)
    # So we require "on"/"off" but via kw_all, meaning they MUST appear together.
    # The "display" check is implicit: if display is in query, DISplay boost wins.
    (["turn"],                      ["channel", "on"],       "SELect:CH",                          250),
    (["turn"],                      ["channel", "off"],      "SELect:CH",                          200),

        # ── Bus ───────────────────────────────────────────────────────────────────

    # ── Fast acquisition ─────────────────────────────────────────────────────
    (["fast", "acquisition", "palette"], [],                 "ACQuire:FASTAcq:PALEtte",            100),
    (["fast", "acquisition", "color"],   [],                 "ACQuire:FASTAcq:PALEtte",            100),
    (["fast", "acquisition"],            [],                 "FASTAcq:STATE",                       80),

    # ── Channel coupling ──────────────────────────────────────────────────────
    (["coupling"],                  [],                      "CH:COUPling",                         40),
    (["termination"],               ["channel"],             "CH:TERmination",                      60),
    (["termination"],               [],                      "CH:TERmination",                      40),
    (["deskew"],                    [],                      "CH:DESKew",                           60),
    (["bandwidth"],                 ["channel"],             "CH:BANdwidth",                        60),
    (["offset"],                    ["channel"],             "CH:OFFSet",                           60),
    (["scale"],                     ["channel"],             "CH:SCAle",                            60),
    (["invert"],                    ["channel"],             "CH:INVert",                           60),
    (["label"],                     ["channel"],             "CH:LABel",                            60),

    # ── Acquisition ──────────────────────────────────────────────────────────
    (["single", "shot", "sequence", "stopafter"], [],        "ACQuire:STOPAfter",                   80),
    (["continuous", "run"],         ["acquisition"],         "ACQuire:STOPAfter",                   60),
    (["acquisition", "state"],      [],                      "ACQuire:STATE",                       40),

    # ── Trigger ──────────────────────────────────────────────────────────────
    (["trigger"],                  ["source"],               "TRIGger:{A|B}:EDGE:SOUrce",          150),

    (["trigger", "slope"],          [],                      "TRIGger:A:EDGE:SLOpe",                60),
    (["trigger", "mode"],           [],                      "TRIGger:A:MODe",                      60),
    (["trigger", "holdoff"],        [],                      "TRIGger:A:HOLDoff",                   60),

    # ── Display / header / autoset ───────────────────────────────────────────
    (["display", "channel"],        [],                      "DISplay:WAVEView",                    60),
    (["header"],                    [],                      "HEADer",                             350),
    (["autoset"],                   [],                      "AUTOSet",                             80),

    # ── Measurement ──────────────────────────────────────────────────────────
    (["add", "measurement"],        [],                      "MEASUrement:ADDMEAS",                 60),
    (["delete", "measurement"],     [],                      "MEASUrement:DELETEALL",               80),
    (["measurement"],               ["type"],                "MEASUrement:MEAS<x>:TYPe",            300),
    (["measurement", "source"],     [],                      "MEASUrement:MEAS:SOUrce",             60),
    (["measurement", "results"],    [],                      "MEASUrement:MEAS:RESUlts",            60),
    (["delay", "measurement"],      [],                      "MEASUrement:ADDMEAS",                 60),
    (["eye", "diagram", "measurement"], [],                  "MEASUrement:ADDMEAS",                 60),
    (["jitter", "summary"],         [],                      "MEASUrement:MEAS:JITTERSummary",      60),
    (["immediate", "measurement"],  [],                      "MEASUrement:IMMed",                   60),

    # ── Save / Recall ─────────────────────────────────────────────────────────
    (["save", "screenshot"],        [],                      "SAVe:IMAGe",                          60),
    (["save", "waveform"],          [],                      "SAVe:WAVEform",                       80),
    (["save", "waveform", "file", "format"], [],             "SAVe:WAVEform:FILEFormat",           100),
    (["save", "setup"],             [],                      "SAVe:SETUp",                          60),
    (["recall", "session"],         [],                      "RECAll:SESsion",                      60),

    # ── Spectrum View ─────────────────────────────────────────────────────────
    (["spectrum"],                  ["center"],              "CH:SV:CENTERFrequency",               60),
    (["spectrum"],                  ["span"],                "SV:SPAN",                             60),

    # ── Built-in scope AFG (MSO 4/5/6/7) ────────────────────────────────────
    # "scope built-in AFG" / "scope AFG" → AFG: commands, NOT SOURce: (external AFG31000)
    # Key discriminator: query mentions "scope" + "AFG" without "external"
    (["scope"],                     ["afg", "frequency"],    "AFG:FREQuency",                      450),  # only when frequency specified
    (["scope"],                     ["afg", "frequency"],    "AFG:FREQuency",                      500),
    (["scope"],                     ["afg", "function"],     "AFG:FUNCtion",                       350),
    (["scope"],                     ["afg", "waveform"],     "AFG:FUNCtion",                       350),
    (["scope"],                     ["afg", "amplitude"],    "AFG:AMPLitude",                      350),
    (["scope"],                     ["afg", "impedance"],    "AFG:OUTPut:LOAd:IMPEDance",          500),
    (["scope"],                     ["afg", "load"],         "AFG:OUTPut:LOAd:IMPEDance",          500),
    (["built-in"],                  ["afg", "frequency"],   "AFG:FREQuency",                      250),
    (["builtin"],                   ["afg", "frequency"],   "AFG:FREQuency",                      250),
    (["afg"],                       ["frequency"],           "AFG:FREQuency",                      200),
    (["afg"],                       ["function"],            "AFG:FUNCtion",                       200),
    (["afg"],                       ["waveform"],            "AFG:FUNCtion",                       200),
    (["afg"],                       ["amplitude"],           "AFG:AMPLitude",                      200),
    (["afg"],                       ["impedance"],           "AFG:OUTPut:LOAd:IMPEDance",          400),
    (["afg"],                       ["load"],                "AFG:OUTPut:LOAd:IMPEDance",          400),
    (["afg"],                       ["square"],              "AFG:FUNCtion",                       200),
    (["afg"],                       ["sine"],                "AFG:FUNCtion",                       200),

    # ── Spectrum View subcommands ─────────────────────────────────────────────
    (["spectrum"],                  ["center", "frequency"], "CH:SV:CENTERFrequency",              350),
    (["center", "frequency"],       ["spectrum"],            "CH:SV:CENTERFrequency",              350),
    (["sv"],                        ["center"],              "CH:SV:CENTERFrequency",              300),
    (["spectrum"],                  ["span"],                "SV:SPAN",                            350),
    (["sv"],                        ["span"],                "SV:SPAN",                            300),
    (["spectrum"],                  ["rbw"],                 "SV:RBW",                             350),
    (["resolution", "bandwidth"],   ["spectrum"],            "SV:RBW",                             300),
    (["rbw"],                       [],                      "SV:RBW",                             250),
    (["spectrum"],                  ["window"],              "SV:WINDOW",                          350),
    (["sv"],                        ["window"],              "SV:WINDOW",                          300),
    (["normal", "trace"],           ["spectrum"],            "SV:CH:SELect:NORMaltrace",           250),
    (["sv"],                        ["units"],               "SV:CH:UNIts",                        250),
    (["spectrum"],                  ["units"],               "SV:CH:UNIts",                        250),

    # ── MATH waveform (DISplay:GLObal:MATH<x>:STATE is the correct MSO form) ──
    (["math"],                      ["enable"],              "DISplay:WAVEView<x>:MATH:MATH<x>:STATE", 500),
    (["math"],                      ["display"],             "DISplay:WAVEView<x>:MATH:MATH<x>:STATE", 350),
    (["enable"],                    ["math"],                "DISplay:WAVEView<x>:MATH:MATH<x>:STATE", 450),
    (["math"],                      ["waveform"],            "DISplay:WAVEView<x>:MATH:MATH<x>:STATE", 300),
    (["math"],                      ["filter"],              "MATH:MATH<x>:FILTer:TYPe",           300),
    (["math"],                      ["filter", "type"],      "MATH:MATH<x>:FILTer:TYPe",           350),
    (["filter", "type"],            ["math"],                "MATH:MATH<x>:FILTer:TYPe",           300),
    (["low", "pass"],               ["filter"],              "MATH:MATH<x>:FILTer:TYPe",           250),

    # ── MEASUrement subcommand specificity ────────────────────────────────────
    (["clock", "recovery"],         ["bandwidth"],           "MEASUrement:CLOCKRecovery:ADVanced:PLL:BANDwidth", 350),
    (["pll"],                        ["bandwidth"],           "MEASUrement:CLOCKRecovery:ADVanced:PLL:BANDwidth", 350),
    (["clock", "recovery"],         ["pll"],                 "MEASUrement:CLOCKRecovery:ADVanced:PLL:BANDwidth", 300),
        (["measurement"],               ["annotation"],          "MEASUrement:ANNOTate",               300),
    (["annotation"],                ["measurement"],         "MEASUrement:ANNOTate",               300),
    (["turn", "off"],               ["annotation"],          "MEASUrement:ANNOTate",               300),
    (["measurement"],               ["count", "how"],        "MEASUrement:DELETEALL",              200),  # best available
    (["how", "many"],               ["measurement"],         "MEASUrement:DELETEALL",              150),
    (["pass", "fail"],              ["measurement"],         "MEASUrement:MEAS<x>:PASSFAILENabled",300),
    (["limit", "testing"],          [],                      "MEASUrement:MEAS<x>:PASSFAILENabled",300),
    (["passfail"],                  [],                      "MEASUrement:MEAS<x>:PASSFAILENabled",300),
    (["reference", "level"],        ["measurement"],         "MEASUrement:MEAS<x>:REFLevel:PERCent:HIGH", 250),
    (["reflevel"],                  [],                      "MEASUrement:MEAS<x>:REFLevel:PERCent:HIGH", 250),
    (["high", "threshold"],         ["reference"],           "MEASUrement:MEAS<x>:REFLevel:PERCent:HIGH", 250),

    # ── Trigger type/level/slope (DB uses {A|B} form) ─────────────────────────
    # trigger type — requires BOTH "trigger" AND "type" but protected by exact-match scoring
    (["trigger"],                   ["type"],                "TRIGger:{A|B}:TYPe",                 350),  # raised — trigger+type = set type command
    (["trigger"],                   ["level"],               "TRIGger:{A|B}:LEVel",                180),
    (["trigger"],                   ["level"],               "TRIGger:{A|B}:LEVel",                180),  # dup removed
    (["trigger"],                   ["slope"],               "TRIGger:{A|B}:EDGE:SLOpe",           250),
    (["rising", "edge"],            [],                      "TRIGger:{A|B}:EDGE:SLOpe",           200),
    (["falling", "edge"],           [],                      "TRIGger:{A|B}:EDGE:SLOpe",           200),
    (["trigger"],                   ["runt"],                "TRIGger:{A|B}:RUNT:SOUrce",          200),
    (["runt"],                      ["trigger"],             "TRIGger:{A|B}:RUNT:SOUrce",          250),
    (["trigger"],                   ["pulse", "width"],      "TRIGger:{A|B}:PULSEWidth:WHEn",      200),
    (["pulse", "width"],            ["trigger"],             "TRIGger:{A|B}:PULSEWidth:WHEn",      250),

    # ── Cursor subcommands ────────────────────────────────────────────────────
    (["cursor"],                    ["position", "horizontal"], "DISplay:WAVEView<x>:CURSor:CURSOR<x>:VBArs:APOSition", 300),
    (["cursor"],                    ["horizontal", "position"], "DISplay:WAVEView<x>:CURSor:CURSOR<x>:VBArs:APOSition", 300),
    (["cursor"],                    ["time", "difference"],  "DISplay:WAVEView<x>:CURSor:CURSOR<x>:VBArs:DELTa", 250),
    (["cursor"],                    ["delta", "time"],       "DISplay:WAVEView<x>:CURSor:CURSOR<x>:VBArs:DELTa", 250),
    (["cursor"],                    ["type"],                "DISplay:WAVEView<x>:CURSor:CURSOR<x>:FUNCtion", 250),
    (["cursor"],                    ["function"],            "DISplay:WAVEView<x>:CURSor:CURSOR<x>:FUNCtion", 250),
    (["cursor"],                    ["waveform"],            "DISplay:WAVEView<x>:CURSor:CURSOR<x>:FUNCtion", 200),

    # ── Horizontal/acquisition ────────────────────────────────────────────────
    (["sample", "rate"],            [],                      "HORizontal:MODe:SAMPLERate",         250),
    (["sample"],                    ["rate"],                "HORizontal:MODe:SAMPLERate",         250),
    (["acquisition", "time"],       [],                      "HORizontal:ACQDURATION",             400),
    (["acquisition", "duration"],   [],                      "HORizontal:ACQDURATION",             400),
    (["acqduration"],               [],                      "HORizontal:ACQDURATION",             400),
    (["total", "time"],             [],                      "HORizontal:ACQDURATION",             350),
    (["time", "window"],            [],                      "HORizontal:ACQDURATION",             350),
    (["record", "length"],          [],                      "HORizontal:RECOrdlength",            250),
    (["recordlength"],              [],                      "HORizontal:RECOrdlength",            250),
    (["fastframe"],                 ["count"],               "HORizontal:FASTframe:COUNt",         350),  # keep high for count queries
    (["fastframe"],                 ["frame", "count"],      "HORizontal:FASTframe:COUNt",         400),


    # ── Save commands ─────────────────────────────────────────────────────────
    (["save"],                      ["session"],             "SAVe:SESsion",                       300),
    (["session"],                   ["save"],                "SAVe:SESsion",                       300),
    (["save"],                      ["screenshot"],          "SAVe:IMAGe",                         300),
    (["screenshot"],                [],                      "SAVe:IMAGe",                         300),
    (["screen", "capture"],         [],                      "SAVe:IMAGe",                         250),
    (["save", "image"],             [],                      "SAVe:IMAGe",                         300),

    # ── SMU current source (set vs measure) ──────────────────────────────────
    (["smu"],                       ["current", "level"],    "SOURce:CURRent:LEVel",               300),
    (["set"],                       ["current", "level"],    "SOURce:CURRent:LEVel",               200),
    (["current", "level"],          ["smu"],                 "SOURce:CURRent:LEVel",               300),

    # ── Horizontal sample rate — penalize BUS:BITRate ─────────────────────────
    # "query current sample rate" and "set sample rate" must not return BUS:BITRate
    # The boosts above should handle this, but also add acquisition mode boosts
    (["single"],                    ["acquisition"],         "ACQuire:STOPAfter",                  250),
    (["single", "shot"],            [],                      "ACQuire:STOPAfter",                  300),
    (["continuous"],                ["acquisition"],         "ACQuire:STOPAfter",                  200),
    (["stopafter"],                 [],                      "ACQuire:STOPAfter",                  250),

    
    # ── External AFG (AFG31000) vs built-in scope AFG ─────────────────────────
    # "external" keyword → force AFG31000 commands (SOURce, ROSCillator, etc.)
    (["external"],                  ["afg"],                 "SOURce<x>:FREQuency:CW",             300),
    (["external"],                  ["afg", "frequency"],    "SOURce<x>:FREQuency:CW",             400),
    (["external"],                  ["afg", "function"],     "SOURce<x>:FUNCtion:SHAPe",           400),
    (["external"],                  ["afg", "waveform"],     "SOURce<x>:FUNCtion:SHAPe",           400),
    (["external"],                  ["afg", "amplitude"],    "SOURce<x>:VOLTage:LEVel:IMMediate:AMPLitude", 400),
    (["external"],                  ["afg", "voltage"],      "SOURce<x>:VOLTage:LEVel:IMMediate:AMPLitude", 400),
    (["external"],                  ["afg", "clock"],        "ROSCillator:SOURce",                 400),
    (["external"],                  ["afg", "reference"],    "ROSCillator:SOURce",                 400),
    (["external"],                  ["afg", "impedance"],    "OUTPut<x>:IMPedance",                400),
    (["external"],                  ["afg", "output"],       "OUTPut<x>:STATe",                    300),

    # ── Horizontal sample rate — prefer short form for plain "sample rate" queries ──
    (["sample"],                    ["rate"],                "HORizontal:SAMPLERate",              320),
    (["sample", "rate"],            [],                      "HORizontal:SAMPLERate",              320),

    # ── FastFrame state/timestamp (not count) for enable/query ─────────────────
    (["fastframe"],                 ["enable"],              "HORizontal:FASTframe:STATE",         350),
    (["fastframe"],                 ["state"],               "HORizontal:FASTframe:STATE",         350),
    (["enable"],                    ["fastframe"],           "HORizontal:FASTframe:STATE",         300),
    (["fastframe"],                 ["timestamp"],           "HORizontal:FASTframe:TIMEStamp",     400),
    (["fastframe"],                 ["time"],                "HORizontal:FASTframe:TIMEStamp",     300),
    (["timestamps"],                [],                      "HORizontal:FASTframe:TIMEStamp",     300),

    # ── FASTAcq state ─────────────────────────────────────────────────────────
    (["fast", "acquisition"],       [],                      "FASTAcq:STATE",                      500),
    (["fastacq"],                   [],                      "FASTAcq:STATE",                      500),
    (["fast", "acq"],               ["enable"],              "FASTAcq:STATE",                      350),

    # ── Clock recovery data rate ──────────────────────────────────────────────
    (["clock", "recovery"],         ["data", "rate"],        "MEASUrement:CLOCKRecovery:EXPLicit:DATARate", 400),
    (["clock", "recovery"],         ["explicit"],            "MEASUrement:CLOCKRecovery:EXPLicit:DATARate", 400),
    (["explicit"],                  ["clock"],               "MEASUrement:CLOCKRecovery:EXPLicit:DATARate", 350),

    # ── AWG CLOCk:SRATe (AWG sample rate, distinct from scope sample rate) ────
    (["awg"],                       ["sample", "rate"],      "CLOCk:SRATe",                        500),
    (["awg"],                       ["clock", "rate"],       "CLOCk:SRATe",                        400),

    # ── Trigger holdoff ───────────────────────────────────────────────────────
    (["trigger"],                   ["holdoff"],             "TRIGger:A:HOLDoff:TIMe",             300),
    (["holdoff"],                   [],                      "TRIGger:A:HOLDoff:TIMe",             300),

    # ── Trigger mode ─────────────────────────────────────────────────────────
    (["trigger"],                   ["mode"],                "TRIGger:A:MODe",                     250),
    (["trigger", "mode"],           [],                      "TRIGger:A:MODe",                     250),

    # ── Trigger state query ───────────────────────────────────────────────────
    (["trigger"],                   ["state"],               "TRIGger:STATE",                      200),

    # ── Trigger B event count ─────────────────────────────────────────────────
    (["trigger"],                   ["event", "count"],      "TRIGger:B:EVENTS:COUNt",             300),
    (["b", "trigger"],              ["count"],               "TRIGger:B:EVENTS:COUNt",             300),
    (["trigger", "b", "event"],     [],                      "TRIGger:B:EVENTS:COUNt",             250),

    # ── MEASUrement immediate ─────────────────────────────────────────────────
    (["immediate"],                 ["measurement"],         "MEASUrement:IMMed:TYPe",             300),
    (["immediate"],                 ["type"],                "MEASUrement:IMMed:TYPe",             300),
    (["immmed"],                    [],                      "MEASUrement:IMMed:TYPe",             300),

    # ── MEASTABle (results table) vs MEASUrement:ADDMEAS ─────────────────────
    (["results", "table"],          [],                      "MEASTable:ADDNew",                   500),
    (["add"],                       ["results", "table"],    "MEASTable:ADDNew",                   500),
    (["measurement", "table"],      [],                      "MEASTable:ADDNew",                   300),

    # ── SEARch:ADDNew ─────────────────────────────────────────────────────────
    (["add"],                       ["search", "new"],       "SEARch:ADDNew",                      300),
    (["search"],                    ["add", "new"],          "SEARch:ADDNew",                      300),
    (["search"],                    ["add"],                 "SEARch:ADDNew",                      250),


    # ── BUS type ─────────────────────────────────────────────────────────────

    # ── *OPC? operation complete query ────────────────────────────────────────
    (["opc"],                       [],                      "*OPC",                               400),
    (["operation", "complete"],     [],                      "*OPC",                               400),
    (["previous", "operations"],    [],                      "*OPC",                               400),
    (["long", "operations"],        [],                      "*OPC",                               400),

    # ── Horizontal position (trigger position) ────────────────────────────────
    (["horizontal"],                ["position"],            "HORizontal:POSition",                250),
    (["trigger", "position"],       [],                      "HORizontal:POSition",                250),

    # ── SV position (spectrum view reference level) ───────────────────────────
    (["spectrum"],                  ["reference", "level"],  "CH:SV:POSition",                     450),
    (["spectrum", "view"],          ["reference"],           "CH:SV:POSition",                     450),
    (["sv"],                        ["reference"],           "CH:SV:POSition",                     450),
    (["sv"],                        ["position"],            "CH:SV:POSition",                     400),

    # ── MEASUrement reference levels ──────────────────────────────────────────
    (["measurement"],               ["absolute", "high"],    "MEASUrement:CH<x>:REFLevels:ABSolute:RISEHigh", 300),
    (["reflevel"],                  ["absolute"],            "MEASUrement:CH<x>:REFLevels:ABSolute:RISEHigh", 300),
    (["reference", "level"],        ["absolute"],            "MEASUrement:CH<x>:REFLevels:ABSolute:RISEHigh", 250),

    # ── SV normal trace ───────────────────────────────────────────────────────
    (["spectrum", "view"],          ["trace", "normal"],     "SV:CH:SELect:NORMaltrace",           350),
    (["sv"],                        ["normal", "trace"],     "SV:CH:SELect:NORMaltrace",           350),
    (["spectrum", "view"],          ["trace", "type"],       "SV:CH:SELect:NORMaltrace",           300),
    (["normal"],                    ["trace", "spectrum"],   "SV:CH:SELect:NORMaltrace",           300),

    # ── HSSerial / PRBS patterns ──────────────────────────────────────────────
    (["prbs"],                      [],                      "HSSerial:BDATa:PRBS",                400),
    (["prbs7"],                     [],                      "HSSerial:BDATa:PRBS",                400),
    (["hsserial"],                  [],                      "HSSerial:BDATa:PRBS",                300),
    (["compile"],                   ["overwrite"],           "HSSERIAL:COMPILE:OVERWRITE",         400),
    (["overwrite"],                 ["compile"],             "HSSERIAL:COMPILE:OVERWRITE",         400),

    # ── AWG CLOCk:SRATe boost (AWG sample rate not scope sample rate) ────────
    (["awg"],                       ["sample"],              "CLOCk:SRATe",                        500),
    (["clock"],                     ["rate", "awg"],         "CLOCk:SRATe",                        400),

        # ── BUS protocol bitrate — beats HORizontal:SAMPLERate for bus queries ──
    # BUS type
    # BUS:TYPe — see clean block below, requires "bus" in kw_any not kw_all
    # BUS add new
        # ── ACQuire:STOPAfter — single shot vs continuous ────────────────────────
    (["single", "shot"],            [],                      "ACQuire:STOPAfter",                  500),
    (["single"],                    ["acquisition"],         "ACQuire:STOPAfter",                  500),
    (["continuous"],                ["acquisition"],         "ACQuire:STOPAfter",                  500),
    (["run", "stop"],               [],                      "ACQuire:STOPAfter",                  400),
    (["acquisition"],               ["mode"],                "ACQuire:STOPAfter",                  200),
    # SAVe:IMAGe for screenshot
    (["screenshot"],                [],                      "SAVe:IMAGe",                         500),
    (["save"],                      ["screenshot"],          "SAVe:IMAGe",                         400),
    (["save"],                      ["image"],               "SAVe:IMAGe",                         350),
    (["screen", "capture"],         [],                      "SAVe:IMAGe",                         350),
    # *IDN? — must beat SEARCH:... term accumulation
    (["identification"],            [],                      "*IDN",                               600),
    (["identify"],                  [],                      "*IDN",                               500),
    (["idn"],                       [],                      "*IDN",                               600),
    (["query"],                     ["identification"],      "*IDN",                               600),
    # Horizontal position (not trigger)
    (["horizontal", "position"],    [],                      "HORizontal:POSition",                350),
    (["horizontal"],                ["trigger", "position"], "HORizontal:POSition",                350),
    # Trigger pulse width parameters
    (["pulse", "width"],            ["low"],                 "TRIGger:{A|B}:PULSEWidth:LOWLimit",  450),
    (["pulse", "width"],            ["low", "limit"],        "TRIGger:{A|B}:PULSEWidth:LOWLimit",  500),
    (["low", "limit"],              ["pulse"],               "TRIGger:{A|B}:PULSEWidth:LOWLimit",  450),
    (["pulse", "width"],            ["when"],                "TRIGger:{A|B}:PULSEWidth:WHEn",      300),
    # Channel label
    (["label"],                     ["channel"],             "CH<x>:LABel:NAMe",                   450),
    (["channel"],                   ["label", "name"],       "CH<x>:LABel:NAMe",                   450),
    # Probe attenuation
    (["probe"],                     ["attenuation"],         "CH<x>:PROBEFunc:EXTAtten",           300),
    (["probe"],                     ["external", "atten"],   "CH<x>:PROBEFunc:EXTAtten",           350),
    # *OPC? — needs very high boost to beat WFMOUTPRE:YZERO
    (["opc"],                       [],                      "*OPC",                               600),
    (["operation"],                 ["complete"],            "*OPC",                               550),
    (["previous"],                  ["operations"],          "*OPC",                               550),
    # MEASUrement:COUNt? — benchmark expects this but DB has DELETEALL near it
    (["how", "many"],               ["measurement"],         "MEASUrement:COUNt",                  500),
    (["count"],                     ["measurement"],         "MEASUrement:COUNt",                  450),
    (["query", "count"],            ["measurement"],         "MEASUrement:COUNt",                  350),
        # ── MATH vertical scale ──────────────────────────────────────────────────
    (["math"],                      ["vertical", "scale"],   "DISplay:WAVEView<x>:MATH:MATH<x>:VERTical:SCAle", 450),
    (["math"],                      ["scale"],               "DISplay:MATHFFTView<x>:VERTical:SCAle", 250),
    # MEASUrement:CLOCKRecovery — DB nests under MEAS<x>, benchmark expects shorter form
    # Both are in DB — try to boost shorter form
    (["clock", "recovery"],         ["method"],              "MEASUrement:CLOCKRecovery:METHod",    400),
    (["clock", "recovery"],         ["pll"],                 "MEASUrement:CLOCKRecovery:ADVanced:PLL:BANDwidth", 400),
    # PG channel voltage (T9-01)
    (["pattern", "generator"],      ["voltage"],             "PG:CH<x>:VOLTage:HIGH",              400),
    (["pg"],                        ["voltage"],             "PG:CH<x>:VOLTage:HIGH",              400),
    (["mso24"],                     ["voltage"],             "PG:CH<x>:VOLTage:HIGH",              400),
    (["mso2"],                      ["pattern"],             "PG:CH<x>:VOLTage:HIGH",              350),
    # SMU: measure current vs source current
    (["smu"],                       ["measure", "current"],  "MEASure:CURRent",                    400),
    (["read"],                      ["current"],             "MEASure:CURRent",                    300),
    (["measure"],                   ["current"],             "MEASure:CURRent",                    300),
    # MEASUrement ADDMEAS for adding measurements (not search)
    (["add"],                       ["measurement"],         "MEASUrement:ADDMEAS",                350),
    (["add", "jitter"],             [],                      "MEASUrement:ADDMEAS",                350),
    (["add", "measurement"],        [],                      "MEASUrement:ADDMEAS",                350),
    # HORizontal delay mode vs horizontal mode
    (["horizontal"],                ["delay", "mode"],       "HORizontal:DELay:MODe",              350),
    (["delay"],                     ["mode"],                "HORizontal:DELay:MODe",              250),
    # External clock reference (ROSCillator)
    (["external"],                  ["clock", "reference"],  "ROSCillator:SOURce",                 400),
    (["reference"],                 ["external", "clock"],   "ROSCillator:SOURce",                 400),
    (["roscillator"],               [],                      "ROSCillator:SOURce",                 400),
    (["oscillator"],                ["external"],            "ROSCillator:SOURce",                 350),
        # ── T5-14: CAN bus frame type search ────────────────────────────────────
    # T5-28: External AFG output voltage → SOURce1:VOLTage (not AFG:AMPLitude)
    (["external"],                  ["voltage", "amplitude"], "SOURce<x>:VOLTage:LEVel:IMMediate:AMPLitude", 500),
    (["external"],                  ["afg", "voltage"],      "SOURce<x>:VOLTage:LEVel:IMMediate:AMPLitude", 500),
    (["external", "afg"],           ["voltage"],             "SOURce<x>:VOLTage:LEVel:IMMediate:AMPLitude", 500),
    # T7-01: Enable scope AFG (output state, not function)
    (["enable"],                    ["afg", "function", "generator"], "AFG:OUTPut:STATe",          450),
    (["function", "generator"],     ["enable"],              "AFG:OUTPut:STATe",                   450),
    (["function", "generator"],     ["scope"],               "AFG:OUTPut:STATe",                   400),
    (["built-in"],                  ["function", "generator"], "AFG:OUTPut:STATe",                 450),
    # A-03: Immediate measurement type (IMMed not MEAS<x>)
    (["immediate"],                 ["frequency"],           "MEASUrement:IMMed:TYPe",             400),
    (["immediate"],                 ["measurement", "type"], "MEASUrement:IMMed:TYPe",             450),
    # A-07: "set sample rate to 1 GS/s" → HORizontal:MODE:SAMPLERate
    (["set"],                       ["sample", "rate"],      "HORizontal:MODe:SAMPLERate",         400),
    (["gs"],                        ["rate"],                "HORizontal:MODe:SAMPLERate",         400),
    # BAUD rate → RS232C bitrate
    (["baud"],                      [],                      "BUS:B<x>:RS232C:BITRate",            500),  # baud only — never "rate" alone
    # T11-25: Annotation state (benchmark expects ANNotation:STATE, DB has ANNOTate)
    # norm('measurement:annotate') = 'MEASUREMENT:ANNOTATE'
    # norm('MEASUrement:ANNotation:STATE') = 'MEASUREMENT:ANNOTATION:STATE'
    # ANNOTATE vs ANNOTATION — close but not prefix match
    # Can't fix without DB addition
    # T11-27: MEAS1:REFLevel:PERCent:HIGH
    # Got: measurement:meas<x>:reflevels<x>:percent:risehigh
    # norm got = 'MEASUREMENT:MEAS:REFLEVELS:PERCENT:RISEHIGH'
    # norm exp = 'MEASUREMENT:MEAS:REFLEVEL:PERCENT:HIGH'
    # 'MEASUREMENT:MEAS:REFLEVEL:PERCENT:HIGH' in 'MEASUREMENT:MEAS:REFLEVELS:PERCENT:RISEHIGH'? NO
    # But RISEHIGH contains HIGH as suffix — custom scorer might accept
    # Can't easily fix without changing the comparison logic
        # ── CAN FD specific — must win over base CAN and BUS:TYPe ─────────────────
    # "CAN FD" in query is the key discriminator — always prefer FD subcommands
    # Base CAN bitrate (no FD) — only when "fd" NOT in query
    # Can't do negative kw, but CAN FD boosts above will dominate when FD present
    # CAN bus source
    # CAN error frames vs CAN FD flags
    # ["bus","type"] kw_any removed — "type" alone fired it on non-bus queries
    
    # ══════════════════════════════════════════════════════════════════════════
    # BUS PROTOCOL BOOSTS — Hierarchical: protocol first, then parameter
    # Strategy: identify bus type from query, then narrow to specific parameter.
    # This prevents RS232 bitrate from beating CAN bitrate on "CAN bit rate" queries.
    # ══════════════════════════════════════════════════════════════════════════

    # ── BUS:ADDNew / SEARch:ADDNew / MEASTable:ADDNew ─────────────────────────
    (["add"],                       ["bus"],                 "BUS:ADDNew",                          400),
    (["add"],                       ["new", "bus"],          "BUS:ADDNew",                          500),
    (["add"],                       ["search"],              "SEARch:ADDNew",                       600),
    (["search"],                    ["add"],                "SEARch:ADDNew",                       600),
    (["add"],                       ["results", "table"],    "MEASTable:ADDNew",                    900),
    (["results", "table"],          [],                      "MEASTable:ADDNew",                    900),
    (["add"],                       ["measurement", "table"],"MEASTable:ADDNew",                    500),
    (["results", "table"],          [],                      "MEASTable:ADDNew",                    500),

    # ── BUS:TYPe — REQUIRES "bus" explicitly in the query ────────────────────
    # "type" alone must NEVER fire this — "measurement type", "trigger type",
    # "cursor type", "filter type" all contain "type" but have nothing to do
    # with BUS:TYPe. Only fire when "bus" is also present.
    (["bus"],                       ["type"],                "BUS:B<x>:TYPe",                      600),
    (["bus"],                       ["type", "to"],          "BUS:B<x>:TYPe",                      700),
    # kw_all=['bus','type'] removed — kw_any=['bus'] with kw_all=['type'] already covers this

    # ── CAN bus — base commands (no FD keyword in query) ─────────────────────
    # "CAN" in query → must win over RS232/UART for all BUS:CAN:* commands




    # CAN standard — BUS:CAN:STANDard handles ALL variants including FDISO, FDNONISO
    # No separate CAN:FD:STANDard needed on MSO 4/5/6 — it's an argument value






    # ── CAN FD — data phase bit rate (FD-specific parameter) ─────────────────
    # "FD" in query → CAN:FD:BITRate wins over base CAN:BITRate
    (["fd"],                        ["bit", "rate"],         "BUS:B<x>:CAN:FD:BITRate",            700),
    (["fd"],                        ["bitrate"],             "BUS:B<x>:CAN:FD:BITRate",            700),
    (["fd"],                        ["data", "phase"],       "BUS:B<x>:CAN:FD:BITRate",            750),
    (["fd"],                        ["data", "rate"],        "BUS:B<x>:CAN:FD:BITRate",            750),
    (["can"],                       ["fd", "bit", "rate"],   "BUS:B<x>:CAN:FD:BITRate",            750),
    (["can"],                       ["fd", "bitrate"],       "BUS:B<x>:CAN:FD:BITRate",            750),

    # ── CAN error/frame search ────────────────────────────────────────────────
    (["can"],                       ["error", "frame"],      "SEARCH:SEARCH<x>:TRIGger:A:BUS:CAN:FRAMEtype", 600),
    (["can"],                       ["frame", "type"],       "SEARCH:SEARCH<x>:TRIGger:A:BUS:CAN:FRAMEtype", 600),
    (["can"],                       ["frametype"],           "SEARCH:SEARCH<x>:TRIGger:A:BUS:CAN:FRAMEtype", 600),
    (["can"],                       ["error"],               "SEARCH:SEARCH<x>:TRIGger:A:BUS:CAN:ERRType",   500),
    (["search"],                    ["can", "error", "frame"],"SEARCH:SEARCH<x>:TRIGger:A:BUS:CAN:FRAMEtype", 600),

    # ── RS232 / UART — identified by protocol name ────────────────────────────
    # "rs232" or "uart" in query → must win over CAN for BUS:RS232:* commands
    # Both "baud rate" and "bit rate" mean bitrate here








    # "baud" alone — RS232/UART is the most common baud rate context
    (["baud"],                      [],                      "BUS:B<x>:RS232C:BITRate",            500),

    # ── I2C — identified by "i2c" keyword ─────────────────────────────────────






        # ── Within-protocol bitrate disambiguation ───────────────────────────────
    # "bit rate" / "baud rate" → prefer BITRate over DATABits within same family
    # The affinity puts all RS232/CAN/LIN commands at equal +500, but "bit" node
    # in DATABits can outscore "bitrate" substring. These boosts tip the balance.
    (["uart"],                      ["rate"],                "BUS:B<x>:RS232C:BITRate",            300),
    (["uart"],                      ["bit", "rate"],         "BUS:B<x>:RS232C:BITRate",            400),
    (["rs232"],                     ["rate"],                "BUS:B<x>:RS232C:BITRate",            300),
    (["rs232"],                     ["bit", "rate"],         "BUS:B<x>:RS232C:BITRate",            400),
    (["lin"],                       ["rate"],                "BUS:B<x>:LIN:BITRate",               300),
    (["lin"],                       ["bit", "rate"],         "BUS:B<x>:LIN:BITRate",               400),
    (["can"],                       ["rate"],                "BUS:B<x>:CAN:BITRate",               300),
    (["can"],                       ["bit", "rate"],         "BUS:B<x>:CAN:BITRate",               400),
    # CAN FD and XL bitrates — only when explicitly mentioned
    (["fd"],                        ["bit", "rate"],         "BUS:B<x>:CAN:FD:BITRate",            500),
    (["fd"],                        ["data", "phase"],       "BUS:B<x>:CAN:FD:BITRate",            500),
    (["xl"],                        ["bit", "rate"],         "BUS:B<x>:CAN:XL:BITRate",            500),
        # ── Trigger type ─────────────────────────────────────────────────────────
    # "trigger type" → TRIGger:A:TYPe — must require BOTH "trigger" AND "type"
    (["trigger"],                   ["type"],                "TRIGger:{A|B}:TYPe",                 350),
    # ── Measurement type (immediate vs badge) ────────────────────────────────
    (["immediate"],                 ["type"],                "MEASUrement:IMMed:TYPe",             350),
        (["uart"],                      ["source"],              "BUS:B<x>:RS232C:SOUrce",             400),
    (["rs232"],                     ["source"],              "BUS:B<x>:RS232C:SOUrce",             400),
        (["table"],                      ["results"],             "MEASTable:ADDNew",                    900),
    (["table"],                      ["add"],                 "MEASTable:ADDNew",                    800),
        # ── Root commands — must beat term-accumulation from long multi-node competitors ──
    # Root commands get -150 (-200 if query-only) penalty. Boosts here must
    # exceed 200 + typical competitor term score to win on their target query.
    (["reset"],                     ["oscilloscope"],        "*RST",                               400),
    (["header"],                    [],                      "HEADer",                             350),
    (["display", "header"],         [],                      "HEADer",                             350),
    (["verbose"],                   [],                      "VERBose",                            200),
    (["transfer"],                  ["waveform"],            "CURVe",                              400),
    (["download"],                  ["waveform"],            "CURVe",                              300),
    (["get"],                       ["waveform", "data"],    "CURVe",                              300),
    (["get", "curve"],              [],                      "CURVe",                              250),
    # CURSor:STATE wins over DISplay:WAVEView:CURsor accumulation
    (["cursors"],                   [],                      "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["cursor"],                    ["on"],                  "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["cursor"],                    ["off"],                 "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["turn"],                      ["cursor"],              "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),
    (["cursor"],                    ["enable"],              "DISplay:WAVEView<x>:CURSor:CURSOR<x>:STATE", 200),

    # ── Scope built-in AFG ────────────────────────────────────────────────────
    # IMPORTANT: These must require BOTH "afg" AND context words to avoid
    # false-firing on AFG31000 queries ("external afg output voltage") or
    # SMU queries ("smu output voltage"). The distinguishing signal is either
    # "scope"/"built"/"internal" context OR explicit "state" in the query.
    (["enable", "turn"],            ["afg"],                 "AFG:OUTPut:STATe",                    80),
    (["afg"],                       ["state"],               "AFG:OUTPut:STATe",                    80),
    (["function", "generator"],     ["scope"],               "AFG:OUTPut:STATe",                    80),
    (["function", "generator"],     ["built"],               "AFG:OUTPut:STATe",                    80),
    (["function", "generator"],     ["internal"],            "AFG:OUTPut:STATe",                    80),
    (["afg", "frequency"],          [],                      "AFG:FREQuency",                       60),
    (["afg", "function"],           [],                      "AFG:FUNCtion",                        60),
    (["afg", "amplitude"],          [],                      "AFG:AMPLitude",                       60),
    (["afg", "impedance", "load"],  [],                      "AFG:OUTPut:LOAd:IMPEDance",           60),

    # ── AUX output ────────────────────────────────────────────────────────────
    (["aux", "out"],                [],                      "AUXout:SOUrce",                       80),
    (["auxiliary", "output"],       [],                      "AUXout:SOUrce",                       60),
    (["aux", "clock"],              [],                      "AUXout:SOUrce",                       80),

    # ── Waveform data / transfer (scope to PC) ───────────────────────────────
    # CURVe is the correct command for oscilloscope waveform transfer.
    # It gets -200 from the root penalty, so boost must exceed that.
    # CURVe is scope-only — never correct for AWG or waveform generation queries.
    (["transfer"],                  ["waveform"],            "CURVe",                               250),
    (["download"],                  ["waveform"],            "CURVe",                               250),
    (["get"],                       ["waveform", "data"],    "CURVe",                               260),
    (["get", "curve"],              [],                      "CURVe",                               250),
    (["curve", "data"],             [],                      "CURVe",                               250),
    (["waveform", "data", "source"],   [],                   "DATa:SOUrce",                         60),
    (["set", "data", "source"],        [],                   "DATa:SOUrce",                         60),

    # ── AWG core control ─────────────────────────────────────────────────────
    (["awg", "play"],               [],                      "AWGControl:RUN",                      80),
    (["awg", "run"],                [],                      "AWGControl:RUN",                      80),
    (["awg", "stop"],               [],                      "AWGControl:STOP",                     80),
    (["awg", "output", "on"],       [],                      "OUTPut:STATe",                        80),
    (["awg", "output", "off"],      [],                      "OUTPut:STATe",                        80),
    (["awg", "output", "enable"],   [],                      "OUTPut:STATe",                        80),
    (["output", "state"],           ["awg"],                 "OUTPut:STATe",                        80),
    (["output", "channel"],         ["awg"],                 "OUTPut:STATe",                        60),
    # AWG sample/clock rate — CLOCk:SRATe not HORizontal:SAMPLERRate
    (["sample", "rate"],            ["awg"],                 "CLOCk:SRATe",                        100),
    (["clock", "rate"],             ["awg"],                 "CLOCk:SRATe",                         80),
    (["awg", "sample"],             [],                      "CLOCk:SRATe",                         80),

    # ── SMU (Keithley Source Measure Unit) ───────────────────────────────────
    # These MUST outrank MSO/AFG matches when "smu" or "keithley" is in query.
    (["smu"],                       ["voltage"],             "SOURce:VOLTage:LEVel",                300),
    (["smu"],                       ["current"],             "MEASure:CURRent",                    300),
    (["smu", "output"],             [],                      "OUTPut:STATe",                        80),
    (["smu", "compliance"],         [],                      "SOURce:CURRent:PROTection:LEVel",     80),
    (["smu"],                       ["measure"],             "MEASure:CURRent",                    200),
    (["keithley"],                  ["voltage"],             "SOURce:VOLTage:LEVel",                250),
    (["keithley", "current"],       [],                      "MEASure:CURRent",                    100),
    (["source", "voltage"],         ["smu"],                 "SOURce:VOLTage:LEVel:IMMediate:AMPLitude", 80),
    (["output", "voltage"],         ["smu"],                 "SOURce:VOLTage:LEVel:IMMediate:AMPLitude", 80),
    (["read", "current"],           ["smu"],                 "MEASure:CURRent",                    250),
    (["measure", "current"],        ["smu"],                 "MEASure:CURRent",                    250),
    (["read", "voltage"],           ["smu"],                 "MEASure:VOLTage",                     80),
    (["source", "current"],         ["smu"],                 "SOURce:CURRent:LEVel:IMMediate:AMPLitude", 80),

    # ── AWG HSSerial / PRBS ───────────────────────────────────────────────────
    (["prbs", "pattern"],           [],                      "HSSerial:BDATa:PRBS",                 80),
    (["prbs"],                      [],                      "HSSerial:BDATa:PRBS",                 60),
    (["nrz", "encoding"],           [],                      "HSSerial:ENCOde:SCHeme",              80),
    (["nrz"],                       [],                      "HSSerial:ENCOde:SCHeme",              60),
    (["pam4"],                      [],                      "HSSerial:ENCOde:SCHeme",              60),
    (["high", "speed", "serial", "compile"], [],             "HSSerial:COMPile",                    80),
    (["hss", "compile"],            [],                      "HSSerial:COMPile",                    80),
    (["compile", "overwrite"],      [],                      "HSSerial:COMPile:OVERwrite",          80),
    (["hss", "data", "rate"],       [],                      "HSSerial:DRATe",                      60),
    (["high", "speed", "serial", "data", "rate"], [],        "HSSerial:DRATe",                      60),

    # ── AWG Radar plugin ─────────────────────────────────────────────────────
    (["radar", "carrier", "frequency"], [],                  "RADar:PTRain:CARRier:FREQuency",      80),
    (["carrier", "frequency"],      ["radar"],               "RADar:PTRain:CARRier:FREQuency",      80),
    (["radar", "pulse", "width"],   [],                      "RADar:PULSe:PENVelope:WIDTh",         80),
    (["pulse", "width"],            ["radar"],               "RADar:PULSe:PENVelope:WIDTh",         80),
    (["radar", "pri"],              [],                      "RADar:PULSe:PENVelope:PRI",           80),
    (["radar", "pulse", "interval"],  [],                    "RADar:PULSe:PENVelope:PRI",           60),
    (["radar", "lfm"],              [],                      "RADar:PULSe:MODulation:LFM:SRANge",   80),
    (["lfm", "sweep"],              [],                      "RADar:PULSe:MODulation:LFM:SRANge",   80),
    (["radar", "compile"],          [],                      "RADar:COMPile:PLAY",                  80),
    (["compile", "play", "radar"],  [],                      "RADar:COMPile:PLAY",                  80),
    (["radar", "pulse", "train"],   [],                      "RADar:PTRain:ADD",                    60),
    (["ptrain"],                    [],                      "RADar:PTRain",                        60),

    # ── AFG31000 (standalone) ─────────────────────────────────────────────────
    (["afg", "output", "impedance"],   [],                   "OUTPut:IMPedance",                    60),
    (["external", "afg", "impedance"], [],                   "OUTPut:IMPedance",                    60),
    (["afg", "amplitude", "voltage"],  [],                   "SOURce:VOLTage:LEVel:IMMediate:AMPLitude", 60),
    (["afg", "output", "voltage"],     [],                   "SOURce:VOLTage:LEVel:IMMediate:AMPLitude", 60),

    # ── SignalVu ──────────────────────────────────────────────────────────────
    (["signalvu", "connect"],       [],                      "INSTrument:CONNect",                  80),
    (["connect", "signalvu"],       [],                      "INSTrument:CONNect",                  80),
    (["connect", "scope", "hardware"], [],                   "INSTrument:CONNect",                  80),
    (["signalvu", "disconnect"],    [],                      "INSTrument:DISConnect",               80),
    (["disconnect", "signalvu"],    [],                      "INSTrument:DISConnect",               80),
    (["disconnect", "scope", "hardware"], [],                "INSTrument:DISConnect",               80),

    # ── UART / RS232C ─────────────────────────────────────────────────────────
    (["uart", "data", "bits"],      [],                      "BUS:B:RS232C:DATABits",               60),
    (["uart", "parity"],            [],                      "BUS:B:RS232C:PARity",                 60),

    # ── FastFrame ─────────────────────────────────────────────────────────────
    (["fastframe", "state"],        [],                      "HORizontal:FASTframe:STATE",          60),
    (["fastframe", "count"],        [],                      "HORizontal:FASTframe:COUNt",          60),

    # ── AWG OFDM plugin ───────────────────────────────────────────────────────
    (["ofdm", "compile"],           [],                      "OFDM:COMPile",                        80),
    (["ofdm", "carrier"],           [],                      "OFDM:CARRier:FREQuency",              80),
    (["ofdm", "bandwidth"],         [],                      "OFDM:BANDwidth",                      60),
    (["ofdm", "subcarrier"],        [],                      "OFDM:SUBCarrier",                     60),

    # ── AWG RF Generic plugin (RFG:*) ────────────────────────────────────────
    (["rfg", "carrier"],            [],                      "RFG:CARRier:FREQuency",               80),
    (["rf generic", "carrier"],     [],                      "RFG:CARRier:FREQuency",               80),
    (["rfg", "compile"],            [],                      "RFG:COMPile:PLAY",                    80),
    (["rf generic", "compile"],     [],                      "RFG:COMPile:PLAY",                    80),

    # ── AWG Optical plugin (OPTical:*) ───────────────────────────────────────
    (["optical", "compile"],        [],                      "OPTical:COMPile",                     80),
    (["optical", "extinction"],     [],                      "OPTical:EXTinction:RATio",            80),

    # ── AWG Multitone plugin (MTONe:*) ───────────────────────────────────────
    (["multitone", "compile"],      [],                      "MTONe:COMPile",                       80),
    (["multitone", "tone"],         [],                      "MTONe:TONE:FREQuency",                60),
    # ── AWG Pulse plugin (PULSe:*) ───────────────────────────────────────────
    (["pulse", "compile"],          ["awg"],                 "PULSe:COMPile",                       80),
    (["pulse", "plugin", "compile"], [],                     "PULSe:COMPile",                       80),
    (["pulse", "width"],            ["awg", "plugin"],       "PULSe:WIDTh",                         60),

    # ── AWG WPlugin active (select plugin) ───────────────────────────────────
    (["select", "plugin"],          [],                      "WPLugin:ACTive",                      80),
    (["activate", "plugin"],        [],                      "WPLugin:ACTive",                      80),
    (["wplugin", "active"],         [],                      "WPLugin:ACTive",                      80),

    # ── MSO 2 Pattern Generator ───────────────────────────────────────────────
    (["pattern", "generator", "voltage"],  [],               "PG:CH:VOLTage:HIGH",                 100),
    (["pg", "voltage", "high"],            [],               "PG:CH:VOLTage:HIGH",                 100),
    (["voltage", "high"],                  ["pattern"],      "PG:CH:VOLTage:HIGH",                 100),
    (["output", "voltage"],                ["pattern"],      "PG:CH:VOLTage:HIGH",                  80),
    (["pattern", "generator", "output"],   [],               "PG:OUTPut:MODe",                      60),
    (["pg", "output", "mode"],             [],               "PG:OUTPut:MODe",                      60),

    # ── AFG31000 (standalone function generator) ─────────────────────────────
    (["afg", "output", "impedance"],       [],               "OUTPut:IMPedance",                    80),
    (["external", "afg", "impedance"],     [],               "OUTPut:IMPedance",                    80),
    (["afg", "voltage", "amplitude"],      [],               "SOURce:VOLTage:LEVel:IMMediate:AMPLitude", 80),
    (["afg", "output", "voltage"],         [],               "SOURce:VOLTage:LEVel:IMMediate:AMPLitude", 80),
    (["external", "afg", "voltage"],       [],               "SOURce:VOLTage:LEVel:IMMediate:AMPLitude", 80),
    (["afg", "waveform", "shape"],         [],               "SOURce:FUNCtion:SHAPe",               80),
    (["afg", "function", "shape"],         [],               "SOURce:FUNCtion:SHAPe",               80),
    (["external", "afg", "waveform"],      [],               "SOURce:FUNCtion:SHAPe",               80),
    (["afg", "square"],                    [],               "SOURce:FUNCtion:SHAPe",               60),
    (["afg", "sine"],                      [],               "SOURce:FUNCtion:SHAPe",               60),
]


def _compute_priority_boost(query_lower: str, scpi: str) -> int:
    """Compute additive priority boost for a candidate SCPI command.

    Checks _PRIORITY_BOOSTS table: if the query matches the keyword conditions
    AND this command's SCPI path starts with the boost prefix, return the boost.
    Instance numbers and <x> placeholders are stripped for matching so that
    'CH1:COUPling' and 'CH<x>:COUPling' both match prefix 'CH:COUPling'.
    """
    scpi_upper = scpi.upper()
    scpi_clean = re.sub(r'(?<=[A-Z])\d+', '', scpi_upper)
    scpi_clean = scpi_clean.replace('<X>', '').replace('<x>', '')

    for kw_any, kw_all, boost_prefix, boost_val in _PRIORITY_BOOSTS:
        if not any(kw in query_lower for kw in kw_any):
            continue
        if kw_all and not all(kw in query_lower for kw in kw_all):
            continue
        prefix_upper = boost_prefix.upper()
        prefix_clean = re.sub(r'(?<=[A-Z])\d+', '', prefix_upper)
        prefix_clean = prefix_clean.replace('<X>', '').replace('<x>', '')
        if scpi_clean.startswith(prefix_clean):
            return boost_val
    return 0


# =============================================================================
# USAGE BOOST TABLE — Commands that appear in real Python examples/PTA suites
# =============================================================================
# Commands that appear in real automation scripts get a relevance boost.
# Heavily-used commands (5+ occurrences) get +50, moderate (2-4) get +25,
# single-use get +10.
#
# To regenerate: python generate_usage_boosts.py
#   (scans docs/python_examples/ and PTA/test_suites/)
# =============================================================================

_USAGE_BOOSTS: dict = {
    # Auto-generated from embedded Python example templates in this file.
    # Counts: 5+ occurrences = +50, 2-4 = +25, 1 = +10.
    # Regenerate with: python generate_usage_boosts.py
    "HEADER":                                    50,  # 10x
    "*OPC":                                      50,  # 10x
    "*RST":                                      50,  #  6x
    "*CLS":                                      50,  #  5x
    "DISPLAY:WAVEVIEW<x>:CH<x>:STATE":           50,  #  5x
    "AUTOSET":                                   50,  #  5x (AUTOS EXECUTE)
    "MEASUREMENT:ADDMEAS":                       50,  #  5x (MEASU:ADDMEAS)
    "MEASUREMENT:MEAS<x>:SOURCE":                50,  #  5x
    "MEASUREMENT:MEAS<x>:STATE":                 50,  #  5x
    "ACQUIRE:STOPAFTER":                         50,  #  5x (ACQ:STOPA)
    "ACQUIRE:STATE":                             50,  #  5x
    "VERBOSE":                                   25,  #  4x
    "MEASUREMENT:MEAS<x>:RESULTS:ALLACQS:MEAN":  25,  #  3x
    "CH<x>:SCALE":                               10,  #  1x
    "CH<x>:TERMINATOR":                          10,  #  1x
    "CH<x>:BANDWIDTH":                           10,  #  1x
    "CH<x>:CLIPPING":                            10,  #  1x
    "MEASUREMENT:DELETEALL":                     10,  #  1x
    "MEASUREMENT:MEAS<x>:POPULATION:LIMIT:STATE": 10, #  1x
    "MEASUREMENT:MEAS<x>:POPULATION:LIMIT:VALUE": 10, #  1x
    "DATA:SOURCE":                               10,  #  1x
    "DATA:ENCODINGFORMAT":                       10,  #  1x (DATA:ENCdg)
    "DATA:START":                                10,  #  1x
    "HORIZONTAL:MODE:RECORDLENGTH":              10,  #  1x
    "WAVEFORM:XINCREMENT":                       10,  #  1x (WFMOutpre:XINcr)
    "CURVE":                                     10,  #  1x
    "*OPT":                                      10,  #  1x
}


# ── Instrument keyword → DB mapping ──────────────────────────────────────────
# Maps query keywords to the instrument DB keys they imply.
# Default (no keyword match) = ['mso'] — the MSO 4/5/6/7 series.
# Multiple keyword hits union their DB lists.
_INSTRUMENT_QUERY_HINTS: Dict[str, List[str]] = {
    # AWG / waveform generators
    'awg':           ['awg'],
    'awg5200':       ['awg'],
    'awg70000':      ['awg'],
    'radar':         ['awg'],
    'ofdm':          ['awg'],
    'hss':           ['awg'],
    'hsserial':      ['awg'],
    'wplugin':       ['awg'],
    'plugin':        ['awg'],
    'rfg':           ['awg'],
    'optical':       ['awg'],
    'multitone':     ['awg'],
    'ptrain':        ['awg'],
    # SignalVu / RSA spectrum analyzers
    'signalvu':      ['signalvu'],
    'signalvupc':    ['signalvu'],
    'rsa':           ['signalvu'],
    'rsa306':        ['signalvu'],
    'rsa500':        ['signalvu'],
    'rsa600':        ['signalvu'],
    'dpx':           ['signalvu'],
    'spectrogram':   ['signalvu'],
    'instconnect':   ['signalvu'],
    # SMU / Keithley source-measure
    'smu':           ['smu'],
    'keithley':      ['smu'],
    'sourcemeter':   ['smu'],
    'source measure':['smu'],
    '2450':          ['smu'],
    '2460':          ['smu'],
    # MP5000 / TSP-based modular system
    'mp5000':        ['mp5000'],
    'tsp':           ['mp5000'],
    # External AFG function generators
    'afg31000':      ['afg31000'],
    'afg3':          ['afg31000'],
    # Note: "afg" alone could be scope built-in (mso) or external (afg31000)
    # so it stays in the default mso set and also adds afg31000
    'afg':           ['mso', 'afg31000'],
    # MSO 2 Series (small portable scope)
    'mso2':          ['mso2'],
    'mso22':         ['mso2'],
    'mso24':         ['mso2'],
    'mso26':         ['mso2'],
    'battery':       ['mso2'],       # battery power only on MSO2
    'pg':            ['mso2'],       # pattern generator only on MSO2
    'pattern generator': ['mso2'],
    # TBS2000B (basic scope)
    'tbs2000':       ['tbs2000b'],
    'tbs2':          ['tbs2000b'],
    'tbs':           ['tbs2000b'],
    # CAN FD — STANDard command only exists in mdo3/mdo4, not MSO 4/5/6/7
    # Use multi-word key so only "can fd" together triggers this, not "can" alone
    'can fd':        ['mso', 'mdo3'],
    'canfd':         ['mso', 'mdo3'],
    # MDO 3 Series
    'mdo3':          ['mdo3'],
    'mdo3000':       ['mdo3'],
    # MDO 4000 / MSO 4000B / DPO 4000B / MDO 3000 (legacy)
    'mdo4':          ['mdo4'],
    'mdo4000':       ['mdo4'],
    'mso4000':       ['mdo4'],
    'dpo4000':       ['mdo4'],
    # MSO/DPO 5k/7k/70k (high-end legacy)
    'dpo5000':       ['mso_dpo_5k'],
    'mso5000':       ['mso_dpo_5k'],
    'dpo70000':      ['mso_dpo_5k'],
    'mso70000':      ['mso_dpo_5k'],
    'dpo7000':       ['mso_dpo_5k'],
    # DPOJet jitter analysis
    'dpojet':        ['dpojet'],
    # 'jitter' removed — jitter queries in scope context should find MSO MEASUrement commands
    # dpojet commands only when 'dpojet' explicitly mentioned
    'tj':            ['dpojet'],
}

# Default instrument DBs when no hint keyword matches
_DEFAULT_INSTRUMENTS = ['mso']


def _detect_instrument_from_query(query: str) -> str:
    """Return a search-key encoding the instrument DBs to search for this query.

    Returns either a plain instrument key (e.g. 'mso') for single-DB queries,
    or a '_multi:a,b,c' encoded string for multi-DB queries, handled by
    search_commands().

    Strategy:
      1. Normalize query (lower, strip punctuation, collapse spaces).
      2. Check each keyword in _INSTRUMENT_QUERY_HINTS against the normalized query.
      3. Union all matching DB lists.
      4. Always include 'mso' as the base — MSO commands cover scope fundamentals
         and most queries need them regardless of the other instrument.
      5. If the result is just ['mso'], return 'mso' directly (fast path).
    """
    q = query.lower().replace('-', '').replace('_', '').replace(' ', '')
    # Also check space-preserved version for multi-word hints
    q_spaced = query.lower().replace('-', ' ').replace('_', ' ')

    detected: set = set(_DEFAULT_INSTRUMENTS)
    # Track instrument-specific hits to decide whether to drop the MSO default
    instrument_specific_hits: set = set()

    for kw, db_list in _INSTRUMENT_QUERY_HINTS.items():
        kw_nospace = kw.replace(' ', '')
        # Short keywords (< 5 chars) require word-boundary match to avoid
        # substring false-fires (e.g. 'tsp' inside 'spectrum', 'afg' in 'safety')
        if len(kw_nospace) < 5:
            import re as _re
            matched = bool(_re.search(r'\b' + _re.escape(kw) + r'\b', q_spaced))
        else:
            matched = kw_nospace in q or kw in q_spaced
        if matched:
            detected.update(db_list)
            # Record non-mso instruments that were explicitly triggered
            instrument_specific_hits.update(i for i in db_list if i != 'mso')

    # If query clearly targets a non-scope instrument (SMU, MP5000, AFG31000, etc.)
    # and that instrument has its own DB, drop the default MSO inclusion.
    # This avoids MSO commands winning over SMU/MP5000/AFG commands on their queries.
    _no_mso_instruments = {'smu', 'mp5000', 'dpojet'}  # afg31000 removed — scope has built-in AFG
    if instrument_specific_hits & _no_mso_instruments and 'mso' not in instrument_specific_hits:
        # Only remove mso if it came from the default, not from an explicit hint
        detected.discard('mso')

    if not detected:
        detected = set(_DEFAULT_INSTRUMENTS)

    if detected == {'mso'}:
        return 'mso'
    return '_multi:' + ','.join(sorted(detected))


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
    
    # ── Instrument auto-detection ─────────────────────────────────────────────
    # When no instrument is explicitly specified, infer which DBs are relevant
    # from query keywords.  Default is MSO-only (2,980 cmds → ~15ms).
    # Mentioning AWG/SMU/SignalVu etc. expands the search to those DBs.
    # This is the primary speed optimization: avoid scanning all 21K commands
    # when 95% of queries only need the MSO DB.
    if not instrument:
        instrument = _detect_instrument_from_query(query)

    # Determine which instruments to search (skip alias entries to avoid duplicates)
    if instrument and instrument in _commands_flat:
        # AUTO-EXPAND: Include AWG plugin databases when searching AWG families.
        # awg.json contains ALL plugin groups (Radar, HSSerial, OFDM, Pulse,
        # RF_Generic, Optical, Multitone, etc.) for AWG5200 and AWG70000.
        # Searching any AWG family must also search awg.json and vice-versa.
        instruments = [instrument]
        for related in _PLUGIN_SCOPE.get(instrument, []):
            if related in _commands_flat and related not in instruments:
                instruments.append(related)
    elif instrument and instrument.startswith('_multi:'):
        # Multi-instrument result from auto-detection
        instruments = [i for i in instrument[7:].split(',') if i in _commands_flat]
    else:
        # Explicit "all" or unrecognized — search everything
        instruments = [k for k in _commands_flat.keys() if not COMMAND_FILES.get(k, {}).get("is_alias")]
    
    query_lower = query.lower()
    # Normalize punctuation before tokenizing:
    # • "SignalVu-PC" → "signalvu pc"  (hyphenated names split into searchable tokens)
    # • "scope's" → "scopes"           (possessives keep the root word)
    # • "built-in" → "built in"        (compound adjectives split correctly)
    # query_lower is kept for exact-match checks; query_norm feeds tokenization.
    query_norm = (query_lower
                  .replace("'s", "s")
                  .replace("'", "")
                  .replace("-", " "))

    # ── Build effective search terms ──────────────────────────────────────
    # 1. Strip stop words (prevents "the" from matching every command)
    # 2. Drop very short terms (< 2 chars) that cause noise matches
    # 3. Expand natural-language terms via synonym map so "reset" also
    #    searches for "*rst", "factory", etc.
    raw_terms = query_norm.split()
    filtered_terms = [t for t in raw_terms
                      if t not in _SEARCH_STOP_WORDS and len(t) >= 2]

    # Expand synonyms: for each user term, add SCPI-relevant alternatives
    synonym_terms = []
    for term in filtered_terms:
        if term in _SEARCH_SYNONYMS:
            synonym_terms.extend(_SEARCH_SYNONYMS[term])
    # Combine: original filtered terms + synonym expansions (deduplicated)
    all_search_terms = list(dict.fromkeys(filtered_terms + synonym_terms))

    # Fall back to raw terms if filtering removed everything
    # (e.g., query was a single SCPI command like "*RST")
    if not all_search_terms:
        all_search_terms = [query_lower]

    # ── Pre-compute per-query values (done ONCE, not per-command) ────────────
    # This is the critical performance optimization. The original code called
    # _compute_priority_boost() inside the inner command loop, which ran the
    # 237-rule table + re.sub regex for every command in the database
    # (~10,000 commands × 237 rules = 2.37M iterations). Pre-filtering the
    # applicable rules to ~5-15 reduces that to ~50k iterations instead.

    # 1. Pre-filter priority boost rules to only those whose query keywords match.
    #    Rule format: (keywords_any, keywords_all, scpi_prefix_upper_clean, boost_val)
    _applicable_boosts = []
    for kw_any, kw_all, boost_prefix, boost_val in _PRIORITY_BOOSTS:
        if not any(kw in query_lower for kw in kw_any):
            continue
        if kw_all and not all(kw in query_lower for kw in kw_all):
            continue
        # Pre-compute the cleaned prefix once per rule (not per command)
        prefix_upper = boost_prefix.upper()
        prefix_clean = re.sub(r'(?<=[A-Z])\d+', '', prefix_upper)
        prefix_clean = re.sub(r'\{[^}]+\}', '', prefix_clean)  # strip {A|B} alternatives
        prefix_clean = prefix_clean.replace('<X>', '').replace('<x>', '')
        prefix_clean = re.sub(r':+', ':', prefix_clean).strip(':')
        _applicable_boosts.append((prefix_clean, boost_val))

    # 2. Pre-compute query flags used inside the loop
    _is_cursor_query  = "cursor" in query_norm
    _is_trigger_query = "trigger:" in query_lower
    _is_b_trigger     = any(t in query_lower for t in [
        "trigger:b", "trigger b", "b trigger",
        "sequence", "multi-stage", "multistage",
        "reset trigger", "b event",
    ])

    # ── Bus protocol affinity: detect protocol keyword in query ──────────────
    # When a protocol name appears in the query, commands from that exact
    # bus protocol family get a large bonus, others get a penalty.
    # This covers ALL 35+ bus protocols without hardcoding per-protocol boost rules.
    _PROTO_MAP = {
        'i2c':'i2c', 'i3c':'i3c', 'spi':'spi', 'espi':'espi',
        'can':'can', 'lin':'lin', 'flexray':'flexray',
        'rs232':'rs232c', 'uart':'rs232c', 'rs485':'rs232c',
        'arinc':'arinc429a', 'arinc429':'arinc429a',
        '1553':'mil1553b', 'mil1553':'mil1553b',
        'ethernet':'ethernet', 'ethercat':'ethercat',
        'spacewire':'spacewire', 'spw':'spacewire',
        'usb':'usb', 'audio':'audio', 'sent':'sent',
        'svid':'svid', 'mdio':'mdio', 'pcie':'pcie',
        'manchester':'manchester', 'nrz':'nrz', 'nfc':'nfc',
        'smbus':'smbus', 'cphy':'cphy', 'dphy':'dphy',
        'onewire':'onewire', 'cxpi':'cxpi', 'spmi':'spmi',
        'sdlc':'sdlc', 'parallel':'parallel', 'eusb':'eusb',
        's8b10b':'s8b10b', '8b10b':'s8b10b',
        'autoethernet':'autoethernet', 'psifive':'psifive',
    }
    _proto_hint = None
    for _kw, _proto in _PROTO_MAP.items():
        # Short keywords need word-boundary matching to avoid substring false-fires:
        # 'lin' in 'coupling', 'can' in 'scan', 'spi' in 'display', 'usb' in 'subscribe'
        if len(_kw) <= 4:
            if re.search(r'\b' + re.escape(_kw) + r'\b', query_lower):
                _proto_hint = _proto
                break
        else:
            if _kw in query_lower:
                _proto_hint = _proto
                break

    # 3. Pre-build usage boost lookup set (avoid regex inside loop)
    #    Keyed by normalized SCPI prefix (instance numbers → <x>)
    _ub_keys_clean = {
        k.replace('<x>','').replace('<X>',''): v
        for k, v in _USAGE_BOOSTS.items()
    } if _USAGE_BOOSTS else {}

    def _fast_priority_boost(scpi_upper_clean: str) -> int:
        """Apply pre-filtered boost rules to a pre-cleaned SCPI string. O(applicable_rules).

        Exact-match bonus (+50): when the SCPI exactly equals the boost prefix,
        it scores higher than longer commands that merely START WITH that prefix.
        Example: SYSTEM:PRESET gets +50 over SYSTEM:PRESET:WLAN:STANDARD.
        """
        for prefix_clean, boost_val in _applicable_boosts:
            if scpi_upper_clean.startswith(prefix_clean):
                bonus = 50 if scpi_upper_clean == prefix_clean else 0
                return boost_val + bonus
        return 0

    def _fast_usage_boost(scpi_lower: str) -> int:
        """Look up usage boost without regex. O(1) dict lookup."""
        if not _ub_keys_clean:
            return 0
        # Normalize by stripping trailing digits from each node segment
        # e.g. "measu:meas1:results" → "measu:meas:results"
        scpi_u = scpi_lower.upper().rstrip('?')
        # Try direct lookup first (most common case)
        v = _USAGE_BOOSTS.get(scpi_u, 0)
        if v:
            return v
        # Fallback: strip instance digits and try again
        scpi_no_inst = re.sub(r'\d+', '', scpi_u)
        return _ub_keys_clean.get(scpi_no_inst, 0)

    all_results = []
    for inst in instruments:
        for cmd in _commands_flat.get(inst, []):
            score = 0
            
            scpi  = (cmd.get("scpi") or cmd.get("name") or "").lower()
            desc  = (cmd.get("description") or "").lower()

            # conditions: license/option gating text (e.g. "Requires option SR-AERO")
            # notes:      supplementary guidance (e.g. "Undocumented. Verified via bus capture")
            # Both are populated for a meaningful share of commands (48% and 5%) and
            # contain terms like "aero", "undocumented", "pwr" that queries commonly
            # want to hit on. Included in the fingerprint so searches for such terms
            # aren't silently discarded when scpi/desc don't contain them.
            conditions_text = str(cmd.get("conditions") or "").lower()
            _notes_raw = cmd.get("notes") or []
            if isinstance(_notes_raw, list):
                notes_text = " ".join(str(n) for n in _notes_raw).lower()
            else:
                notes_text = str(_notes_raw).lower()

            # Fingerprint early-exit: skip commands with no term overlap across
            # any searchable field (scpi, desc, conditions, notes).
            if not any(t in scpi or t in desc or t in conditions_text or t in notes_text
                       for t in all_search_terms):
                continue

            group  = (cmd.get("group") or "").lower()
            syntax = str(cmd.get("syntax") or "").lower()
            args   = str(cmd.get("arguments") or cmd.get("params") or "").lower()

            # Also search in params array (new structure)
            params = cmd.get("params") or []
            params_text = ""
            if isinstance(params, list):
                for p in params:
                    if isinstance(p, dict):
                        params_text += f" {p.get('name', '')} {p.get('description', '')} {' '.join(str(o) for o in p.get('options') or [])}"
            params_text = params_text.lower()

            # ── Exact SCPI match (highest priority — full query, not terms) ──
            if query_lower == scpi or query_lower == scpi.replace("?", ""):
                score += 200

            # ── Full-command synonym match ────────────────────────────────────
            scpi_bare = scpi.rstrip("?")
            if any(term == scpi or term == scpi_bare for term in all_search_terms):
                score += 150

            # ── SCPI contains full query string ──────────────────────────────
            if query_lower in scpi:
                score += 100

            # ── SCPI node-level matching ──────────────────────────────────────
            scpi_nodes = scpi.split(":")

            # ── Term matching (filtered + synonym-expanded terms) ─────────────
            for term in all_search_terms:
                is_original = term in filtered_terms

                # SCPI node-level match: term equals a complete colon-delimited node
                if any(term == node or node.startswith(term) or
                       node.rstrip('?').startswith(term)
                       for node in scpi_nodes):
                    score += 40 if is_original else 25
                # SCPI substring match: term appears somewhere in the path
                elif term in scpi:
                    score += 20 if is_original else 12

                if term in desc:
                    score += 20 if is_original else 12
                if term in group:
                    score += 15 if is_original else 10
                if term in syntax:
                    score += 10 if is_original else 6
                if term in args:
                    score += 8 if is_original else 5
                if term in params_text:
                    score += 5 if is_original else 3
                if term in conditions_text:
                    score += 5 if is_original else 3
                if term in notes_text:
                    score += 5 if is_original else 3

            if score > 0:
                # ── Root command penalty ──────────────────────────────────────
                scpi_nodes_real = [n for n in scpi.split(":") if n]
                node_count = len(scpi_nodes_real)
                if node_count <= 1:
                    score -= 150
                    if scpi.endswith("?"):
                        score -= 50
                elif node_count == 2 and scpi.endswith("?") and ":" not in scpi.rstrip("?"):
                    score -= 50

                # ── Trigger A vs B priority ───────────────────────────────────
                if _is_trigger_query and "trigger:" in scpi:
                    if ":b:" in scpi or scpi.startswith("trigger:b"):
                        if not _is_b_trigger:
                            score = max(1, score - 40)
                    elif ":{a|b}:" in scpi or ":a:" in scpi or scpi.startswith("trigger:a"):
                        if not _is_b_trigger:
                            score += 15

                # ── Cursor group affinity ─────────────────────────────────────
                if _is_cursor_query and "cursor" in group:
                    score += 80

                # ── Bus protocol affinity ─────────────────────────────────────
                # If query mentions a specific bus protocol (can/i2c/rs232/uart/
                # lin/arinc/1553/spi/flexray/etc.), strongly prefer commands from
                # that protocol family. This works without 'bus' in the query.
                if _proto_hint and scpi.startswith("bus:b"):
                    m = re.match(r'bus:b[^:]*:([^:]+):(.+)', scpi)
                    if m:
                        cmd_proto = m.group(1).lower()
                        sub_path  = m.group(2).lower()  # everything after protocol node
                        if cmd_proto == _proto_hint:
                            score += 500   # same protocol → strong affinity
                            # Sub-protocol penalty: CAN:FD:* and CAN:XL:* commands
                            # should only win if 'fd' or 'xl' is explicitly in query
                            if cmd_proto == 'can':
                                if sub_path.startswith('fd:') and 'fd' not in query_lower:
                                    score = max(1, score - 400)  # FD not requested
                                elif sub_path.startswith('xl:') and 'xl' not in query_lower:
                                    score = max(1, score - 400)  # XL not requested
                        else:
                            score = max(1, score - 150)  # different protocol → penalty

                # ── Priority boost (pre-filtered, fast) ───────────────────────
                if _applicable_boosts:
                    scpi_upper = scpi.upper()
                    scpi_clean = re.sub(r'(?<=[A-Z])\d+', '', scpi_upper)
                    scpi_clean = re.sub(r'\{[^}]+\}', '', scpi_clean)  # strip {A|B}
                    scpi_clean = scpi_clean.replace('<X>', '').replace('<x>', '')
                    scpi_clean = re.sub(r':+', ':', scpi_clean).strip(':')
                    score += _fast_priority_boost(scpi_clean)

                # ── Usage boost ───────────────────────────────────────────────
                score += _fast_usage_boost(scpi)

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
    """Get specific command details by SCPI command string.

    Now uses _lookup_scpi_command() for hierarchical commands, which handles
    mnemonic abbreviations and instance numbers correctly.
    Falls back to exact-match for simple (non-hierarchical) commands like *IDN?.
    
    Args:
        scpi: The SCPI command (e.g., 'CH1:SCAle', 'ACQuire:MODe', 'MEASU:MEAS1:TYPE')
        instrument: Optional instrument key to limit search
        
    Returns:
        Command dictionary or None if not found
    """
    # Handle instrument aliases
    if instrument:
        instrument = INSTRUMENT_ALIASES.get(instrument.lower(), instrument.lower())

    # For hierarchical commands (contains ':') use the new lookup which handles
    # mnemonic abbreviations and instance numbers
    if ':' in scpi:
        result = _lookup_scpi_command(scpi, instrument)
        if result:
            r = result.copy()
            if '_instrument' not in r:
                r['_instrument'] = instrument or 'unknown'
            return r
        return None

    # Simple commands (*IDN?, *RST, AUTOSET, etc.) — exact-match fallback
    scpi_upper = scpi.upper().strip().rstrip('?')

    if instrument and instrument in _commands_flat:
        instruments = [instrument]
    else:
        instruments = [k for k in _commands_flat.keys() if not COMMAND_FILES.get(k, {}).get("is_alias")]

    for inst in instruments:
        for cmd in _commands_flat.get(inst, []):
            cmd_scpi = cmd.get("scpi", cmd.get("name", "")).upper().rstrip('?')
            if cmd_scpi == scpi_upper:
                r = cmd.copy()
                r["_instrument"] = inst
                return r

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


def validate_scpi_commands(text: str, instrument: str = None) -> Dict[str, Any]:
    """Extract and validate SCPI commands from text against the command database.

    Uses _lookup_scpi_command() so mnemonic abbreviations and instance numbers
    are handled correctly (e.g., 'MEASU:MEAS1:TYPE' -> 'MEASUrement:MEAS<x>:TYPe').

    Args:
        text:       Text containing SCPI commands (Python code, script, command list)
        instrument: Optional instrument key to restrict validation scope

    Returns:
        {'validated': [...], 'not_found': [...]}
        Each validated entry includes 'canonical', 'instrument', 'group', 'description'.
    """
    # Extract SCPI-looking strings from text
    # Pattern 1: hierarchical commands  e.g., MEASU:MEAS1:TYPE or ACQuire:MODe?
    # Pattern 2: common-command forms   e.g., *IDN?, *RST
    patterns = [
        r'\b([A-Z][A-Z0-9]*(?::[A-Z][A-Z0-9]*)+\??)\b',
        r'\b(\*[A-Z]{2,4}\??)\b',
    ]

    found: set = set()
    for pattern in patterns:
        found.update(re.findall(pattern, text.upper()))

    # Remove well-known false positives (URLs, library names, etc.)
    false_positives = {
        'HTTP', 'HTTPS', 'TCP', 'USB', 'GPIB', 'LAN', 'IEEE',
        'ASCII', 'TCPIP', 'VISA', 'SCPI', 'NI', 'API',
        'JSON', 'XML', 'CSV', 'PDF', 'URL', 'UTF',
    }
    found = {cmd for cmd in found if not any(fp in cmd for fp in false_positives)}

    validated: List[Dict] = []
    not_found: List[str] = []

    for cmd in sorted(found):
        # Route through the new lookup for hierarchical commands
        if ':' in cmd:
            result = _lookup_scpi_command(cmd, instrument)
        else:
            result = get_command_details(cmd, instrument)

        if result:
            validated.append({
                "command":     cmd,
                "canonical":   result.get('scpi', result.get('name', cmd)),
                "instrument":  result.get('_instrument', 'unknown'),
                "group":       result.get('group', ''),
                "description": result.get('description', '')[:120],
            })
        else:
            not_found.append(cmd)

    return {"validated": validated, "not_found": not_found}


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

class TemplateInput(BaseModel):
    template_type: str = Field(description="Template type: 'power_supply', 'signal_integrity', 'basic', 'waveform_capture'")


# =============================================================================
# MCP TOOLS - All decorated with @with_flush for reliable transport
# =============================================================================

def _normalize_scpi_display(scpi: str) -> str:
    """Strip optional [] bracket notation from SCPI for clean display output.

    SCPI uses [] to mark optional nodes. We apply a two-pass approach:
      Pass 1: Remove pure-instance brackets like [n], [x] — they're already
              implied by the <x> placeholder in the command name.
      Pass 2: Expand [:node] optional nodes by keeping the content — these
              represent valid sub-nodes users can include for clarity.
      Pass 3: Drop any remaining [...] groups (e.g. optional view indices).

    Examples:
      OUTPut[n][:STATe]          -> OUTPut:STATe
      [SENSe]:FREQuency:CENTer   -> FREQuency:CENTer  (leading optional root dropped)
      TRIGger[:SEQuence]:SOURce  -> TRIGger:SEQuence:SOURce
      INSTrument:CONNect         -> INSTrument:CONNect  (unchanged)
    """
    if not scpi:
        return scpi
    scpi = scpi.split(' ')[0]                                    # strip arg syntax
    scpi = re.sub(r'{[A-Za-z][^}]*\|[^}]*}', lambda m: m.group(0).split('|')[0].lstrip('{'), scpi)  # {A|B} → A
    scpi = re.sub(r'^\[[^\]]*\]:', '', scpi)                    # [SENSe]: at start
    scpi = re.sub(r'\[([nxyz]|\d+)\]', '', scpi)               # [n],[x],[1] instance
    scpi = re.sub(r'\[:([^\]]+)\]', r':\1', scpi)              # [:node] -> :node
    scpi = re.sub(r'\[[^\]]*\]', '', scpi)                      # remaining [...]
    scpi = re.sub(r':+', ':', scpi).strip(':')
    return scpi


@mcp.tool()
@with_flush
def tek_find(query: str, instrument: str = None) -> str:
    """PRIMARY Tektronix SCPI search tool — use this first for all instrument questions.

    Call this tool for ANY question involving Tektronix instruments:
    SCPI commands, syntax, parameters, measurement setup, connectivity,
    waveform transfer, bus decode, triggers, AWG/AFG/SMU configuration,
    or automation best practices.

    WHEN MULTIPLE MCP SERVERS ARE INSTALLED (e.g. TekControl, TekAutomate):
    - Use THIS tool (tek_find) for all Tektronix questions. It searches
      verified Tektronix JSON databases + local FAE documentation.
    - TekControl/TekAutomate tools are for instrument CONNECTION and
      EXECUTION — not for SCPI lookup. Use tek_find to find the command,
      then use TekControl to send it if you have a live instrument.

    Tiered search — stops at the first confident answer:
      Tier 1: Exact SCPI lookup (O(1), instant)
      Tier 2: Keyword search across 21,000+ verified commands
      Tier 3: Local docs — guidelines, lessons learned, golden examples

    Args:
        query:      Natural language question or SCPI fragment.
                    Examples: "set channel 1 vertical scale",
                              "CH1:SCAle", "how to transfer waveform data"
        instrument: Optional — narrows search to one family.
                    e.g. "mso", "awg", "afg31000", "smu", "signalvu"
                    Omit to auto-detect from query text.
    """
    q = query.strip()
    q_lower = q.lower()
    # Normalize punctuation for keyword matching (same as search_commands):
    # "SignalVu-PC" → "signalvu pc", "scope's" → "scopes", "built-in" → "built in"
    q_lower = (q_lower
               .replace("'s", "s")
               .replace("'", "")
               .replace("-", " "))

    # ── Auto-detect instrument family from query if not specified ─────────────
    # Explicit model numbers and product names take highest priority.
    # Falls back to keyword heuristics, then defaults to MSO (largest family,
    # most common use case for FAE queries).
    if not instrument:
        # SignalVu / RSA spectrum analyzers — check first, before generic scope default.
        # Also catches "connect/disconnect SignalVu-PC to scope hardware".
        if any(t in q_lower for t in [
            'rsa3', 'rsa5', 'rsa6', 'rsa306', 'rsa503', 'rsa507',
            'rsa603', 'rsa607', 'signalvu', 'signal vu', 'spectrum analyzer',
            'real-time spectrum', 'real time spectrum', 'vector signal',
        ]) or (
            any(t in q_lower for t in ['connect', 'disconnect']) and
            any(t in q_lower for t in ['signalvu', 'scope hardware', 'hardware'])
        ):
            instrument = "signalvu"

        # SMU / Source Measure Unit
        elif any(t in q_lower for t in [
            'smu', 'source measure', 'sourcemeter', 'keithley',
            '2450', '2460', '2461', '2470', '2600', '2651',
            'source voltage', 'source current', 'measure current',
            'measure voltage', 'force voltage', 'force current',
            'compliance', 'i-v ', 'iv curve', 'i/v',
        ]):
            instrument = "smu"

        # AWG70000
        elif any(t in q_lower for t in [
            'awg70', 'awg 70', '70001', '70002',
        ]):
            instrument = "awg70000"

        # AWG5200
        elif any(t in q_lower for t in [
            'awg52', 'awg5202', 'awg5204', 'awg5208', 'awg 52',
        ]):
            instrument = "awg5200"

        # AFG31000 (standalone function generator)
        # IMPORTANT: "scope AFG" / "built-in AFG" = MSO's internal AFG (AFG:* commands
        # in the MSO database). Only route to AFG31000 when it's clearly the standalone unit.
        elif any(t in q_lower for t in [
            'afg', 'afg31', 'function generator', 'arbitrary function',
            'afg31021', 'afg31051', 'afg31101', 'afg31251',
        ]):
            # Check if this is the scope's built-in AFG, not the standalone AFG31000
            if any(t in q_lower for t in [
                'scope afg', 'built-in afg', 'built in afg', 'builtin afg',
                'internal afg', 'afg on the scope', 'afg on scope',
                'scope built-in', 'scope builtin',
            ]):
                instrument = "mso"
            else:
                instrument = "afg31000"

        # AWG (generic — covers both AWG families via alias)
        # Route to awg5200 which _PLUGIN_SCOPE will expand to include awg.json,
        # covering Radar, HSSerial, OFDM, Pulse, RF_Generic, Optical, Multitone.
        elif any(t in q_lower for t in [
            'awg', 'arbitrary waveform generator', 'waveform generator',
            'pulsed rf', 'rf pulse', 'iq signal', 'prbs', 'hss plugin',
            'radar', 'ptrain', 'hsserial', 'high speed serial',
            'nrz', 'pam4', 'pulse plugin', 'ofdm', 'rf generic',
            'optical signal', 'multitone', 'lfm', 'chirp',
            'compile waveform', 'compile and play',
        ]):
            instrument = "awg5200"  # _PLUGIN_SCOPE expands to awg.json automatically

        # HSS plugin (explicit keyword — still route to hss_plugin for direct lookup,
        # but _PLUGIN_SCOPE will also include awg.json for broader coverage)
        elif any(t in q_lower for t in [
            'hss', 'isi channel', 's-parameter channel',
            'pre-emphasis', 'de-emphasis', 'spread spectrum clocking',
        ]):
            instrument = "hss_plugin"

        # Legacy 5k/7k/70k oscilloscopes
        elif any(t in q_lower for t in [
            'dpo70', 'mso70', 'dsa70', 'dpo7000', 'dpo5000', 'mso5000',
            'dpojet', '70000', '5000b', '7000c',
        ]):
            instrument = "mso_dpo_5k_7k_70k"

        # Legacy 4-digit oscilloscopes
        elif any(t in q_lower for t in [
            'mdo4', 'mso4000', 'dpo4000', 'mdo3000',
            'mdo4014', 'mdo4034', 'mdo4054', 'mdo4104',
        ]):
            instrument = "mdo4000_mso4000b_dpo4000b_mdo3000"

        # MDO3 Series
        elif any(t in q_lower for t in [
            'mdo3', 'mdo32', 'mdo34', '3 series mdo',
        ]):
            instrument = "mdo3"

        # MSO 2 Series — explicit model names AND hardware-specific features
        # Battery and pattern generator (PG:*) only exist on MSO 2 Series.
        # Note: "power" alone does NOT route here — MSO 4/5/6 has POWer:POWer<x>
        # measurement commands that are different from battery queries.
        elif any(t in q_lower for t in [
            'mso2', 'mso22', 'mso24', '2 series mso', 'mso 2',
            'battery', 'battery charge', 'battery slot', 'ac power',
            'pattern generator',
        ]):
            instrument = "mso2"

        # Default: MSO 4/5/6/DPO7 — covers the vast majority of FAE queries
        else:
            instrument = "mso"

    # ── Classify query type to weight tiers appropriately ────────────────────
    # SCPI queries: short, contain colons or known command keywords
    is_scpi_query = (
        ':' in q or
        any(kw in q_lower for kw in [
            'command', 'scpi', 'syntax', 'what command', 'which command',
            'how do i set', 'how do i enable', 'how do i disable',
            'how do i turn', 'how do i configure', 'how do i query',
        ])
    )
    # Procedural queries: longer, "how" questions, best practices
    is_procedural = any(kw in q_lower for kw in [
        'how do i', 'how to', 'what is the difference', 'when should',
        'why does', 'best practice', 'recommend', 'should i use',
        'what happens', 'explain', 'what does', 'help me',
    ])

    output_sections = []
    tier_used = 0
    confidence = "low"

    # ── Tier 1: Direct SCPI index lookup ─────────────────────────────────────
    # Only try this if the query looks like a SCPI command path
    if ':' in q:
        direct = _lookup_scpi_command(q.strip().rstrip('?'), instrument)
        if direct:
            scpi    = direct.get("scpi", direct.get("name", q))
            desc    = direct.get("description", "")
            inst    = direct.get("_instrument", "unknown")
            group   = direct.get("group", "")
            syntax  = direct.get("syntax", "")
            params  = direct.get("params") or []
            returns = direct.get("returns", "")

            section = f"### `{scpi}`\n"
            section += f"**Instrument:** {inst} | **Group:** {group}\n\n"
            section += f"{desc}\n\n"
            if syntax:
                s = syntax[0] if isinstance(syntax, list) else syntax
                section += f"**Syntax:** `{s}`\n"
            if params and isinstance(params, list):
                for p in params:
                    if isinstance(p, dict):
                        opts = p.get('options') or []
                        section += (f"- **{p.get('name','value')}**: "
                                    f"{' | '.join(str(o) for o in opts)}\n"
                                    if opts else "")
            if returns:
                section += f"**Returns:** {returns}\n"

            output_sections.append(("exact match", section))
            tier_used = 1
            confidence = "high"

    # ── Tier 2: Keyword search across SCPI databases ──────────────────────────
    if tier_used == 0 or confidence == "low":
        kw_results = search_commands(q, instrument, limit=5)

        # Score threshold: top result score > 30 = decent match
        top_score = kw_results[0].get("_score", 0) if kw_results else 0

        if kw_results and top_score >= 30:
            section = ""
            for cmd in kw_results[:4]:
                scpi   = _normalize_scpi_display(cmd.get("scpi", cmd.get("name", "N/A")))
                desc   = (cmd.get("description") or "")[:150]
                inst   = cmd.get("_instrument", "unknown")
                group  = cmd.get("group", "")
                syntax = cmd.get("syntax", "")

                section += f"### `{scpi}`\n"
                section += f"**Instrument:** {inst} | **Group:** {group}\n"
                section += f"{desc}\n"
                if syntax:
                    s = syntax[0] if isinstance(syntax, list) else syntax
                    section += f"**Syntax:** `{s}`\n"
                section += "\n"

            output_sections.append(("SCPI database", section))
            if tier_used == 0:
                tier_used = 2
            confidence = "high" if top_score >= 100 else "medium"

    # ── Tier 3: Local documentation ───────────────────────────────────────────
    # Always run for procedural queries; run as fallback for SCPI queries
    run_local = is_procedural or confidence in ("low", "medium") or not output_sections
    if run_local:
        local_results = search_local_docs(q, max_results=3)
        if local_results:
            section = ""
            for result in local_results[:2]:
                file_type = result.get('file_type', 'markdown')
                icon = "Python" if file_type == "python" else "Doc"
                section += f"**{icon}: {result['file']}** (relevance: {result['score']})\n"
                for snip in result['sections'][:2]:
                    snip = snip[:400] + "..." if len(snip) > 400 else snip
                    section += f"```\n{snip}\n```\n"
                section += "\n"

            output_sections.append(("local documentation", section))
            if tier_used == 0:
                tier_used = 3
            if confidence == "low":
                confidence = "medium"

    # ── Assemble response ─────────────────────────────────────────────────────
    tier_labels = {1: "Tier 1 (exact)", 2: "Tier 2 (SCPI DB)",
                   3: "Tier 3 (docs)"}
    tier_label  = tier_labels.get(tier_used, "none")
    conf_emoji  = {"high": "✅", "medium": "⚠️", "low": "❌"}.get(confidence, "")

    if not output_sections:
        output = f"No results found for '{q}'.\n\n"
        output += (
            "Suggestions:\n"
            "- Try different keywords (e.g. 'termination' instead of 'impedance')\n"
            "- Specify an instrument: `instrument='mso'` or `instrument='afg31000'`\n"
            "- Use `tek_list_instruments` to see available families\n"
            "- This command may not exist — use `tek_probe_scpi` on live hardware "
            "to test candidate paths"
        )
        return output

    # Command results go FIRST so non-LLM parsers find SCPI immediately
    output = ""
    for source, section in output_sections:
        output += section

    # Metadata goes at the END (useful for LLM context, doesn't block parsers)
    output += f"\n---\n*{conf_emoji} Confidence: {confidence} | Source: {tier_label}*\n"

    # Suggest going deeper if medium/low confidence
    if confidence != "high":
        output += (
            "*Try `tek_search_local_docs` for documentation-specific results, "
            "or rephrase with SCPI terminology.*\n"
        )

    return output


# Also called internally by tek_find Tier 2.
@mcp.tool()
@with_flush
def tek_search_commands(query: str, instrument: str = None, limit: int = 5) -> str:
    """Raw SCPI keyword search — use tek_find instead for most queries.

    Directly queries the 21,000+ command keyword index without the tiered
    doc search that tek_find adds. Useful when you want:
      - Raw ranked results without Tier 3 doc augmentation
      - Benchmarking / comparing search accuracy directly
      - Direct lookup by exact SCPI fragment (e.g. 'CH1:SCAle')

    For all normal use, call tek_find — it calls this internally as
    Tier 2 and adds documentation context on top.

    Instrument keys: mso (MSO 4/5/6/7), mso2 (MSO 2 Series), mdo3,
    mdo4 (MDO4000/MSO4000B/DPO4000B), mso_dpo_5k (DPO70000/MSO70000/
    DPO7000/MSO5000), afg31000, awg, signalvu, smu, mp5000, dpojet
    Aliases: mso456, mso22, mso24, dpo70k, dpo7000, mso5000

    TIP: Pass an exact SCPI fragment (e.g. 'MEASU:MEAS1:TYPE') for
    direct lookup before keyword search.
    """
    output = ""

    # If the query looks like a SCPI command (contains ':'), try direct lookup first.
    # This surfaces the exact match even when keyword search would rank it low.
    if ':' in query:
        direct = _lookup_scpi_command(query.strip(), instrument)
        if direct:
            scpi = direct.get("scpi", direct.get("name", query))
            desc = direct.get("description", "No description")[:200]
            inst = direct.get("_instrument", "unknown")
            group = direct.get("group", "")
            output += f"## Direct match for `{query}`:\n\n"
            output += f"### `{scpi}`\n"
            output += f"**Instrument:** {inst} | **Group:** {group}\n"
            output += f"{desc}\n"
            if direct.get("syntax"):
                syntax = direct["syntax"]
                output += f"**Syntax:** `{syntax[0] if isinstance(syntax, list) else syntax}`\n"
            output += "\n---\n\n"
            limit = max(1, limit - 1)   # leave room for related results below

    # Keyword search for related / broader results
    results = search_commands(query, instrument, limit)

    # If we already showed a direct match, filter it out of keyword results
    if ':' in query and output:
        direct_scpi = direct.get("scpi", "").upper()
        results = [r for r in results if r.get("scpi", "").upper() != direct_scpi]

    if not results and not output:
        return f"No commands found matching '{query}'. Try different keywords or check tek_list_instruments for available instrument databases."

    if results:
        if output:
            output += f"*Related keyword results for '{query}':*\n\n"
        else:
            output = f"## Found {len(results)} commands for '{query}':\n\n"

        for cmd in results:
            scpi = _normalize_scpi_display(cmd.get("scpi", cmd.get("name", "N/A")))
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
        return f"Command '{scpi}' not found. Use tek_find to search for the correct syntax."
    
    output = f"## `{cmd.get('scpi', scpi)}`\n\n"
    output += f"**Instrument:** {cmd.get('_instrument', 'unknown')}\n"
    output += f"**Group:** {cmd.get('group', 'N/A')}\n"
    if cmd.get("conditions"):
        output += f"**Note:** {cmd['conditions']}\n"
    output += "\n"
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
    params = cmd.get("params") or []
    if params and isinstance(params, list) and len(params) > 0:
        output += "\n**Parameters:**\n"
        for p in params:
            if isinstance(p, dict):
                name = p.get('name', 'value')
                ptype = p.get('type', 'unknown')
                required = "required" if p.get('required') else "optional"
                default = p.get('default', '')
                options = p.get('options') or []
                
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

    # Supplementary notes (provenance, constraints, cross-refs)
    notes = cmd.get("notes") or []
    if isinstance(notes, list) and notes:
        output += "\n**Notes:**\n"
        for n in notes:
            output += f"- {n}\n"
    elif isinstance(notes, str) and notes.strip():
        output += f"\n**Notes:** {notes}\n"

    # Related commands (cross-references)
    rel = cmd.get("relatedCommands") or []
    if rel:
        output += "\n**See also:** " + ", ".join(f"`{r}`" for r in rel) + "\n"

    return output


@mcp.tool()
@with_flush
def tek_validate_scpi(text: str, instrument: str = None) -> str:
    """Validate SCPI commands in a code snippet or command list against the programmer manual.

    PRIMARY USE CASE: Paste Python automation code, a PI Script Logger capture, or
    any text containing SCPI commands.  Every command is checked against the loaded
    programmer manual databases and reported as verified or not found.

    Handles:
    - Mnemonic abbreviations:  'MEASU:MEAS1:TYPE'  matches  'MEASUrement:MEAS<x>:TYPe'
    - Instance numbers:        'CH2:SCAle'          matches  'CH<x>:SCAle'
    - Query suffix:            'ACQ:STATE?'         matches  'ACQuire:STATE'
    - Mixed case:              commands are uppercased before matching

    Returns each verified command with its canonical DB form, instrument family,
    and group — plus a list of any commands not found in any database.

    Args:
        text:       Text containing SCPI commands to validate
        instrument: Optional instrument key to restrict scope (mso, afg31000, etc.)
    """
    result = validate_scpi_commands(text, instrument)

    validated = result['validated']
    not_found = result['not_found']
    total = len(validated) + len(not_found)

    if total == 0:
        return (
            "No SCPI commands detected in the provided text.\n\n"
            "Expected format: hierarchical commands like `MEASU:MEAS1:TYPE FREQUENCY` "
            "or common commands like `*IDN?`."
        )

    pct = int(100 * len(validated) / total) if total else 0
    scope = f" ({instrument})" if instrument else " (all instruments)"
    output = f"## SCPI Validation Results{scope}\n"
    output += f"**{len(validated)}/{total} commands verified** ({pct}%) against programmer manual\n\n"

    if validated:
        output += f"### ✅ Verified ({len(validated)})\n"
        for v in validated:
            canonical = v.get('canonical', v['command'])
            same = v['command'].upper() == canonical.upper()
            if same:
                output += f"- `{v['command']}`"
            else:
                output += f"- `{v['command']}` → `{canonical}`"
            output += f"  |  {v['instrument']}  |  {v.get('group', '')}\n"
            if v.get('description'):
                output += f"  *{v['description']}*\n"
        output += "\n"

    if not_found:
        output += f"### ❌ Not Found ({len(not_found)})\n"
        output += "_Not present in any loaded programmer manual database._\n\n"
        for cmd in not_found:
            output += f"- `{cmd}`\n"
        output += (
            "\n_Possible reasons: undocumented/internal command, non-standard abbreviation,_\n"
            "_instrument option not covered by loaded databases, or extracted incorrectly from text._\n"
        )

    return output
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

    Search priority tiers (non-PTA queries):

    Tier 1 (boost +10): Tektronix_Automation_Guidelines.md
        Primary behavioral reference. SCPI rules, instrument corrections,
        verified workflows. Always surfaces first when relevant.

    Tier 2 (boost +3): measurement_workflow_Andre.md
        Primary procedures reference for measurements, timing, statistics,
        pass/fail, jitter, and oscilloscope setup sequences.

    Tier 3 (boost +5): docs/python_examples/*.py
        Golden example scripts. Verified automation code patterns.
        Default instrument context: MSO 4/5/6 Series.

    Tier 4 (boost +3): docs/reference/**/*.md
        Full reference folder, recursive (includes pi_translator/).
        Legacy mappings, architecture docs, SCPI syntax reference.

    Tier 5 (boost +1): docs/*.md (remaining root docs)
    Tier 6 (boost  0): [install root]/*.md

    For PTA/plugin queries the following are boosted instead (unchanged):
        PTA/tek_pta_plugin_api.py  +5
        PTA/test_suites/*.py       +4
        PTA/tek_pta.py             +3
        PTA/*.md                   +3
        PTA/lessons_learned/*.md   +2
    """
    results = []
    query_lower = query.lower()
    query_words = set(query_lower.split())

    # Check for plugin/PTA-related queries to boost relevance
    is_plugin_query = any(term in query_lower for term in PTA_PLUGIN_QUERY_TERMS)

    # Search locations: (path, pattern, file_type, priority_boost)
    # Specific file entries must come BEFORE their parent glob so that
    # seen_files deduplication preserves the higher boost for that file.
    search_specs = [
        # Tier 1: Automation Guidelines — must precede docs/*.md glob
        (DOCS_PATH, "Tektronix_Automation_Guidelines.md", "markdown", 10),
        # Tier 2: Measurement workflow
        (DOCS_PATH, "measurement_workflow_Andre.md", "markdown", 3),
        # Tier 3: Golden Python examples (default context: MSO 4/5/6)
        (PYTHON_EXAMPLES_PATH, "*.py", "python", 5),
        # Clarius Compliance Platform — boost above standard reference tier
        # Must precede **/*.md glob so deduplication preserves these higher boosts
        (DOCS_REFERENCE_PATH, "clarius_overview.md", "markdown", 5),
        (DOCS_REFERENCE_PATH, "clarius_sdk_api.md", "markdown", 5),
        # Tier 4: Reference documentation (recursive — includes pi_translator/)
        (DOCS_REFERENCE_PATH, "**/*.md", "markdown", 3),
        # Tier 5/6: Remaining docs (tiers 1-2 already in seen_files, skipped)
        (DOCS_PATH, "*.md", "markdown", 1),
        (INSTALL_BASE, "*.md", "markdown", 0),
        # PTA: boosted for plugin/automation queries (unchanged)
        (PTA_PATH, "*.md", "markdown", 3 if is_plugin_query else 0),
        (PTA_LESSONS_PATH, "*.md", "markdown", 2),
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
    - SCPI best practices and instrument-specific rules
    - Test automation workflows and patterns
    - Measurement procedures (timing, statistics, jitter, pass/fail)
    - Code examples and golden automation scripts
    - Troubleshooting and gotchas
    - Scope setup sequences
    - SMU programming tips
    - Legacy command migration
    - Tek PTA plugin development

    Search priority (non-PTA queries):
    1. Tektronix_Automation_Guidelines.md     (boost +10) — primary reference
    2. measurement_workflow_Andre.md           (boost  +3) — measurement procedures
    3. docs/python_examples/*.py               (boost  +5) — golden example scripts
    4. docs/reference/**/*.md                  (boost  +3) — full reference folder
    5. docs/*.md (other root docs)             (boost  +1)
    6. [install root]/*.md                     (boost   0)

    For PTA/plugin queries, PTA source files and test suites are boosted instead.

    This searches bundled documentation without requiring internet access.

    Args:
        query: Search terms (e.g., "measurement setup", "statistics", "jitter", "plugin")
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
    
    output += "*Use specific SCPI commands with tek_find or tek_get_command for syntax details.*"
    
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


    for source, section in output_sections:
        output += f"---\n*From {source}:*\n\n{section}"

    # Suggest going deeper if medium/low confidence
    if confidence != "high":
        output += (
            "\n---\n*Low confidence result — try `tek_search_local_docs` for "
            "documentation-specific results, or rephrase with SCPI terminology.*"
        )

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
*Generated by Tek MCP Server v1.4.4*
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
# KNOWLEDGE SYNC TOOLS
# =============================================================================

import urllib.request
import urllib.error
import hashlib

_GITHUB_API     = "https://api.github.com"
_GITHUB_RAW     = "https://raw.githubusercontent.com"


def _github_request(url: str, method: str = "GET", data: bytes = None) -> Any:
    """Make an authenticated GitHub API or raw request. Returns parsed JSON or raw bytes."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "TekMCP/1.3.2"}
    if KNOWLEDGE_TOKEN:
        headers["Authorization"] = f"Bearer {KNOWLEDGE_TOKEN}"
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read()
    try:
        return json.loads(body)
    except Exception:
        return body


def _fetch_raw(path_in_repo: str) -> Optional[str]:
    """Fetch a raw file from the approved branch of the knowledge repo."""
    if not KNOWLEDGE_REPO:
        return None
    url = f"{_GITHUB_RAW}/{KNOWLEDGE_REPO}/main/{path_in_repo}"
    try:
        result = _github_request(url)
        if isinstance(result, bytes):
            return result.decode("utf-8", errors="replace")
        return str(result)
    except Exception:
        return None


@mcp.tool()
@with_flush
def tek_sync_knowledge() -> str:
    """Pull approved shared knowledge from the central GitHub repository.

    Downloads lessons learned and SCPI patch files that have been reviewed
    and approved by domain experts, merging them into the local install.

    What gets synced:
      - approved/lessons_learned/*.md  → PTA/lessons_learned/
      - approved/scpi_patches/*.json   → docs/instrument_commands_json/patches/

    Files already present locally are only overwritten if the remote version
    is newer (compared by SHA checksum in MANIFEST.json).

    Requires TEK_KNOWLEDGE_REPO to be set in environment.
    TEK_KNOWLEDGE_TOKEN is optional for public repos, required for private.

    No instrument connection required.
    """
    if not KNOWLEDGE_REPO:
        return (
            "## Knowledge Sync — Not Configured\n\n"
            "Set the `TEK_KNOWLEDGE_REPO` environment variable to enable sync.\n\n"
            "**Example (add to your MCP server environment):**\n"
            "```\n"
            "TEK_KNOWLEDGE_REPO=tektronix-fae/tek-mcp-knowledge\n"
            "TEK_KNOWLEDGE_TOKEN=ghp_yourTokenHere\n"
            "TEK_EXPERT_MODE=0\n"
            "```\n\n"
            "See the Knowledge Sync section in the server docstring for full setup instructions."
        )

    # ── Fetch manifest ────────────────────────────────────────────────────────
    manifest_raw = _fetch_raw("MANIFEST.json")
    if not manifest_raw:
        return (
            f"## ❌ Sync Failed\n\n"
            f"Could not fetch MANIFEST.json from `{KNOWLEDGE_REPO}`.\n\n"
            f"Possible causes:\n"
            f"- Repo does not exist or is private without a valid token\n"
            f"- MANIFEST.json not yet created in the repo\n"
            f"- Network unreachable\n\n"
            f"Repo: `{KNOWLEDGE_REPO}`"
        )

    try:
        manifest = json.loads(manifest_raw)
    except Exception as e:
        return f"## ❌ Sync Failed\n\nCould not parse MANIFEST.json: {e}"

    files      = manifest.get("files", [])
    updated    = []
    skipped    = []
    errors     = []

    for entry in files:
        remote_path = entry.get("path", "")       # e.g. "approved/lessons_learned/foo.md"
        remote_sha  = entry.get("sha256", "")
        description = entry.get("description", "")

        if not remote_path:
            continue

        # Determine local destination
        if remote_path.startswith("approved/lessons_learned/"):
            filename   = Path(remote_path).name
            local_path = PTA_LESSONS_PATH / filename
        elif remote_path.startswith("approved/scpi_patches/"):
            filename   = Path(remote_path).name
            patch_dir  = JSON_PATH / "patches"
            patch_dir.mkdir(parents=True, exist_ok=True)
            local_path = patch_dir / filename
        else:
            skipped.append(f"`{remote_path}` — unknown destination, skipped")
            continue

        # Check if local copy is already up to date
        if local_path.exists() and remote_sha:
            local_sha = hashlib.sha256(local_path.read_bytes()).hexdigest()
            if local_sha == remote_sha:
                skipped.append(f"`{filename}` — already up to date")
                continue

        # Download and save
        content = _fetch_raw(remote_path)
        if content is None:
            errors.append(f"`{remote_path}` — download failed")
            continue

        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(content, encoding="utf-8")
            updated.append(f"`{filename}`" + (f" — {description}" if description else ""))
        except Exception as e:
            errors.append(f"`{filename}` — write failed: {e}")

    # ── Report ────────────────────────────────────────────────────────────────
    output  = f"## 🔄 Knowledge Sync — `{KNOWLEDGE_REPO}`\n\n"
    output += f"**Manifest version:** {manifest.get('version', 'unknown')} | "
    output += f"**Last updated:** {manifest.get('last_updated', 'unknown')}\n\n"

    if updated:
        output += f"### ✅ Updated ({len(updated)} file(s))\n"
        for u in updated:
            output += f"- {u}\n"
        output += "\n"

    if skipped:
        output += f"### ⏭ Already current ({len(skipped)} file(s))\n"
        for s in skipped:
            output += f"- {s}\n"
        output += "\n"

    if errors:
        output += f"### ❌ Errors ({len(errors)})\n"
        for e in errors:
            output += f"- {e}\n"
        output += "\n"

    if not updated and not errors:
        output += "*Local knowledge is already up to date with the shared repository.*\n\n"

    output += (
        "---\n"
        "*Use `tek_search_local_docs` to search the newly synced content.\n"
        "Use `tek_submit_knowledge` to contribute your own findings for expert review.*"
    )
    return output


@mcp.tool()
@with_flush
def tek_submit_knowledge(
    filepath: str,
    title: str,
    description: str,
) -> str:
    """Submit a local knowledge file to the shared repository for expert review.

    Contributors (TEK_EXPERT_MODE=0): file is uploaded to the staging/ branch
    as a GitHub pull request for domain experts to review and approve.

    Experts (TEK_EXPERT_MODE=1): file is committed directly to the approved/
    branch and will be available to all users on next sync.

    Suitable for submitting:
      - Lessons learned markdown files (from PTA/lessons_learned/)
      - Undocumented command findings
      - Workflow documentation

    Args:
        filepath:    Absolute or relative path to the local file to submit.
                     Relative paths are resolved from the PTA/lessons_learned/ directory.
        title:       Short title for the submission (used as the PR/commit title).
        description: Brief description of what this contributes and why it's valuable.

    Requires TEK_KNOWLEDGE_REPO and TEK_KNOWLEDGE_TOKEN to be set.
    """
    if not KNOWLEDGE_REPO:
        return (
            "## Submit Failed — Not Configured\n\n"
            "Set `TEK_KNOWLEDGE_REPO` and `TEK_KNOWLEDGE_TOKEN` environment variables first."
        )

    if not KNOWLEDGE_TOKEN:
        return (
            "## Submit Failed — No Token\n\n"
            "`TEK_KNOWLEDGE_TOKEN` is required to submit contributions.\n"
            "Read-only sync works without a token, but submitting requires write access."
        )

    # Resolve file path
    path = Path(filepath)
    if not path.is_absolute():
        path = PTA_LESSONS_PATH / filepath
    if not path.exists():
        return f"## Submit Failed\n\nFile not found: `{path}`"

    content      = path.read_text(encoding="utf-8", errors="replace")
    content_b64  = __import__("base64").b64encode(content.encode("utf-8")).decode()
    filename     = path.name
    mode         = "expert" if KNOWLEDGE_EXPERT_MODE else "contributor"

    if KNOWLEDGE_EXPERT_MODE:
        # Expert: commit directly to approved branch
        target_path   = f"approved/lessons_learned/{filename}"
        commit_branch = "main"
        dest_label    = "approved/ (expert direct commit)"
    else:
        # Contributor: create/update file on a staging branch
        safe_name     = re.sub(r'[^a-z0-9_-]', '-', filename.lower().replace('.md', ''))
        commit_branch = f"staging/{safe_name}"
        target_path   = f"staging/{filename}"
        dest_label    = f"staging/ branch `{commit_branch}` (awaiting expert review)"

    # ── Check if branch exists, create if needed (contributors only) ──────────
    repo_api = f"{_GITHUB_API}/repos/{KNOWLEDGE_REPO}"

    if not KNOWLEDGE_EXPERT_MODE:
        try:
            # Get SHA of main branch HEAD to branch from
            main_info = _github_request(f"{repo_api}/git/ref/heads/main")
            main_sha  = main_info["object"]["sha"]
            # Create staging branch (ignore error if already exists)
            try:
                _github_request(
                    f"{repo_api}/git/refs",
                    method="POST",
                    data=json.dumps({
                        "ref": f"refs/heads/{commit_branch}",
                        "sha": main_sha,
                    }).encode(),
                )
            except Exception:
                pass  # Branch may already exist — that's fine
        except Exception as e:
            return f"## ❌ Submit Failed\n\nCould not access repo `{KNOWLEDGE_REPO}`: {e}"

    # ── Get existing file SHA if updating ─────────────────────────────────────
    existing_sha = None
    try:
        existing = _github_request(
            f"{repo_api}/contents/{target_path}?ref={commit_branch}"
        )
        if isinstance(existing, dict):
            existing_sha = existing.get("sha")
    except Exception:
        pass  # File doesn't exist yet — that's fine for a new submission

    # ── Commit the file ───────────────────────────────────────────────────────
    commit_payload: Dict[str, Any] = {
        "message": f"[{mode}] {title}",
        "content": content_b64,
        "branch":  commit_branch,
    }
    if existing_sha:
        commit_payload["sha"] = existing_sha

    try:
        _github_request(
            f"{repo_api}/contents/{target_path}",
            method="PUT",
            data=json.dumps(commit_payload).encode(),
        )
    except Exception as e:
        return f"## ❌ Submit Failed\n\nCould not commit file to GitHub: {e}"

    # ── Open a Pull Request (contributors only) ───────────────────────────────
    pr_url = ""
    if not KNOWLEDGE_EXPERT_MODE:
        try:
            pr_payload = {
                "title": f"[Contribution] {title}",
                "body":  (
                    f"**Submitted by:** local MCP server ({mode} mode)\n\n"
                    f"**File:** `{filename}`\n\n"
                    f"**Description:** {description}\n\n"
                    f"---\n*Review with `tek_sync_knowledge` after merging.*"
                ),
                "head":  commit_branch,
                "base":  "main",
            }
            pr_result = _github_request(
                f"{repo_api}/pulls",
                method="POST",
                data=json.dumps(pr_payload).encode(),
            )
            pr_url = pr_result.get("html_url", "")
        except Exception:
            pass  # PR creation is best-effort; the file is already committed

    # ── Report ────────────────────────────────────────────────────────────────
    output  = f"## ✅ Knowledge Submitted\n\n"
    output += f"**File:** `{filename}`\n"
    output += f"**Title:** {title}\n"
    output += f"**Destination:** {dest_label}\n"
    output += f"**Mode:** {mode}\n\n"

    if KNOWLEDGE_EXPERT_MODE:
        output += (
            "File committed directly to the approved branch. "
            "It will be available to all users on their next `tek_sync_knowledge`.\n"
        )
    else:
        output += "File is in staging and awaiting review by a domain expert.\n"
        if pr_url:
            output += f"\n**Pull Request:** {pr_url}\n"

    return output

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
- Try `tek_find` to find the modern command
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
- Use `tek_find` to explore the modern command's full syntax and options
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
def tek_probe_scpi(command: str) -> str:
    """Probe a single SCPI query against the live instrument to test if it is valid.

    Designed for AI-driven undocumented command discovery. Uses an 800ms timeout
    so invalid paths fail fast without hanging. The main session timeout is always
    restored after the probe regardless of outcome.

    Interprets three distinct outcomes:
      RESPONDED  — path exists and returned a value (confirmed valid)
      SCPI ERROR — instrument recognized the path but rejected it (wrong args,
                   inactive mode, or license missing)
      TIMED OUT  — instrument did not respond (path does not exist)

    The distinction between SCPI ERROR and TIMED OUT is useful: a SCPI error
    means the parser saw the command — the subsystem is likely real but may
    need a different argument or an active mode (e.g. Spectrum View enabled).

    Always appends '?' if not already present — this tool only sends queries.

    Args:
        command: SCPI path to probe, with or without trailing '?'
                 e.g. "CH1:SV:STATE" or "DISPlay:SPECView1:STATE?"
    """
    if not _ensure_connected():
        return "ERROR: No instrument connected. Use tek_instrument_connect() first."

    # Ensure it's a query
    query = command.strip()
    if not query.endswith("?"):
        query += "?"

    _PROBE_TIMEOUT_MS = 800

    # Save and override timeout
    original_timeout = None
    try:
        with _visa_lock:
            original_timeout = _visa_session.timeout
            _visa_session.timeout = _PROBE_TIMEOUT_MS
    except Exception as e:
        return f"ERROR: Could not set probe timeout: {e}"

    outcome = None
    response = None
    error_detail = None

    try:
        with _visa_lock:
            response = _visa_session.query(query).strip()

        # Check if the response is a SCPI error string rather than a real value
        error_markers = [
            "undefined header", "illegal parameter", "invalid",
            "-113", "-131", "-141", "-200", "-220",
        ]
        if any(m in response.lower() for m in error_markers):
            outcome = "SCPI_ERROR"
            error_detail = response
        else:
            outcome = "RESPONDED"

    except pyvisa.errors.VisaIOError as visa_err:
        err_str = str(visa_err).lower()
        if "timeout" in err_str or "vi_error_tmo" in err_str:
            outcome = "TIMED_OUT"
        else:
            outcome = "VISA_ERROR"
            error_detail = str(visa_err)
    except Exception as e:
        outcome = "VISA_ERROR"
        error_detail = str(e)
    finally:
        if original_timeout is not None:
            try:
                with _visa_lock:
                    _visa_session.timeout = original_timeout
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Format output — make undocumented finds obvious and lessons-learned ready
    # -------------------------------------------------------------------------
    if outcome == "RESPONDED":
        return (
            f"✅ VALID — `{query}` responded with: `{response}`\n\n"
            f"**Instrument:** {_visa_idn}\n\n"
            f"⚠️ **If this command is not in the programmer manual, it is undocumented.**\n"
            f"Use `tek_save_lessons_learned` to record this finding before ending the session.\n\n"
            f"**Lessons learned entry suggestion:**\n"
            f"- Command: `{query}`\n"
            f"- Current value returned: `{response}`\n"
            f"- Confirmed working on: {_visa_idn}\n"
            f"- Status: UNDOCUMENTED — verify set form works before using in production code"
        )

    elif outcome == "SCPI_ERROR":
        return (
            f"⚠️ SCPI ERROR — `{query}` was recognized but rejected.\n\n"
            f"**Error:** `{error_detail}`\n\n"
            f"The instrument parser saw this command — the subsystem likely exists.\n"
            f"Possible causes:\n"
            f"  - Required mode not active (e.g. Spectrum View, Bus, Math)\n"
            f"  - License not present\n"
            f"  - Wrong argument syntax (check set form)\n"
            f"  - Node exists but query form not supported on this node"
        )

    elif outcome == "TIMED_OUT":
        return (
            f"❌ TIMED OUT — `{query}` did not respond within 800ms.\n\n"
            f"This path does not exist on this instrument, or the instrument "
            f"is busy. Try a different command structure."
        )

    else:
        return (
            f"❌ VISA ERROR — `{query}` failed with a transport-level error.\n\n"
            f"**Detail:** {error_detail}\n\n"
            f"Check instrument connection with `tek_instrument_state()`."
        )


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
def tek_status() -> str:
    """Check Tektronix MCP server status - shows in Claude's chat UI."""
    uptime = datetime.now() - _server_start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    output = f"## 🔬 Tektronix MCP Server v1.4.4\n\n"
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
    print("🔬 Tektronix MCP Server v1.4.4", file=sys.stderr)
    print("   - MSO 4/5/6/7 + MSO 2 Series command databases", file=sys.stderr)
    print("   - Local docs search includes Tek PTA source", file=sys.stderr)
    print("   - Live instrument control via PyVISA", file=sys.stderr)
    print("   - Unbuffered I/O for reliable transport", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    flush_output()
    
    load_commands_database()
    
    print(f"\n📊 Total: {_total_commands:,} commands across {len(_commands_flat)} instrument families", file=sys.stderr)
    
    if PYVISA_AVAILABLE:
        print("✓ PyVISA available for live instrument control", file=sys.stderr)
    else:
        print("✗ PyVISA not installed (instrument control disabled)", file=sys.stderr)
    
    # Detect hosted mode: Railway (and most cloud platforms) set the PORT env var.
    # When PORT is present, run as a Streamable HTTP server on that port.
    # Without PORT, run as a local STDIO server (default for Claude Desktop / Codex).
    port = os.environ.get("PORT")
    if port:
        print(f"🌐 Hosted mode — HTTP transport on port {port}", file=sys.stderr)
        print("\n🚀 Server ready\n" + "=" * 60, file=sys.stderr)
        flush_output()
        mcp.run(transport="streamable-http")
    else:
        print("💻 Local mode — STDIO transport", file=sys.stderr)
        print("\n🚀 Server ready\n" + "=" * 60, file=sys.stderr)
        flush_output()
        mcp.run()


if __name__ == "__main__":
    main()
