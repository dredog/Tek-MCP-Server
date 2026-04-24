# Eye Diagram Measurement Lessons Learned

**Date:** 2026-02-04 (Updated)  
**Applies to:** MSO4/5/6 Series Oscilloscopes, Tek PTA Framework  
**Keywords:** eye diagram, jitter, HEIGHT, WIDTH, PATTERNLENGTH, DATARATE, DJ, reference waveform, acquisition, population limiting, InstrumentManager, scope_write, scope_query, TestPoint, enabled, generate_test_points, plugin lifecycle, callbacks, SAVe:IMAGe, FILESystem:READFile, HARDCopy:DATA, screenshot, VI_ERROR_TMO

---

## Critical Lessons

### 1. Reference Waveforms are STATIC - No Acquisition!

**Problem:** Test failed when using reference waveforms (REF1, REF2) because acquisition commands timed out waiting for triggers that never came.

**Root Cause:** Reference waveforms are pre-captured, static data already loaded in scope memory. There is no trigger, no acquisition - the waveform is already on screen.

**Solution:** Skip ALL acquisition commands when using reference waveforms:

```python
def run_sequence(self):
    ref_mode = self.config["source_mode"] == "REFERENCE"
    
    if ref_mode:
        # REFERENCE MODE: Waveform is already captured
        # Just ensure it's displayed and run measurements
        self._log("REFERENCE MODE: Using pre-captured waveform")
        self.inst.scope_write(f"DISplay:GLObal:{source}:STATE ON")
        time.sleep(0.5)  # Brief wait for measurements to process
    else:
        # CHANNEL MODE: Need to trigger and acquire
        self.run_acquisitions()
```

**Commands to SKIP in reference mode:**
- `ACQuire:STATE RUN`
- `ACQuire:STOPAfter SEQuence/RUNSTop`
- `ACQuire:NUMACq?`
- Any trigger configuration
- Waiting loops for acquisition completion

---

### 2. SCPI Measurement Types - Use HEIGHT and WIDTH, Not EYEHEIGHT/EYEWIDTH

**Problem:** Measurements returned errors or invalid values when using "EYEHEIGHT" and "EYEWIDTH" as measurement types.

**Root Cause:** There are NO measurement types called "EYEHEIGHT" or "EYEWIDTH" in the MSO4/5/6 SCPI command set. These were hallucinated command names.

**Correct SCPI Types:**
| Measurement | SCPI Type | Unit | Description |
|-------------|-----------|------|-------------|
| Eye Height | `HEIGHT` | V | Vertical eye opening |
| Eye Width | `WIDTH` | s | Horizontal eye opening |
| Pattern Length | `PATTERNLENGTH` | bits | Bits in repeating pattern |
| Data Rate | `DATARATE` | bps | Measured bit rate |
| Deterministic Jitter | `DJ` | s | DJ component |

**Correct Setup:**
```python
# Eye Height - uses HEIGHT, not EYEHEIGHT!
self.inst.scope_write('MEASUrement:ADDNew "MEAS1"')
self.inst.scope_write("MEASUrement:MEAS1:TYPe HEIGHT")
self.inst.scope_write(f"MEASUrement:MEAS1:SOUrce {source}")

# Eye Width - uses WIDTH, not EYEWIDTH!
self.inst.scope_write('MEASUrement:ADDNew "MEAS2"')
self.inst.scope_write("MEASUrement:MEAS2:TYPe WIDTH")
self.inst.scope_write(f"MEASUrement:MEAS2:SOUrce {source}")
```

---

### 3. Single Long Acquisition is Sufficient for Eye/Jitter Analysis

**Problem:** Initial implementation used 100 acquisitions, which was slow and unnecessary.

**Key Insight:** A single 10 µs/div acquisition captures thousands of unit intervals (UIs), which is more than enough for eye diagram and jitter statistics.

**Math:**
- At 1.62 Gbps: UI = 1/1.62e9 = 617 ps
- 10 µs/div × 10 divs = 100 µs total
- 100 µs / 617 ps = ~162,000 UIs captured in ONE acquisition

**Recommendation:** Default to `num_acquisitions = 1` for eye diagram tests:

```python
DEFAULT_CONFIG = {
    "num_acquisitions": 1,          # Single long acquisition
    "horizontal_scale_us": 10,      # 10 µs/div captures thousands of UIs
}
```

---

### 4. Population Limiting Required for Multi-Acquisition Statistics

**Problem:** When using multiple acquisitions, mean and standard deviation values were wrong.

**Root Cause:** Without population limiting, the scope computes statistics incorrectly across multiple acquisitions.

**Solution:** Enable population limiting when num_acquisitions > 1:

```python
if self.num_acquisitions > 1:
    self._log(f"Configuring population limit to {self.num_acquisitions}")
    for meas_num in [1, 2, 3, 4, 5]:
        self.inst.scope_write(f"MEASUrement:MEAS{meas_num}:POPUlation:LIMIT:STATE ON")
        self.inst.scope_write(f"MEASUrement:MEAS{meas_num}:POPUlation:LIMIT:VALue {self.num_acquisitions}")
```

---

### 5. Enable Statistics Display for On-Screen Visibility

**Tip:** Show measurement statistics in the on-screen badges for debugging and verification:

```python
self.inst.scope_write("MEASUrement:MEAS1:DISPlaystat:ENABle ON")
```

This displays mean, min, max, std dev in the measurement badge on the scope screen.

---

### 6. Clock Recovery Configuration for Eye Measurements

All eye diagram measurements require clock recovery. Use global clock recovery for consistency:

```python
# Configure global clock recovery
data_rate_hz = data_rate_gbps * 1e9
self.inst.scope_write("MEASUrement:CLOCKRecovery:MODel STANDARD")
self.inst.scope_write("MEASUrement:CLOCKRecovery:NOMINALOFFset:SELECTIONtype MANUAL")
self.inst.scope_write(f"MEASUrement:CLOCKRecovery:NOMINALOFFset {data_rate_hz}")

# Each measurement uses global clock recovery
self.inst.scope_write("MEASUrement:MEAS1:CLOCKRecovery:GLOBal 1")
```

---

### 7. Eye Diagram Plot Configuration

```python
# Create eye diagram plot
self.inst.scope_write('PLOT:ADDNew "PLOT1"')
self.inst.scope_write("PLOT:PLOT1:TYPe EYEDIAGRAM")
self.inst.scope_write(f"PLOT:PLOT1:SOUrce {source}")
self.inst.scope_write("PLOT:PLOT1:CLOCKRecovery:GLOBal ON")
self.inst.scope_write("PLOT:PLOT1:BITType ALLBits")
self.inst.scope_write("PLOT:PLOT1:STATE ON")
```

---

### 8. Test-Specific Plugin Architecture

**Best Practice:** Define measurements in the test suite plugin, not in the main framework.

```python
# In eye_diagram_test_suite.py - define WHAT this test measures
MEASUREMENTS = {
    "eye_height": {
        "scpi_type": "HEIGHT",
        "name": "Eye Height",
        "unit": "mV",
        "scale": 1000,      # V to mV
        "enabled": True,
    },
    "eye_width": {
        "scpi_type": "WIDTH",
        "name": "Eye Width", 
        "unit": "ps",
        "scale": 1e12,      # s to ps
        "enabled": True,
    },
    # ... additional measurements
}

DEFAULT_CONFIG = {
    # Which measurements to enable for this test
    "measurements_enabled": ["eye_height", "eye_width", "pattern_length", "data_rate", "dj"],
}
```

This allows different test suites to use different subsets of measurements without modifying the framework.

---

### 9. Querying Measurement Results

Use ALLAcqs for statistics across all data:

```python
mean = self.inst.scope_query(f"MEASUrement:MEAS{n}:RESUlts:ALLAcqs:MEAN?")
minimum = self.inst.scope_query(f"MEASUrement:MEAS{n}:RESUlts:ALLAcqs:MINimum?")
maximum = self.inst.scope_query(f"MEASUrement:MEAS{n}:RESUlts:ALLAcqs:MAXimum?")
stddev = self.inst.scope_query(f"MEASUrement:MEAS{n}:RESUlts:ALLAcqs:STDDev?")
```

---

### 10. Handling Invalid Measurements

Tektronix uses 9.91E+37 as the "invalid measurement" marker:

```python
def _is_valid(value):
    """Check if measurement value is valid."""
    if value is None:
        return False
    try:
        v = float(value)
        return not (abs(v) > 1e30 or math.isnan(v) or math.isinf(v))
    except (ValueError, TypeError):
        return False
```

---

## Complete Eye Diagram Measurement Setup Example

```python
def setup_eye_measurements(self, source: str):
    """Configure all eye diagram measurements."""
    data_rate_hz = self.data_rate_gbps * 1e9
    
    # Delete existing measurements
    self.inst.scope_write("MEASUrement:DELETEALL")
    
    # Configure global clock recovery
    self.inst.scope_write("MEASUrement:CLOCKRecovery:MODel STANDARD")
    self.inst.scope_write("MEASUrement:CLOCKRecovery:NOMINALOFFset:SELECTIONtype MANUAL")
    self.inst.scope_write(f"MEASUrement:CLOCKRecovery:NOMINALOFFset {data_rate_hz}")
    
    # MEAS1: Eye Height
    self.inst.scope_write('MEASUrement:ADDNew "MEAS1"')
    self.inst.scope_write("MEASUrement:MEAS1:TYPe HEIGHT")
    self.inst.scope_write(f"MEASUrement:MEAS1:SOUrce {source}")
    self.inst.scope_write("MEASUrement:MEAS1:CLOCKRecovery:GLOBal 1")
    self.inst.scope_write("MEASUrement:MEAS1:DISPlaystat:ENABle ON")
    self.inst.scope_write("MEASUrement:MEAS1:STATE ON")
    
    # MEAS2: Eye Width
    self.inst.scope_write('MEASUrement:ADDNew "MEAS2"')
    self.inst.scope_write("MEASUrement:MEAS2:TYPe WIDTH")
    self.inst.scope_write(f"MEASUrement:MEAS2:SOUrce {source}")
    self.inst.scope_write("MEASUrement:MEAS2:CLOCKRecovery:GLOBal 1")
    self.inst.scope_write("MEASUrement:MEAS2:DISPlaystat:ENABle ON")
    self.inst.scope_write("MEASUrement:MEAS2:STATE ON")
    
    # MEAS3: Pattern Length
    self.inst.scope_write('MEASUrement:ADDNew "MEAS3"')
    self.inst.scope_write("MEASUrement:MEAS3:TYPe PATTERNLENGTH")
    self.inst.scope_write(f"MEASUrement:MEAS3:SOUrce {source}")
    self.inst.scope_write("MEASUrement:MEAS3:CLOCKRecovery:GLOBal 1")
    self.inst.scope_write("MEASUrement:MEAS3:STATE ON")
    
    # MEAS4: Data Rate
    self.inst.scope_write('MEASUrement:ADDNew "MEAS4"')
    self.inst.scope_write("MEASUrement:MEAS4:TYPe DATARATE")
    self.inst.scope_write(f"MEASUrement:MEAS4:SOUrce {source}")
    self.inst.scope_write("MEASUrement:MEAS4:CLOCKRecovery:GLOBal 1")
    self.inst.scope_write("MEASUrement:MEAS4:DISPlaystat:ENABle ON")
    self.inst.scope_write("MEASUrement:MEAS4:STATE ON")
    
    # MEAS5: Deterministic Jitter (DJ)
    self.inst.scope_write('MEASUrement:ADDNew "MEAS5"')
    self.inst.scope_write("MEASUrement:MEAS5:TYPe DJ")
    self.inst.scope_write(f"MEASUrement:MEAS5:SOUrce {source}")
    self.inst.scope_write("MEASUrement:MEAS5:CLOCKRecovery:GLOBal 1")
    self.inst.scope_write("MEASUrement:MEAS5:DISPlaystat:ENABle ON")
    self.inst.scope_write("MEASUrement:MEAS5:STATE ON")
    
    # Enable statistics
    self.inst.scope_write("MEASUrement:STATistics:STATE ON")
```

---

## Summary Table

| Issue | Wrong Approach | Correct Approach |
|-------|----------------|------------------|
| Measurement type | EYEHEIGHT, EYEWIDTH | HEIGHT, WIDTH |
| Reference waveforms | Run acquisition commands | Skip acquisition, waveform is static |
| Acquisition count | 100 acquisitions | 1 long acquisition (10 µs/div) |
| Multi-acq statistics | No population limiting | Enable POPUlation:LIMIT |
| Clock recovery | Per-measurement | Global clock recovery |

---

## Tek PTA Plugin API Lessons Learned

### 11. InstrumentManager Interface - Use Correct Methods

**Problem:** Plugin crashed with `'InstrumentManager' object has no attribute 'write'`

**Root Cause:** The InstrumentManager class does NOT have direct `write()` or `query()` methods. It has instrument-specific wrapper methods.

**Correct InstrumentManager Methods:**

| Instrument | Write | Query | Wait for OPC |
|------------|-------|-------|--------------|
| Oscilloscope | `self.inst.scope_write(cmd)` | `self.inst.scope_query(cmd)` | `self.inst.scope_opc(timeout)` |
| SMU | `self.inst.smu_write(cmd)` | `self.inst.smu_query(cmd)` | N/A |
| AWG | `self.inst.awg.write(cmd)` | `self.inst.awg.query(cmd)` | N/A |

**CRITICAL:** There are NO `awg_write()` or `awg_query()` wrapper methods! Use the raw pyvisa resource directly.

**Correct Usage:**
```python
# OSCILLOSCOPE - use wrapper methods
self.inst.scope_write("MEASUrement:DELETEALL")
response = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
self.inst.scope_opc(30)  # Wait up to 30 seconds

# SMU - use wrapper methods
self.inst.smu_write("SOUR:VOLT 3.3")
current = self.inst.smu_query("MEAS:CURR?")

# AWG - use RAW pyvisa resource (NO wrapper methods!)
if self.inst.awg is not None:
    self.inst.awg.write("*RST")
    response = self.inst.awg.query("*IDN?")

# Binary read for screenshots - use raw scope resource
self.inst.scope_write("HARDCopy:DATA?")
raw_data = self.inst.scope.read_raw()
```

---

### 12. TestPoint Dataclass - All 14 Fields Required

**Problem:** Plugin crashed with `'TestPoint' object has no attribute 'enabled'`

**Root Cause:** TestPoint dataclass was missing required fields that Tek PTA expects.

**Complete TestPoint Definition (ALL fields required):**
```python
@dataclass
class TestPoint:
    test_id: int                              # Sequential ID (1, 2, 3, ...)
    name: str                                 # Display name
    nominal_value: float                      # Expected value
    unit: str                                 # Unit string ("mV", "ps", etc.)
    tolerance_pct: float = 0.0                # Tolerance percentage
    has_limits: bool = True                   # Whether to check limits
    enabled: bool = True                      # CRITICAL: Must be present!
    status: TestStatus = TestStatus.NOT_RUN   # Current status
    measured_value: float = 0.0               # Actual measured value
    error_pct: float = 0.0                    # Percentage error
    lower_limit: float = 0.0                  # Lower limit
    upper_limit: float = 0.0                  # Upper limit
    screenshot_path: str = ""                 # Screenshot file path
    extra_data: Dict[str, Any] = field(default_factory=dict)
```

**Solution:** Always copy the EXACT TestPoint definition from `tek_pta_plugin_api.py`.

---

### 13. Plugin Lifecycle - generate_test_points() Called on SELECT

**Problem:** Plugin appeared in test suite list but nothing loaded when clicked - UI remained blank.

**Root Cause:** Missing `generate_test_points()` method. This method is called when the user SELECTS the test suite (clicks the button), NOT when they click "Run".

**Plugin Lifecycle:**

| Step | User Action | Method Called | Purpose |
|------|-------------|---------------|---------|
| 1 | Clicks test suite button | `generate_test_points(config)` | Populate UI test table |
| 2 | Clicks "Run" button | `run(config)` | Execute tests |
| 3 | Clicks "Stop" button | `stop()` | Graceful shutdown |

**Correct Implementation:**
```python
def generate_test_points(self, config: Dict[str, Any] = None) -> List[TestPoint]:
    """
    CRITICAL: Called when user SELECTS the test suite.
    Must populate self.test_points AND return the list.
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
    
    return self.test_points  # MUST return the list!

def run(self, config: Dict[str, Any]) -> List[TestPoint]:
    """
    Called when user clicks Run button.
    Test points already exist from generate_test_points().
    """
    # Ensure test points exist (defensive)
    if not self.test_points:
        self.generate_test_points(config)
    
    # Execute tests using self.test_points
    for tp in self.test_points:
        # ... perform measurements ...
        pass
    
    return self.test_points
```

---

### 14. Callbacks - Must Call for UI Updates

**Problem:** Test runs but results don't update in the UI.

**Root Cause:** Not calling the callback functions that notify the UI of progress.

**Required Callbacks:**
```python
# At start of each test
tp.status = TestStatus.RUNNING
if self.on_test_start:
    self.on_test_start(tp)

# After each measurement
tp.measured_value = result
tp.status = TestStatus.PASS  # or FAIL
if self.on_test_complete:
    self.on_test_complete(tp)

# At end of all tests
if self.on_complete:
    self.on_complete(pass_count, fail_count)

# For screenshots
if self.on_screenshot:
    self.on_screenshot(screenshot_path)
```

---

### 15. First Steps for Plugin Development

**CRITICAL:** Before writing ANY plugin code, ALWAYS examine these files first:

1. **`tek_pta_plugin_api.py`** - Official plugin API with base classes
2. **`TEK_PTA_PLUGIN_GUIDE.md`** - Development guide with patterns
3. **`TEK_PTA_API_REFERENCE.md`** - Complete API reference
4. **Working examples** in `test_suites/` folder

Use the Tektronix MCP server to search documentation:
```python
tek_search_local_docs("InstrumentManager scope_write")
tek_search_local_docs("generate_test_points plugin")
tek_search_local_docs("TestPoint enabled")
```

---

### 16. Screenshot Capture - Use SAVe:IMAGe, Not HARDCopy:DATA?

**Problem:** Screenshot capture times out with `VI_ERROR_TMO` after 30 seconds.

**Log Example:**
```
SCOPE << HARDCopy STARt
SCOPE << HARDCopy:DATA?
Screenshot error: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.
```

**Root Cause:** `HARDCopy:DATA?` tries to render and transfer the entire image in one operation. For complex displays (eye diagrams, multiple plots), this exceeds the VISA timeout.

**Solution:** Use the **Save-then-Transfer** pattern:

```python
def _take_screenshot(self, output_dir: Path, name: str) -> str:
    """Capture screenshot using SAVe:IMAGe (reliable method)"""
    try:
        timestamp = time.strftime("%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = output_dir / filename
        
        # Scope temp file path
        scope_temp_path = "C:/Temp/tek_pta_screenshot.png"
        
        # Step 1: Save image to scope filesystem
        self.inst.scope_write(f'SAVe:IMAGe "{scope_temp_path}"')
        self.inst.scope_opc(15)  # Wait for save to complete
        time.sleep(0.3)
        
        # Step 2: Transfer file from scope to PC
        self.inst.scope_write(f'FILESystem:READFile "{scope_temp_path}"')
        
        # Increase timeout for file transfer (60 seconds)
        old_timeout = self.inst.scope.timeout
        self.inst.scope.timeout = 60000
        try:
            raw_data = self.inst.scope.read_raw()
        finally:
            self.inst.scope.timeout = old_timeout
        
        # Step 3: Parse IEEE 488.2 block header
        if raw_data[0:1] == b'#':
            num_digits = int(raw_data[1:2])
            data_length = int(raw_data[2:2+num_digits])
            image_data = raw_data[2+num_digits:2+num_digits+data_length]
        else:
            image_data = raw_data
        
        # Step 4: Save locally
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Step 5: Clean up temp file on scope
        try:
            self.inst.scope_write(f'FILESystem:DELEte "{scope_temp_path}"')
        except Exception:
            pass
        
        return str(filepath)
        
    except Exception as e:
        self._log(f"Screenshot error: {e}")
        return ""
```

**Why This Works:**
| Method | What Happens | Issue |
|--------|--------------|-------|
| `HARDCopy:DATA?` | Renders + transfers in one step | Timeout on complex displays |
| `SAVe:IMAGe` + `FILESystem:READFile` | Saves to file, then transfers | Reliable, file already exists |

---

## Plugin API Quick Reference

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

*End of Eye Diagram Lessons Learned*
