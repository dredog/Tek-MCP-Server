# Tektronix MCP Server v3.2
## Complete System Documentation

**Version:** 3.2  
**Date:** January 2026  
**Author:** Andre Asbury, Tektronix Application Engineer

---

## 🎯 What Is This?

The **Tektronix MCP Server** is a Claude Desktop integration that provides authoritative SCPI command references for automating Tektronix test equipment. It ensures Claude never invents SCPI commands—all automation code uses verified syntax from official Tektronix documentation.

**Key Principle:** NEVER invent SCPI commands. Every command must be verified.

---

## 📊 Current Capabilities

### Command Databases (11 instrument families, 17,000+ commands)

| Family | File | Commands | Instruments |
|--------|------|----------|-------------|
| MSO 4/5/6 Series | mso_commands.json | ~2,300 | MSO44/B, MSO46/B, MSO54/B, MSO56/B, MSO58/B, MSO64/B, MSO66/B, MSO68/B, LPD64 |
| MSO 2 Series | mso2_series_commands.json | ~1,800 | MSO22, MSO24 |
| MDO 3 Series | mdo3_series_commands.json | ~2,100 | MDO32, MDO34 |
| MDO4000/MSO4000B | mdo4000_mso4000b_...json | ~2,500 | MDO4014B-MDO4104C, MSO4014B-MSO4104B, DPO4014B-DPO4104B |
| MSO/DPO 5k/7k/70k | MSO_DPO_5k_7k_70K_commands.json | ~2,400 | MSO5034-MSO5204, DPO5034-DPO5204, DPO7054-DPO7354, MSO/DPO70000 series |
| DPO70000 Series | dpo70k_commands.json | ~1,800 | DPO70404-DPO77002SX, MSO70404C-MSO73304DX |
| AFG31000 Series | afg31000-commands.json | ~190 | AFG31021, AFG31051, AFG31101, AFG31151, AFG31251 |
| AWG5200 Series | awg5200_commands.json | ~1,200 | AWG5202, AWG5204, AWG5208 |
| AWG70000 Series | awg70000_commands.json | ~1,300 | AWG70001A/B, AWG70002A/B |
| SignalVu | signalvu-commands.json | ~200 | SignalVu-PC, RSA306B, RSA500/600 |
| Keithley SMU | smu_commands.json | ~400 | 2450, 2460, 2461, 2470 |

**Total: ~17,000 verified SCPI commands**

### MCP Tools Available

| Tool | Purpose | Speed |
|------|---------|-------|
| `tek_search_commands` | Search commands by keyword | Fast (50-100ms) |
| `tek_get_command` | Get detailed command syntax | Fast |
| `tek_list_groups` | List all command groups | Fast |
| `tek_get_group_commands` | Get all commands in a group | Fast |
| `tek_list_instruments` | Show loaded instrument databases | Fast |
| `tek_search_local_docs` | Search markdown documentation | Fast |
| `tek_vector_search` | Search OpenAI vector store | Medium (1-3s) |
| `tek_comprehensive_search` | Multi-tier intelligent search | Variable |
| `tek_get_test_template` | Get Python test templates | Fast |
| `tek_status` | Check server status | Instant |

---

## 🏗️ Package Structure

```
TektronixMCP/
├── tektronix_mcp_server.py      # Main MCP server (1,200 lines)
├── requirements.txt              # Python dependencies
├── INSTALL.bat                   # Windows installer (MCP + PTA)
├── INSTALL_TekPTA_Only.bat       # PTA-only installer
├── README.md                     # Quick start guide
│
├── docs/
│   ├── instrument_commands_json/ # SCPI command databases (11 files)
│   │   ├── mso_commands.json
│   │   ├── mso2_series_commands.json
│   │   ├── mdo3_series_commands.json
│   │   ├── mdo4000_mso4000b_dpo4000b_mdo3000_commands.json
│   │   ├── MSO_DPO_5k_7k_70K_commands.json
│   │   ├── dpo70k_commands.json
│   │   ├── afg31000-commands.json
│   │   ├── awg5200_commands.json
│   │   ├── awg70000_commands.json
│   │   ├── signalvu-commands.json
│   │   └── smu_commands.json
│   │
│   └── reference/                # Markdown documentation (searchable)
│       ├── Tektronix_Automation_Guidelines.md
│       ├── TEK_PTA_AUTOMATION_GUIDE.md
│       ├── measurement_workflow_Andre.md
│       └── TEKTRONIX_MCP_README.md (this file)
│
└── PTA/                          # Production Test Assistant
    ├── tek_pta.py                # GUI application (3,700+ lines)
    ├── tek_pta_config.json       # Configuration
    ├── tek_pta_plugin_api.py     # Plugin system
    ├── requirements_pta.txt      # PTA dependencies
    ├── Run_TekPTA.bat            # Launcher
    └── test_suites/              # Custom test plugins
```

---

## 🔍 Search Hierarchy

When you ask Claude about SCPI commands, it searches in this order:

```
┌─────────────────────────────────────────────────────────────┐
│  TIER 1: Local JSON Database (50-100ms)                     │
│  ├── 11 instrument command databases                        │
│  └── 17,000+ verified SCPI commands                         │
│  ✓ AUTHORITATIVE - Commands verified from official manuals  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼ (If not found)
┌─────────────────────────────────────────────────────────────┐
│  TIER 1.5: Local Markdown Docs (100-200ms)                  │
│  ├── Tektronix_Automation_Guidelines.md (FAE knowledge)     │
│  ├── TEK_PTA_AUTOMATION_GUIDE.md (lessons learned)          │
│  └── measurement_workflow_Andre.md (workflows & examples)   │
│  ✓ Best practices, code patterns, troubleshooting           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼ (If vector store configured)
┌─────────────────────────────────────────────────────────────┐
│  TIER 2: OpenAI Vector Store (1-3s) - OPTIONAL              │
│  └── ~80 Tektronix reference documents                      │
│  ✓ Complex procedural questions, application notes          │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼ (Fallback)
┌─────────────────────────────────────────────────────────────┐
│  TIER 3: Web Search - tek.com (3-5s)                        │
│  └── Claude's built-in web search                           │
│  ⚠ Last resort for newest content                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 Documentation Files

### Tektronix_Automation_Guidelines.md
**Purpose:** High-level FAE reference for SCPI automation

Key topics covered:
- SCPI command syntax rules (set vs query, NR3 format)
- Impedance/termination commands by family
- Display configuration (stacked vs overlay)
- Probe and external attenuator setup
- Horizontal mode (AUTO vs MANUAL)
- Status and error handling (IEEE-488.2)
- Spectrum View commands
- Measurement statistics and pass/fail
- TekVISA vs NI-VISA guidance
- Waveform transfer methods
- Links to programmer manuals

### TEK_PTA_AUTOMATION_GUIDE.md  
**Purpose:** Lessons learned from Production Test Assistant development

Key topics covered:
- Critical checklist before every test
- Oscilloscope communication setup (HEADer OFF!)
- Keithley 2450 SMU programming (TSP vs SCPI)
- Measurement setup patterns
- Current measurement via shunt resistor
- Pass/fail criteria and error calculations
- Screenshot capture
- Common gotchas and solutions

### measurement_workflow_Andre.md
**Purpose:** Comprehensive test automation workflows

Key topics covered:
- Complete measurement workflow (9,000+ lines)
- Code development checklist
- AFG setup sequences
- Channel configuration patterns
- Jitter measurement guidelines
- OPC handling for synchronization
- Plotting and visualization
- Complete working code examples

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TEK_INSTALL_PATH` | No | Override install location |
| `OPENAI_API_KEY` | For Tier 2 | OpenAI API key for vector store |
| `TEK_VECTOR_STORE_ID` | For Tier 2 | Vector store ID (vs_xxxxxxx) |

### Claude Desktop Configuration

The installer automatically configures `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tektronix": {
      "command": "path/to/venv/python",
      "args": ["path/to/tektronix_mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "your-key-here",
        "TEK_VECTOR_STORE_ID": "vs_xxxxxxx"
      }
    }
  }
}
```

---

## 🚀 Quick Start

### Installation (Windows)

```batch
# Full install (MCP Server + Tek PTA)
INSTALL.bat

# Or PTA only (for test benches without Claude)
INSTALL_TekPTA_Only.bat
```

### Verify Installation

In Claude Desktop, ask:
> "What is your Tektronix MCP server status?"

Expected response shows:
- Server version
- Loaded instruments and command counts
- Vector store status

### Run Tek PTA

```batch
%USERPROFILE%\TektronixMCP\PTA\Run_TekPTA.bat
```

---

## 🎯 Usage Examples

### Find Commands
> "How do I set the horizontal scale on an MSO64B?"

Claude searches `tek_search_commands` → finds `HORizontal:SCAle` with full syntax.

### Get Detailed Syntax
> "Show me the full syntax for CH1:SCAle including examples"

Claude uses `tek_get_command` → returns arguments, description, examples.

### Procedural Questions
> "What's the proper sequence for setting up measurements?"

Claude searches local docs → finds workflow in measurement_workflow_Andre.md.

### Generate Code
> "Write Python code to measure frequency with pass/fail limits"

Claude combines:
1. SCPI commands from JSON databases
2. Best practices from Automation_Guidelines
3. Code patterns from measurement_workflow

---

## 🔗 Reference Links

### Programmer Manuals
- [MSO 4/5/6 Series](https://www.tek.com/en/manual/oscilloscope/4-5-6-series-mso-programmer-manual)
- [DPO70000 Series](https://www.tek.com/en/manual/oscilloscope/dpo70000sx-programmer-manual)
- [AFG31000 Series](https://www.tek.com/en/signal-generator/afg31000-function-generator-manual)
- [Keithley 2450](https://www.tek.com/en/keithley-source-measure-units/keithley-smu-2400-series-sourcemeter-manual)

### Getting Started Guides
- [Oscilloscope Automation with Python](https://dev.tek.com/en/getting-started-guides/getting-started-with-oscilloscope-automation-and-python)
- [tm_devices Library](https://dev.tek.com/en/getting-started-guides/simplifying-test-automation-with-tmdevices-and-python)
- [TekHSI High-Speed Interface](https://dev.tek.com/en/getting-started-guides/getting-started-with-high-speed-interface-how-to-guide)

### Developer Resources
- [Tektronix Developer Portal](https://dev.tek.com)
- [TekVISA Download](https://www.tek.com/en/support/software/driver/tekvisa-connectivity-software-v5111)

---

## 📋 Python Requirements

| Component | Minimum Python | Reason |
|-----------|----------------|--------|
| MCP Server | 3.10+ | `mcp`, `fastmcp` packages |
| Tek PTA (standalone) | 3.9+ | matplotlib 3.5+ |

### MCP Server Dependencies
```
mcp>=1.0.0
fastmcp>=2.0.0
pydantic>=2.0.0
openai>=1.0.0  # Optional, for vector store
pyvisa>=1.14.0
pyvisa-py>=0.7.0
```

### Tek PTA Dependencies
```
pyvisa>=1.14.0
pyvisa-py>=0.7.0
Pillow>=9.0.0
reportlab>=4.0.0
matplotlib>=3.5.0
```

---

## 🆘 Troubleshooting

### MCP Server Not Appearing in Claude
1. Check Claude Desktop config file location
2. Verify Python path in config is correct
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### "Command not found" Errors
1. Verify instrument family is correct
2. Try broader search terms
3. Check if command exists for your specific model
4. Use `tek_list_instruments` to see loaded databases

### Vector Store Not Working
1. Verify OPENAI_API_KEY is set
2. Verify TEK_VECTOR_STORE_ID is set
3. Check API key has vector store access
4. Server works without vector store (uses local search)

### Tek PTA Won't Start
1. Run from command prompt to see errors
2. Verify all dependencies installed
3. Check Python version (3.9+)
4. Try: `pip install pyvisa pyvisa-py Pillow reportlab matplotlib`

---

*End of Tektronix MCP Server Documentation v3.2*
