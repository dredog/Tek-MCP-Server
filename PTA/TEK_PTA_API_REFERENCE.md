# Tek PTA Plugin API Reference

**Version:** 2.0 (Validated against tek_pta.py)  
**Last Updated:** 2026-02-04

---

## CRITICAL: First Steps for Plugin Development

**Before writing ANY plugin code, you MUST examine these files:**

1. **`tek_pta_plugin_api.py`** - Official plugin API with base classes
2. **`TEK_PTA_PLUGIN_GUIDE.md`** - Development guide with patterns and examples
3. **`TEK_PTA_PLUGIN_ARCHITECTURE.md`** - Architecture overview
4. **Working plugin examples** in `test_suites/` folder

Use the Tektronix MCP server to search these:
```
tek_search_local_docs("InstrumentManager scope_write")
tek_search_local_docs("generate_test_points plugin")
```

---

## Table of Contents

1. [InstrumentManager Interface](#1-instrumentmanager-interface)
2. [TestPoint Dataclass](#2-testpoint-dataclass)
3. [TestStatus Enum](#3-teststatus-enum)
4. [TestSuitePlugin Dataclass](#4-testsuiteplugin-dataclass)
5. [TestEngineBase Class](#5-testenginebase-class)
6. [Plugin Lifecycle](#6-plugin-lifecycle)
7. [Callback Functions](#7-callback-functions)
8. [Screenshot Capture](#8-screenshot-capture)
9. [Common Errors and Solutions](#9-common-errors-and-solutions)
10. [Complete Plugin Template](#10-complete-plugin-template)

---

## 1. InstrumentManager Interface

The `InstrumentManager` instance is passed to your engine's `__init__` and stored as `self.inst`.

### Oscilloscope Methods (Wrapper Methods with SCPI Logging)

| Method | Signature | Description |
|--------|-----------|-------------|
| `scope_write` | `scope_write(cmd: str) -> None` | Send SCPI command to oscilloscope |
| `scope_query` | `scope_query(cmd: str, timeout: int = None) -> str` | Query oscilloscope, returns stripped response |
| `scope_opc` | `scope_opc(timeout: int = 30) -> None` | Wait for *OPC? with timeout (seconds) |
| `scope_wait_acquisition` | `scope_wait_acquisition(timeout: int = 10) -> bool` | Poll ACQuire:STATE until acquisition completes |

### SMU Methods (Wrapper Methods with SCPI Logging)

| Method | Signature | Description |
|--------|-----------|-------------|
| `smu_write` | `smu_write(cmd: str) -> None` | Send SCPI command to SMU |
| `smu_query` | `smu_query(cmd: str) -> str` | Query SMU, returns stripped response |

### Raw PyVISA Resources (For Binary Operations)

**IMPORTANT:** There are NO `awg_write`/`awg_query` wrapper methods. Use the raw resources directly.

| Attribute | Type | Description |
|-----------|------|-------------|
| `scope` | `pyvisa.Resource` or `None` | Raw oscilloscope resource |
| `smu` | `pyvisa.Resource` or `None` | Raw SMU resource |
| `awg` | `pyvisa.Resource` or `None` | Raw AWG/AFG resource |

### Instrument Info Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `scope_info` | `InstrumentInfo` or `None` | Oscilloscope info (model, serial, etc.) |
| `smu_info` | `InstrumentInfo` or `None` | SMU instrument info |
| `awg_info` | `InstrumentInfo` or `None` | AWG/AFG instrument info |

### InstrumentInfo Dataclass

```python
@dataclass
class InstrumentInfo:
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    firmware_version: str = ""
    visa_address: str = ""
    instrument_type: str = "Unknown"  # "Oscilloscope", "SMU", "Function Generator"
    is_connected: bool = False
```

### Usage Examples

```python
# ===== OSCILLOSCOPE (use wrapper methods) =====
self.inst.scope_write("MEASUrement:DELETEALL")
response = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
self.inst.scope_opc(30)  # Wait up to 30 seconds

# Wait for acquisition to complete
self.inst.scope_write("ACQuire:STOPAfter SEQuence")
self.inst.scope_write("ACQuire:STATE RUN")
if self.inst.scope_wait_acquisition(10):
    self.log("Acquisition complete")

# Binary read for screenshots (use raw resource)
self.inst.scope_write("HARDCopy:DATA?")
raw_data = self.inst.scope.read_raw()

# ===== SMU (use wrapper methods) =====
self.inst.smu_write("SOUR:VOLT 3.3")
current = self.inst.smu_query("MEAS:CURR?")

# ===== AWG (NO wrapper methods - use raw resource) =====
if self.inst.awg is not None:
    self.inst.awg.write("*RST")
    idn = self.inst.awg.query("*IDN?")
    self.inst.awg.write("OUTP1:STAT ON")

# Check if instruments are connected
if self.inst.scope is None:
    self.log("ERROR: No oscilloscope connected")
    return
if self.inst.awg is not None:
    self.log(f"AWG connected: {self.inst.awg_info.model}")
```

---

## 2. TestPoint Dataclass

**CRITICAL:** Your TestPoint definition MUST match this EXACTLY or Tek PTA will crash.

```python
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class TestPoint:
    # REQUIRED - no defaults (must be provided)
    test_id: int                              # Sequential ID (1, 2, 3, ...)
    name: str                                 # Display name ("Input 1 Eye Height")
    nominal_value: float                      # Expected value in display units
    unit: str                                 # Unit string ("mV", "ps", "Gbps")
    
    # REQUIRED - have defaults but MUST be present in dataclass
    tolerance_pct: float = 0.0                # Tolerance percentage
    has_limits: bool = True                   # Whether to check limits
    enabled: bool = True                      # CRITICAL: Must be True to run
    status: TestStatus = TestStatus.NOT_RUN   # Current test status
    measured_value: float = 0.0               # Actual measured value
    error_pct: float = 0.0                    # Percentage error from nominal
    lower_limit: float = 0.0                  # Lower limit (0 = no lower check)
    upper_limit: float = 0.0                  # Upper limit (0 = no upper check)
    screenshot_path: str = ""                 # Path to screenshot file
    extra_data: Dict[str, Any] = field(default_factory=dict)  # Additional data
```

### Creating Test Points

```python
# Basic test point with tolerance
tp = TestPoint(
    test_id=1,
    name="Output Voltage",
    nominal_value=3.3,
    unit="V",
    tolerance_pct=5.0,  # ±5%
)
# lower_limit and upper_limit will be 0.0 (calculated from tolerance during run)

# Test point with explicit limits
tp = TestPoint(
    test_id=2,
    name="Eye Height",
    nominal_value=0,        # Info-only, no nominal
    unit="mV",
    lower_limit=250.0,      # Must be >= 250 mV
    upper_limit=0.0,        # No upper limit (0 means no check)
)

# Info-only test point (no pass/fail)
tp = TestPoint(
    test_id=3,
    name="Pattern Length",
    nominal_value=127,
    unit="bits",
    has_limits=False,       # Info only - no pass/fail checking
)
```

---

## 3. TestStatus Enum

```python
from enum import Enum

class TestStatus(Enum):
    NOT_RUN = "Not Run"     # Initial state
    RUNNING = "Running"     # Currently executing
    PASS = "PASS"           # Test passed (NOTE: uppercase "PASS")
    FAIL = "FAIL"           # Test failed (NOTE: uppercase "FAIL")
    ERROR = "ERROR"         # Error during execution
    SKIPPED = "Skipped"     # Test was skipped (disabled)
```

### Usage

```python
# Setting status
tp.status = TestStatus.RUNNING
tp.status = TestStatus.PASS

# Checking status - use enum comparison
if tp.status == TestStatus.PASS:
    pass_count += 1

# For cross-module compatibility, use .value
if tp.status.value == "PASS":
    pass_count += 1
```

---

## 4. TestSuitePlugin Dataclass

```python
@dataclass
class TestSuitePlugin:
    name: str                       # Display name in sidebar
    description: str                # Description shown in UI
    test_type: str                  # UNIQUE identifier (e.g., "my_jitter_test")
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Optional[Type] = None  # Your TestEngineBase subclass
    config_panel_builder: Optional[Callable] = None  # Custom config UI
    setup_diagram_generator: Optional[Callable] = None  # Custom setup diagram
    results_columns: Optional[List[tuple]] = None  # Custom result columns
```

### Registration Function (REQUIRED)

Every plugin file MUST have this function:

```python
def register_suites() -> List[TestSuitePlugin]:
    """Register test suites with Tek PTA"""
    return [
        TestSuitePlugin(
            name="My Jitter Test",
            description="Measures jitter on high-speed serial signals",
            test_type="my_jitter_test",  # MUST be unique across all plugins!
            config={
                "data_rate": 5e9,
                "source1": "CH1",
                "source2": "CH2",
            },
            required_instruments=["Oscilloscope"],
            engine_class=MyJitterEngine,
        )
    ]
```

---

## 5. TestEngineBase Class

### Required Attributes (initialize in `__init__`)

```python
class TestEngineBase:
    def __init__(self, instrument_manager):
        self.inst = instrument_manager          # InstrumentManager instance
        self.test_points: List[TestPoint] = []  # Test point list
        self.running = False                    # Test running flag
        self.output_dir = None                  # Output directory (set by Tek PTA)
        self.reference_config = None            # ReferenceConfig (if using refs)
        
        # Callbacks - set by Tek PTA before calling methods
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[float, str], None]] = None
        self.on_test_start: Optional[Callable[[TestPoint], None]] = None
        self.on_test_complete: Optional[Callable[[TestPoint], None]] = None
        self.on_screenshot: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[int, int], None]] = None
```

### Required Methods

| Method | When Called | Purpose |
|--------|-------------|---------|
| `generate_test_points(config)` | User **SELECTS** test suite | Populate UI test table |
| `run(config)` | User clicks **Run** | Execute tests |
| `stop()` | User clicks **Stop** | Graceful shutdown |

### Helper Methods (provided by base class)

```python
def log(self, message: str):
    """Log message to UI"""
    if self.on_log:
        self.on_log(message)

def progress(self, percentage: float, message: str):
    """Update progress bar (0-100) and status"""
    if self.on_progress:
        self.on_progress(percentage, message)
```

---

## 6. Plugin Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                     PLUGIN LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. USER CLICKS TEST SUITE BUTTON                               │
│     └─► Tek PTA calls: engine.generate_test_points(config)      │
│         └─► You: Create TestPoint objects                       │
│         └─► You: Store in self.test_points                      │
│         └─► You: Return the list                                │
│         └─► UI displays test table                              │
│                                                                 │
│  2. USER CLICKS "RUN" BUTTON                                    │
│     └─► Tek PTA calls: engine.run(config)                       │
│         └─► Test points already exist from step 1               │
│         └─► You: Iterate through self.test_points               │
│         └─► You: Set tp.status = RUNNING, call on_test_start    │
│         └─► You: Perform measurement                            │
│         └─► You: Set tp.measured_value and tp.status            │
│         └─► You: Call on_test_complete                          │
│         └─► You: Call on_complete(passed, failed) at end        │
│                                                                 │
│  3. USER CLICKS "STOP" BUTTON                                   │
│     └─► Tek PTA calls: engine.stop()                            │
│         └─► You: Set self.running = False                       │
│         └─► Your run() loop checks self.running and exits       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**CRITICAL:** If `generate_test_points()` is not implemented or returns empty, the UI will show an empty test table and nothing happens when clicked!

---

## 7. Callback Functions

### on_log

```python
def _log(self, msg: str):
    """Log message to Tek PTA log window"""
    if self.on_log:
        self.on_log(msg)
```

### on_progress

```python
def _progress(self, pct: float, msg: str = ""):
    """Update progress bar (0-100) and status message"""
    if self.on_progress:
        self.on_progress(pct, msg)
```

### on_test_start / on_test_complete

```python
# During run():
for i, tp in enumerate(self.test_points):
    tp.status = TestStatus.RUNNING
    if self.on_test_start:
        self.on_test_start(tp)
    
    # ... perform measurement ...
    tp.measured_value = result
    tp.status = TestStatus.PASS  # or FAIL
    
    if self.on_test_complete:
        self.on_test_complete(tp)
```

### on_screenshot

```python
screenshot_path = self._capture_screenshot("eye_diagram")
if screenshot_path and self.on_screenshot:
    self.on_screenshot(screenshot_path)
```

### on_complete

```python
# At end of run():
if self.on_complete:
    self.on_complete(pass_count, fail_count)
```

---

## 8. Screenshot Capture

### Recommended Pattern: Save to Scope, Transfer to PC

```python
def _capture_screenshot(self, label: str) -> str:
    """Capture screenshot using SAVe:IMAGe and FILESystem:READFile"""
    if not self.output_dir:
        return ""
    
    try:
        timestamp = time.strftime("%H%M%S")
        filename = f"{label}_{timestamp}.png"
        local_path = self.output_dir / filename
        
        # Try multiple scope paths (C:/Temp preferred)
        scope_paths = ["C:/Temp/screenshot.png", "C:/screenshot.png"]
        
        for scope_path in scope_paths:
            try:
                # Save image on scope
                self.inst.scope_write(f'SAVe:IMAGe "{scope_path}"')
                self.inst.scope_opc(10)
                
                # Transfer to PC via binary read
                self.inst.scope_write(f'FILESystem:READFile "{scope_path}"')
                raw_data = self.inst.scope.read_raw()
                
                # Parse IEEE 488.2 block header (#<n><length><data>)
                if raw_data[0:1] == b'#':
                    num_digits = int(raw_data[1:2])
                    data_length = int(raw_data[2:2+num_digits])
                    image_data = raw_data[2+num_digits:2+num_digits+data_length]
                else:
                    image_data = raw_data
                
                # Save locally
                with open(local_path, 'wb') as f:
                    f.write(image_data)
                
                # Delete temp file on scope
                self.inst.scope_write(f'FILESystem:DELEte "{scope_path}"')
                
                self._log(f"Screenshot saved: {filename}")
                return str(local_path)
                
            except Exception:
                continue  # Try next path
        
        return ""
        
    except Exception as e:
        self._log(f"Screenshot error: {e}")
        return ""
```

---

## 9. Common Errors and Solutions

### Error: 'TestPoint' object has no attribute 'enabled'

**Cause:** TestPoint dataclass missing required fields.

**Solution:** Copy the EXACT TestPoint definition from Section 2.

---

### Error: 'InstrumentManager' object has no attribute 'write'

**Cause:** Using `self.inst.write()` instead of `self.inst.scope_write()`.

**Solution:**
```python
# WRONG
self.inst.write(cmd)

# CORRECT
self.inst.scope_write(cmd)
```

---

### Error: 'InstrumentManager' object has no attribute 'query'

**Cause:** Using `self.inst.query()` instead of `self.inst.scope_query()`.

**Solution:**
```python
# WRONG
self.inst.query(cmd)

# CORRECT
self.inst.scope_query(cmd)
```

---

### Error: 'InstrumentManager' object has no attribute 'awg_write'

**Cause:** There are NO `awg_write`/`awg_query` wrapper methods.

**Solution:** Use the raw pyvisa resource:
```python
# WRONG
self.inst.awg_write(cmd)

# CORRECT
if self.inst.awg is not None:
    self.inst.awg.write(cmd)
    response = self.inst.awg.query(cmd)
```

---

### Error: Empty test table when clicking test suite

**Cause:** `generate_test_points()` not implemented or returns empty.

**Solution:** Implement `generate_test_points()`:
```python
def generate_test_points(self, config=None):
    self.test_points = []
    # Create test points...
    self.test_points.append(TestPoint(...))
    return self.test_points  # MUST return the list
```

---

### Error: Test runs but results don't update in UI

**Cause:** Not calling callbacks.

**Solution:** Call callbacks during run():
```python
tp.status = TestStatus.RUNNING
if self.on_test_start:
    self.on_test_start(tp)

# ... measure ...

tp.status = TestStatus.PASS
if self.on_test_complete:
    self.on_test_complete(tp)
```

---

## 10. Complete Plugin Template

```python
#!/usr/bin/env python3
"""
My Custom Test Suite for Tek PTA
"""

import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


# =============================================================================
# PLUGIN API DEFINITIONS (copy from tek_pta_plugin_api.py for portability)
# =============================================================================

class TestStatus(Enum):
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "Skipped"


@dataclass
class TestPoint:
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
    name: str
    description: str
    test_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Optional[type] = None


class TestEngineBase:
    def __init__(self, instrument_manager):
        self.inst = instrument_manager
        self.test_points: List[TestPoint] = []
        self.running = False
        self.output_dir = None
        self.reference_config = None
        
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[float, str], None]] = None
        self.on_test_start: Optional[Callable[[TestPoint], None]] = None
        self.on_test_complete: Optional[Callable[[TestPoint], None]] = None
        self.on_screenshot: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[int, int], None]] = None
    
    def log(self, msg: str):
        if self.on_log:
            self.on_log(msg)
    
    def progress(self, pct: float, msg: str = ""):
        if self.on_progress:
            self.on_progress(pct, msg)
    
    def stop(self):
        self.running = False


# =============================================================================
# TEST ENGINE IMPLEMENTATION
# =============================================================================

class MyTestEngine(TestEngineBase):
    """Custom test engine"""
    
    # Define your measurements
    MEASUREMENTS = [
        # (name, nominal, lower_limit, upper_limit, unit)
        ("Voltage", 3.3, 3.135, 3.465, "V"),      # ±5%
        ("Current", 100.0, 90.0, 110.0, "mA"),    # ±10%
        ("Frequency", 1e6, 0.99e6, 1.01e6, "Hz"), # ±1%
    ]
    
    def generate_test_points(self, config: Dict[str, Any] = None) -> List[TestPoint]:
        """
        CRITICAL: Called when user SELECTS the test suite.
        Must populate self.test_points and return the list.
        """
        self.test_points = []
        
        for i, (name, nominal, lower, upper, unit) in enumerate(self.MEASUREMENTS):
            tp = TestPoint(
                test_id=i + 1,
                name=name,
                nominal_value=nominal,
                unit=unit,
                lower_limit=lower,
                upper_limit=upper,
            )
            self.test_points.append(tp)
        
        return self.test_points
    
    def run(self, config: Dict[str, Any]) -> List[TestPoint]:
        """
        Called when user clicks Run button.
        Test points already exist from generate_test_points().
        """
        self.running = True
        
        # Ensure test points exist
        if not self.test_points:
            self.generate_test_points(config)
        
        # Check scope connection
        if self.inst.scope is None:
            self.log("ERROR: No oscilloscope connected")
            return self.test_points
        
        pass_count = 0
        fail_count = 0
        total = len(self.test_points)
        
        try:
            self.log("=" * 60)
            self.log("STARTING TEST")
            self.log("=" * 60)
            
            # Initialize scope
            self.inst.scope_write("*CLS")
            self.inst.scope_write("HEADer OFF")
            
            for i, tp in enumerate(self.test_points):
                if not self.running:
                    self.log("Test stopped by user")
                    break
                
                # Update progress
                self.progress((i / total) * 100, f"Testing: {tp.name}")
                
                # Notify test start
                tp.status = TestStatus.RUNNING
                if self.on_test_start:
                    self.on_test_start(tp)
                
                try:
                    # === YOUR MEASUREMENT LOGIC HERE ===
                    # Example: Read a measurement
                    # result = float(self.inst.scope_query("MEASUrement:MEAS1:VALue?"))
                    result = tp.nominal_value * 1.02  # Simulated measurement
                    
                    tp.measured_value = result
                    
                    # Evaluate pass/fail
                    if tp.lower_limit > 0 and result < tp.lower_limit:
                        tp.status = TestStatus.FAIL
                    elif tp.upper_limit > 0 and result > tp.upper_limit:
                        tp.status = TestStatus.FAIL
                    else:
                        tp.status = TestStatus.PASS
                    
                    # Calculate error percentage
                    if tp.nominal_value != 0:
                        tp.error_pct = ((result - tp.nominal_value) / tp.nominal_value) * 100
                    
                    if tp.status == TestStatus.PASS:
                        pass_count += 1
                        self.log(f"  ✓ {tp.name}: {result:.4f} {tp.unit}")
                    else:
                        fail_count += 1
                        self.log(f"  ✗ {tp.name}: {result:.4f} {tp.unit} (FAIL)")
                    
                except Exception as e:
                    tp.status = TestStatus.ERROR
                    tp.extra_data['error'] = str(e)
                    fail_count += 1
                    self.log(f"  ERROR {tp.name}: {e}")
                
                # Notify test complete
                if self.on_test_complete:
                    self.on_test_complete(tp)
            
            self.log("=" * 60)
            self.log(f"COMPLETE: {pass_count} passed, {fail_count} failed")
            self.log("=" * 60)
            
        except Exception as e:
            self.log(f"FATAL ERROR: {e}")
        
        finally:
            self.running = False
            self.progress(100, "Complete")
            
            if self.on_complete:
                self.on_complete(pass_count, fail_count)
        
        return self.test_points


# =============================================================================
# PLUGIN REGISTRATION (REQUIRED)
# =============================================================================

TEST_SUITE_INFO = TestSuitePlugin(
    name="My Custom Test",
    description="Description of what this test does.\n\nLine 2 of description.",
    test_type="my_custom_test",  # MUST be unique!
    config={
        "param1": 10,
        "param2": "value",
    },
    required_instruments=["Oscilloscope"],
    engine_class=MyTestEngine,
)


def register_suites() -> List[TestSuitePlugin]:
    """Register test suites with Tek PTA"""
    return [TEST_SUITE_INFO]


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing plugin structure...")
    
    # Test registration
    suites = register_suites()
    print(f"Registered {len(suites)} suite(s)")
    
    # Test engine with mock instrument manager
    class MockInstrumentManager:
        scope = None
        scope_info = None
        def scope_write(self, cmd): print(f"  SCOPE << {cmd}")
        def scope_query(self, cmd): return "0"
        def scope_opc(self, t): pass
    
    engine = MyTestEngine(MockInstrumentManager())
    
    # Test generate_test_points
    test_points = engine.generate_test_points({})
    print(f"\nGenerated {len(test_points)} test points:")
    for tp in test_points:
        print(f"  {tp.test_id}. {tp.name}: [{tp.lower_limit} to {tp.upper_limit}] {tp.unit}")
    
    print("\n✓ Plugin structure valid")
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEK PTA QUICK REFERENCE                      │
├─────────────────────────────────────────────────────────────────┤
│ SCPI COMMUNICATION                                              │
│   self.inst.scope_write(cmd)         # Send command             │
│   self.inst.scope_query(cmd)         # Query, returns string    │
│   self.inst.scope_opc(30)            # Wait for OPC (seconds)   │
│   self.inst.scope.read_raw()         # Binary read (raw pyvisa) │
│                                                                 │
│   self.inst.smu_write(cmd)           # SMU command              │
│   self.inst.smu_query(cmd)           # SMU query                │
│                                                                 │
│   self.inst.awg.write(cmd)           # AWG (raw pyvisa)         │
│   self.inst.awg.query(cmd)           # AWG (raw pyvisa)         │
├─────────────────────────────────────────────────────────────────┤
│ LOGGING                                                         │
│   self.log("Message")                # Log to UI                │
│   self.progress(50, "Halfway")       # Update progress bar      │
├─────────────────────────────────────────────────────────────────┤
│ PLUGIN LIFECYCLE                                                │
│   generate_test_points(config)       # Called on suite SELECT   │
│   run(config)                        # Called on Run button     │
│   stop()                             # Called on Stop button    │
├─────────────────────────────────────────────────────────────────┤
│ CALLBACKS                                                       │
│   self.on_test_start(tp)             # Notify test starting     │
│   self.on_test_complete(tp)          # Notify test done         │
│   self.on_complete(passed, failed)   # Notify all done          │
│   self.on_screenshot(path)           # Notify screenshot taken  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Validated against tek_pta.py source code on 2026-02-04*
