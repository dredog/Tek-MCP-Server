# Tektronix MCP System Structure

## Overview

The Tektronix MCP (Model Context Protocol) system provides Claude with tools to help users create test automation for Tektronix instruments. It supports two approaches:

1. **Simple Python Scripts** - Standalone terminal scripts for quick measurements
2. **Tek PTA Plugins** - Full GUI integration with the Production Test Assistant

## Directory Structure

```
TektronixMCP/                          # INSTALL_BASE
├── tektronix_mcp_server.py            # ★ MCP Server (this file)
│
├── docs/                              # Documentation & data
│   ├── reference/                     # Markdown documentation
│   │   ├── legacy_command_mappings.json
│   │   ├── TEKTRONIX_MCP_SYSTEM_STRUCTURE.md  # System overview
│   │   └── *.md                       # Other guides
│   │
│   ├── instrument_commands_json/      # SCPI command databases
│   │   ├── mso_2_4_5_6_7_commands.json      # MSO/DPO modern scopes
│   │   ├── mdo3_series_commands.json        # MDO3 series
│   │   ├── mdo4000_*.json                   # MDO4000/MSO4000B/DPO4000B
│   │   ├── MSO_DPO_5k_7k_70K_commands.json  # Legacy 5k/7k/70k
│   │   ├── afg31000_commands.json           # AFG31000 series
│   │   ├── awg5200_commands.json            # AWG5200 series
│   │   ├── awg70000_commands.json           # AWG70000 series
│   │   ├── hss_plugin_commands.json         # High Speed Serial plugin
│   │   ├── signalvu_commands.json           # SignalVu
│   │   └── smu_commands.json                # Keithley SMU
│   │
│   ├── programmer_manuals/            # PDF manuals (reference only)
│   └── python_examples/               # Example scripts
│
├── PTA/                               # Tek PTA Application
│   ├── tek_pta.py                    # ★ Main GUI application (~3,700 lines)
│   ├── tek_pta_plugin_api.py         # ★ Plugin API definitions
│   ├── TEK_PTA_PLUGIN_GUIDE.md       # ★ Plugin development guide (move here!)
│   │
│   ├── test_suites/                   # Plugin files (user creates these)
│   │   ├── prbs7_dut_test_suite.py   # Example: PRBS7 testing
│   │   ├── agc_sample_test_suite.py  # Example: AGC testing
│   │   ├── led_current_test_suite.py # Example: LED I-V curves
│   │   └── your_custom_test.py       # User's plugins go here
│   │
│   ├── lessons_learned/               # Knowledge capture
│   │   └── *.md                       # Auto-indexed by search
│   │
│   └── backups/                       # Automatic backups
│
└── README.md                          # Setup instructions
```

## Files You Need to Update

When updating the system, these are the key files:

| File | Purpose | When to Update |
|------|---------|----------------|
| `tektronix_mcp_server.py` | MCP server with all tools | Adding new tools, fixing bugs |
| `PTA/TEK_PTA_PLUGIN_GUIDE.md` | Plugin development guide | When plugin structure changes |
| `PTA/tek_pta.py` | Main GUI application | Adding GUI features |
| `PTA/tek_pta_plugin_api.py` | Plugin API classes | When API changes (rarely) |

## Two Approaches to Test Automation

### Approach 1: Simple Python Script (Terminal)

**Best for:**
- Quick one-off measurements
- Learning SCPI commands
- Simple pass/fail checks
- Integration into existing systems

**Structure:**
```python
#!/usr/bin/env python3
"""Simple measurement script"""
import pyvisa

def main():
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource("TCPIP::192.168.1.100::INSTR")
    # ... configure and measure ...
    scope.close()

if __name__ == "__main__":
    main()
```

**MCP Tool:** `tek_get_test_template("basic")` or `tek_get_test_template("power_supply")`

---

### Approach 2: Tek PTA Plugin (GUI)

**Best for:**
- Production testing with multiple test points
- Tests that need pass/fail limits and statistics
- PDF reports with Tektronix branding
- Operator-friendly interface
- Repeated testing with logging

**Structure:**
```python
#!/usr/bin/env python3
"""Tek PTA Plugin - requires specific structure"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum

class TestStatus(Enum): ...
@dataclass
class TestPoint: ...
@dataclass
class TestSuitePlugin: ...
class TestEngineBase: ...

class MyEngine(TestEngineBase):
    def generate_test_points(self, config): ...
    def setup_instruments(self, config): ...
    def run_single_test(self, test_point, config): ...
    def run(self, config): ...

def register_suites():  # REQUIRED!
    return [TestSuitePlugin(...)]
```

**MCP Tool:** `tek_pta_plugin_template()` - MUST call this first!

---

## MCP Server Tools Reference

### SCPI Command Tools
| Tool | Purpose |
|------|---------|
| `tek_search_commands(query, instrument)` | Search for SCPI commands |
| `tek_get_command(scpi, instrument)` | Get command details |
| `tek_list_groups(instrument)` | List command groups |
| `tek_get_group_commands(group, instrument)` | Get all commands in a group |
| `tek_list_instruments()` | List supported instruments |
| `tek_legacy_command_lookup(command)` | Find modern equivalent of legacy command |

### Documentation Tools
| Tool | Purpose |
|------|---------|
| `tek_search_local_docs(query)` | Search markdown docs and Python files |
| `tek_vector_search(query)` | Search OpenAI vector store |
| `tek_comprehensive_search(query)` | Combined search |

### Tek PTA Plugin Tools
| Tool | Purpose |
|------|---------|
| `tek_pta_plugin_template()` | **CALL FIRST!** Get correct plugin structure |
| `tek_pta_plugin_checklist()` | Development checklist |

### Templates
| Tool | Purpose |
|------|---------|
| `tek_get_test_template("basic")` | Simple frequency measurement |
| `tek_get_test_template("power_supply")` | DC + ripple measurement |
| `tek_get_test_template("signal_integrity")` | Jitter measurement |
| `tek_get_test_template("waveform_capture")` | Capture to CSV |

### Knowledge Capture
| Tool | Purpose |
|------|---------|
| `tek_save_lessons_learned(...)` | Save knowledge for future sessions |
| `tek_list_lessons_learned()` | List saved lessons |

### Status
| Tool | Purpose |
|------|---------|
| `tek_status()` | Server status and loaded databases |

---

## Workflow: Claude Should Ask First!

When a user asks to create a test, Claude should ASK which approach they want:

> "I can help you create this test. Which approach would you prefer?
> 
> 1. **Simple Python script** - Runs from terminal, quick to write, good for one-off measurements
> 2. **Tek PTA plugin** - Full GUI with pass/fail limits, PDF reports, operator interface
> 
> Which would work better for your needs?"

This prevents wasted effort creating the wrong type of solution.
