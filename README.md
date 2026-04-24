# Tektronix MCP Server v3.2 + Tek PTA

## What's Included

| Component | Description | Python Required |
|-----------|-------------|-----------------|
| **MCP Server** | Claude Desktop integration with 16,989 verified SCPI commands | 3.10+ |
| **Tek PTA** | Standalone GUI for automated hardware testing | 3.9+ |

## Quick Install (Windows)

### Option 1: Full Installation (MCP + Tek PTA)
**Requires Python 3.10+**

1. Extract the zip file
2. Double-click `INSTALL.bat`
3. Restart Claude Desktop
4. Test: Ask Claude "What is your Tektronix MCP server status?"

### Option 2: Tek PTA Only (no Claude integration)
**Requires Python 3.9+** - Ideal for production test benches

1. Extract the zip file
2. Double-click `INSTALL_TekPTA_Only.bat`
3. Run: `%USERPROFILE%\TektronixMCP\PTA\Run_TekPTA.bat`

## Directory Structure After Installation

```
%USERPROFILE%\TektronixMCP\
├── venv\                           ← Shared virtual environment
├── tektronix_mcp_server.py         ← MCP server for Claude
├── requirements.txt
├── docs\
│   ├── instrument_commands_json\   ← 11 SCPI command databases
│   └── reference\                  ← Searchable markdown documentation
│       ├── Tektronix_Automation_Guidelines.md
│       ├── TEK_PTA_AUTOMATION_GUIDE.md
│       ├── measurement_workflow_Andre.md
│       └── TEKTRONIX_MCP_README.md
├── PTA\                            ← Tek PTA folder
│   ├── tek_pta.py                  ← Main application
│   ├── Run_TekPTA.bat              ← Launcher
│   ├── tek_pta_config.json         ← Configuration
│   └── test_suites\                ← Test plugins
```

## Supported Instruments (MCP Server)

### Oscilloscopes - Modern Series
| Key | Commands | Models |
|-----|----------|--------|
| mso456 | 2,753 | MSO44/B - MSO68/B, LPD64 |
| mso2 | 2,679 | MSO22, MSO24 |
| mdo3 | 3,374 | MDO32, MDO34 |

### Oscilloscopes - Legacy Series
| Key | Commands | Models |
|-----|----------|--------|
| mdo4000_mso4000b_dpo4000b_mdo3000 | 3,788 | MDO4000/B/C, MSO4000B, DPO4000B |
| mso_dpo_5k_7k_70k | 1,481 | MSO/DPO 5000, 7000 series |
| dpo70k | 1,782 | DPO/MSO/DSA 70000 series |

### Signal Generators
| Key | Commands | Models |
|-----|----------|--------|
| afg31000 | 189 | AFG31021-AFG31252 |
| awg5200 | 314 | AWG5202, AWG5204, AWG5208 |
| awg70000 | 364 | AWG70001A/B, AWG70002A/B |

### Other
| Key | Commands | Models |
|-----|----------|--------|
| signalvu | 202 | SignalVu-PC, RSA306B-RSA607A |
| smu | 63 | Keithley 2400-2651A series |

**Total: 16,989 verified SCPI commands**

## Manual Install / Mac / Linux

1. Copy files to preferred location (e.g., `~/TektronixMCP/`)

2. Create virtual environment:
   ```bash
   cd ~/TektronixMCP
   python3 -m venv venv
   source venv/bin/activate  # Mac/Linux
   # or: venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure Claude Desktop:
   
   **Config file locations:**
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`
   
   ```json
   {
     "mcpServers": {
       "tektronix": {
         "command": "/path/to/TektronixMCP/venv/bin/python",
         "args": ["/path/to/TektronixMCP/tektronix_mcp_server.py"],
         "env": {
           "TEK_INSTALL_PATH": "/path/to/TektronixMCP",
           "OPENAI_API_KEY": "YOUR_API_KEY_HERE",
           "TEK_VECTOR_STORE_ID": "YOUR_VECTOR_STORE_ID_HERE"
         }
       }
     }
   }
   ```

5. Restart Claude Desktop

## Troubleshooting

### "Python not found"
Install from https://python.org and check "Add Python to PATH"

### "Module not found" errors
```bash
cd %USERPROFILE%\TektronixMCP
venv\Scripts\activate
pip install -r requirements.txt
```

### Claude doesn't see the MCP server
1. Check `claude_desktop_config.json` paths
2. Restart Claude Desktop completely (quit, not minimize)
3. Windows paths need double backslashes: `C:\\Users\\...`

### Tek PTA won't start
Run from command line to see errors:
```bash
cd %USERPROFILE%\TektronixMCP\PTA
..\venv\Scripts\python.exe tek_pta.py
```

## Contact

Andre Asbury - andre.asbury@tektronix.com
