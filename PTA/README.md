# Tek PTA - Production Test Assistant

**Location:** `%USERPROFILE%\TektronixMCP\PTA\`

## Quick Start

1. **Install** (one time):
   - Double-click `INSTALL_TekPTA.bat`
   - This adds Tek PTA dependencies to the MCP server virtual environment

2. **Run**:
   - Double-click `Run_TekPTA.bat`
   - Or create a desktop shortcut to it

## Directory Structure

```
%USERPROFILE%\TektronixMCP\
├── venv\                    ← Shared virtual environment
├── tektronix_mcp_server.py  ← MCP server
├── PTA\                     ← Tek PTA (this folder)
│   ├── tek_pta.py
│   ├── Run_TekPTA.bat
│   ├── INSTALL_TekPTA.bat
│   └── test_suites\
│       └── example_suites.py
```

## Files

| File | Description |
|------|-------------|
| `tek_pta.py` | Main application |
| `Run_TekPTA.bat` | Launcher (double-click to run) |
| `INSTALL_TekPTA.bat` | One-time installer |
| `requirements_pta.txt` | Python dependencies |
| `test_suites/` | Plugin folder for test suites |

## Test Suites

Test suites are loaded from multiple locations:

1. **Default:** `test_suites/` folder (always checked)
2. **Config file:** Paths listed in `tek_pta_config.json`
3. **Environment variable:** `TEK_PTA_PLUGIN_DIRS` (semicolon-separated)

### Built-in Example

- `test_suites/example_suites.py` - AFG Frequency, LED Current, Spectrum Scanner tests

### Using Custom Plugin Folders

**Option 1: Config file** (recommended)

Create `tek_pta_config.json` in the PTA folder:
```json
{
    "plugin_directories": [
        "C:\\Users\\YourName\\MyTestSuites",
        "%USERPROFILE%\\Documents\\TekTests"
    ],
    "priority_instruments": [
        "169.254.10.36",
        "169.254.165.92"
    ]
}
```

- `plugin_directories`: Folders to search for test suite plugins
- `priority_instruments`: IP addresses to check first during instrument discovery

**Option 2: Environment variable**

Set `TEK_PTA_PLUGIN_DIRS` to a semicolon-separated list of paths:
```cmd
set TEK_PTA_PLUGIN_DIRS=C:\MyTests;D:\ProjectTests
```

Or add it to Run_TekPTA.bat before the python line.

## Reference Waveforms

The Reference Waveforms feature allows you to run tests using pre-recorded waveform files instead of live acquisition. This is useful for:

- Testing with known-good waveforms
- Debugging test logic without hardware
- Reproducing specific test conditions
- Training and demonstrations

### How to Use

1. Go to **Configure → References** tab
2. Check **"Use Reference Waveforms instead of Live Acquisition"**
3. Specify which test numbers to apply (e.g., "all" or "1-5,10,15-20")
4. Browse and select waveform files for REF1-REF4
5. Click **"Load to Scope"** to transfer files to the oscilloscope
6. Run your test suite

### Channel Mapping

| Reference | Replaces |
|-----------|----------|
| REF1 | CH1 |
| REF2 | CH2 |
| REF3 | CH3 |
| REF4 | CH4 |

### Supported File Formats

- `.WFM` - Tektronix waveform format
- `.ISF` - Internal Save Format
- `.CSV` - Comma-separated values

### Behavior in Reference Mode

- **No acquisition commands** are sent to the scope
- Measurements are taken from the loaded reference waveforms
- Vertical and horizontal scales can still be adjusted
- Configuration is saved per test suite
- Files must be accessible from the oscilloscope (local drive, USB, or network path)

### Adding New Tests

1. Create a new `.py` file in any plugin directory
2. Define your tests using `TestSuitePlugin`
3. Add a `register_suites()` function that returns your tests
4. Restart Tek PTA - new tests appear automatically

Or use the **Import...** button to load test suites from any location.

## Requirements

- Python 3.8+
- Tektronix MCP Server installed (provides venv with PyVISA)
- Pillow, reportlab, matplotlib (installed by INSTALL_TekPTA.bat)

## Reference Waveforms

Instead of using live signals, you can load saved waveform files to reference channels and run tests against them.

**Supported formats:** `.WFM`, `.ISF`, `.CSV`

**Usage:**
1. Go to the **References** tab
2. Browse for waveform files and assign to REF1-REF4
3. Click **Load to Scope** to transfer files to the oscilloscope
4. Check **"Use Reference Waveforms instead of Live Channels"**
5. Run your tests - measurements will use REF channels

**Channel mapping:**
| Reference | Replaces |
|-----------|----------|
| REF1 | CH1 |
| REF2 | CH2 |
| REF3 | CH3 |
| REF4 | CH4 |

**Note:** Waveform files must be accessible from the oscilloscope (local drive, USB, or network path).

## Contact

Andre Asbury - andre.asbury@tektronix.com
