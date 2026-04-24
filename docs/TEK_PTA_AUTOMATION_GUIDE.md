# Tek PTA Automation Development Guide

## Overview

This guide captures lessons learned from developing the Tek PTA (Production Test Assistant) platform. It covers oscilloscope automation, SMU programming, measurement setup, and common pitfalls to avoid. Use this as a reference when developing custom test automation programs.

---

## ⚠️ CRITICAL CHECKLIST - Before Every Test

**Run through this checklist mentally before writing any test automation code:**

### SCPI Command Verification
- [ ] **NEVER assume a command exists** - verify in JSON database, vector store, or tek.com
- [ ] Use `tek_search_commands` or `tek_get_command` to verify syntax
- [ ] Commands like `MEASUrement:MEAS1:TYPe` use MEAS1, MEAS2, etc. not arbitrary names

### Scope Communication Setup
- [ ] `FACtory` - reset to known state at start of each test
- [ ] `HEADer OFF` - sent after every FACtory reset or connection
- [ ] `VERBose OFF` - for short responses
- [ ] `*CLS` - clear any error conditions

### Channel Configuration  
- [ ] Correct channel enabled (`DISplay:WAVEView1:CH{n}:STATE ON`)
- [ ] All OTHER channels disabled (factory default turns CH1 on!)
- [ ] Correct termination:
  - 50Ω for direct connections, BNC cables, antennas, signal generators
  - 1MΩ for passive probes
- [ ] Correct bandwidth (FULL for RF/spectrum, or limited like 20MHz for noise reduction)
- [ ] Correct coupling (DC, AC, or GND)

### Trigger Configuration
- [ ] Trigger SOURCE set to measurement channel (`TRIGger:A:EDGE:SOUrce CH{n}`)
- [ ] Trigger TYPE appropriate (EDGE for most signals)
- [ ] Trigger LEVEL set correctly (not just 0 - what voltage/current do you expect?)
- [ ] Trigger MODE (NORMAL for waiting, AUTO for DC/no-edge signals)
- [ ] Trigger SLOPE (RISe, FALL, or EITHER)

### Horizontal (Timebase)
- [ ] Scale appropriate to show 2-3 cycles for AC, or sufficient for DC settling
- [ ] Avoid roll mode (stay below 40ms/div unless specifically needed)

### Vertical (Amplitude)
- [ ] Scale sized for signal (not too much empty space, not clipping)
- [ ] **Check for clipping with `CH<x>:CLIPping?`** - returns 1 if clipping
- [ ] Auto-scale if clipping detected before measurements
- [ ] Offset set to center the expected signal
- [ ] For current measurement: external attenuation and units configured

### Measurement Setup
- [ ] Measurement type correct (MEAN for DC, FREQUENCY for AC, etc.)
- [ ] Measurement source is the correct channel

### Acquisition
- [ ] Know when to wait for trigger vs force trigger
- [ ] Timeout handling for no-trigger situations

---

## Table of Contents

1. [Oscilloscope Communication](#oscilloscope-communication)
2. [Keithley 2450 SMU Programming](#keithley-2450-smu-programming)
3. [Measurement Setup Patterns](#measurement-setup-patterns)
4. [Pass/Fail Criteria](#passfail-criteria)
5. [Screenshot Capture](#screenshot-capture)
6. [Common Gotchas](#common-gotchas)
7. [Test Engine Architecture](#test-engine-architecture)
8. [Reference Test Implementations](#reference-test-implementations)

---

## Oscilloscope Communication

### Connection Setup

```python
import pyvisa

rm = pyvisa.ResourceManager()
scope = rm.open_resource("TCPIP::192.168.1.100::INSTR")
scope.timeout = 30000  # 30 seconds for long operations
scope.read_termination = '\n'
scope.write_termination = '\n'
```

### Critical First Commands After Connection

**Always send these commands immediately after connecting:**

```python
scope.write("*CLS")          # Clear status registers
scope.write("HEADer OFF")    # CRITICAL: Returns "0" instead of ":ACQUIRE:STATE 0"
scope.write("VERBose OFF")   # Short form responses
```

> ⚠️ **GOTCHA**: Without `HEADer OFF`, query responses include the command prefix (e.g., `:ACQUIRE:STATE 0` instead of just `0`), which breaks `float()` parsing.

### After Factory Reset

Factory reset (`FACtory`) turns headers back on. **Always re-send header commands after reset:**

```python
scope.write("FACtory")
scope.query("*OPC?")  # Wait for completion (can take 10-30 seconds)
scope.write("HEADer OFF")   # Must re-send after FACtory!
scope.write("VERBose OFF")
```

### Using *OPC? vs *OPC

| Command | Use Case | Behavior |
|---------|----------|----------|
| `*OPC?` | Long operations (FACtory, AUTOSet) | Blocks until complete, returns "1" |
| `*OPC` | Short operations | Sets OPC bit in status register |

**Best practice**: Only use `*OPC?` for operations that genuinely take time:
- `FACtory` - 10-30 seconds
- `AUTOSet` - 5-15 seconds
- Large data transfers

**Don't use for**: Simple write commands, channel settings, trigger setup.

### Acquisition Control

```python
# Single acquisition (recommended for measurements)
scope.write("ACQuire:STOPAfter SEQuence")  # Stop after one acquisition
scope.write("ACQuire:STATE RUN")            # Start acquisition

# Wait for acquisition to complete
def wait_acquisition(scope, timeout=10):
    """Poll acquisition state until complete"""
    start = time.time()
    while time.time() - start < timeout:
        state = scope.query("ACQuire:STATE?")
        if state.strip() == "0":  # 0 = stopped (acquisition complete)
            return True
        time.sleep(0.1)
    return False
```

> ⚠️ **GOTCHA**: `ACQuire:STATE?` returns "1" while running, "0" when stopped. Don't confuse this with success/failure.

### Querying Probe Information

For test reports, you may want to document which probes were used:

```python
def get_probe_info(scope, ch: int) -> dict:
    """Get probe type and serial number for a channel"""
    info = {"type": "", "serial": "", "connected": False}
    try:
        # Query probe type
        probe_type = scope.query(f"CH{ch}:PRObe:ID:TYPe?").strip().strip('"')
        if probe_type and probe_type not in ["", "0", "NONE", "UNKNOWN"]:
            info["type"] = probe_type
            info["connected"] = True
            # Try to get serial number
            try:
                serial = scope.query(f"CH{ch}:PRObe:ID:SERnumber?").strip().strip('"')
                if serial and serial not in ["", "0", "NONE", "UNKNOWN"]:
                    info["serial"] = serial
            except Exception:
                pass
    except Exception:
        pass
    return info

# Example usage
for ch in range(1, 5):
    probe = get_probe_info(scope, ch)
    if probe["connected"]:
        print(f"CH{ch}: {probe['type']} (S/N: {probe['serial']})")
```

---

## Keithley 2450 SMU Programming

### TSP vs SCPI: Know Your Command Language

The 2450 supports two command languages. **They cannot be mixed!**

| Language | Example Command | When to Use |
|----------|-----------------|-------------|
| **TSP** | `smu.source.func = smu.FUNC_DC_VOLTAGE` | Default on many units, Lua-like syntax |
| **SCPI** | `SOUR:FUNC VOLT` | Traditional instrument syntax |

> ⚠️ **CRITICAL GOTCHA**: If you see error `-285: TSP syntax error at line 1: unexpected symbol near ':'`, you're sending SCPI commands to a unit in TSP mode.

### TSP Commands (Recommended)

Use TSP commands - they're more readable and most examples use them:

```python
# Reset
smu.write("reset()")
time.sleep(0.5)  # Allow reset to complete

# Configure voltage source, measure current
smu.write("smu.source.func = smu.FUNC_DC_VOLTAGE")
smu.write("smu.source.level = 3.5")           # Set voltage
smu.write("smu.source.ilimit.level = 0.1")    # Current limit (compliance)
smu.write("smu.source.readback = smu.ON")     # Enable source readback

# Configure current measurement
smu.write("smu.measure.func = smu.FUNC_DC_CURRENT")
smu.write("smu.measure.autorange = smu.ON")
smu.write("smu.measure.nplc = 1")             # Integration time (1 = 1 power line cycle)

# Enable output
smu.write("smu.source.output = smu.ON")
time.sleep(0.3)  # Allow settling

# Take measurement
smu.write("smu.measure.read()")
time.sleep(0.1)
result = smu.query("printbuffer(1, 1, defbuffer1.readings)")
current_amps = float(result.strip())

# Disable output
smu.write("smu.source.output = smu.OFF")
```

### TSP Command Reference

| Operation | TSP Command |
|-----------|-------------|
| Reset | `reset()` |
| Source voltage | `smu.source.func = smu.FUNC_DC_VOLTAGE` |
| Source current | `smu.source.func = smu.FUNC_DC_CURRENT` |
| Set voltage level | `smu.source.level = {value}` |
| Set current level | `smu.source.level = {value}` |
| Voltage limit (compliance) | `smu.source.vlimit.level = {value}` |
| Current limit (compliance) | `smu.source.ilimit.level = {value}` |
| Measure voltage | `smu.measure.func = smu.FUNC_DC_VOLTAGE` |
| Measure current | `smu.measure.func = smu.FUNC_DC_CURRENT` |
| Auto range | `smu.measure.autorange = smu.ON` |
| Fixed range | `smu.measure.range = {value}` |
| NPLC (integration) | `smu.measure.nplc = {0.01 to 10}` |
| Output on | `smu.source.output = smu.ON` |
| Output off | `smu.source.output = smu.OFF` |
| Take reading | `smu.measure.read()` |
| Get reading | `printbuffer(1, 1, defbuffer1.readings)` |
| Get source value | `printbuffer(1, 1, defbuffer1.sourcevalues)` |

### SCPI Commands (Alternative)

If you must use SCPI (no leading colons, double quotes for strings):

```python
smu.write("*RST")
smu.write("SOUR:FUNC VOLT")
smu.write("SOUR:VOLT 3.5")
smu.write("SOUR:VOLT:ILIM 0.1")
smu.write('SENS:FUNC "CURR"')  # Note: double quotes
smu.write("SENS:CURR:RANG:AUTO ON")
smu.write("OUTP ON")
result = smu.query("READ?")
```

> ⚠️ **GOTCHA**: SCPI commands do NOT have leading colons (`:SOUR:FUNC` is wrong, `SOUR:FUNC` is correct).

---

## Measurement Setup Patterns

### Current Measurement via Shunt Resistor

**Circuit:**
```
SMU HI → Load → Shunt Resistor (R_shunt) → SMU LO
                      ↑
                Scope probe here
```

**Scope Configuration for Current Display:**

```python
ch = 3  # Channel number
R_shunt = 10  # Ohms

# Basic channel setup
scope.write(f"CH{ch}:COUPling DC")
scope.write(f"CH{ch}:TERmination 1E6")  # High-Z for passive probe

# Bandwidth limiting - reduces noise for slow signals
scope.write(f"CH{ch}:BANdwidth 20E6")  # 20 MHz limit

# CRITICAL: External attenuation for V to A conversion
# Attenuation factor = 1 / R_shunt
# This makes the scope display in Amps directly!
atten_factor = 1.0 / R_shunt  # 0.1 for 10Ω shunt
scope.write(f"CH{ch}:PROBEFunc:EXTAtten {atten_factor}")

# CRITICAL: Enable alternate units (required to activate the conversion)
scope.write(f"CH{ch}:PROBEFunc:EXTUnits:STATE ON")
# Units default to "A" (Amps), so no need to set explicitly
```

> ⚠️ **GOTCHA**: `EXTUnits:STATE ON` is REQUIRED to enable the unit conversion. Just setting `EXTAtten` and `EXTUnits "A"` is not enough!

> ⚠️ **GOTCHA**: After this setup, the scope returns current in **Amps**, not voltage. Do NOT divide by R_shunt again in your code!

### Frequency Measurement Setup

```python
ch = 1

# Channel setup
scope.write(f"CH{ch}:COUPling DC")
scope.write(f"CH{ch}:TERmination 50")  # 50Ω for direct BNC connection

# Trigger setup
scope.write("TRIGger:A:TYPE EDGE")
scope.write(f"TRIGger:A:EDGE:SOUrce CH{ch}")
scope.write("TRIGger:A:EDGE:SLOpe RISe")
scope.write("TRIGger:A:MODe NORMal")  # Normal trigger for repetitive signals

# Measurement setup
scope.write('MEASUrement:DELETEALL')
scope.write('MEASUrement:ADDNew "MEAS1"')
scope.write("MEASUrement:MEAS1:TYPe FREQuency")
scope.write(f"MEASUrement:MEAS1:SOUrce CH{ch}")
scope.write("MEASUrement:MEAS1:STATE ON")

# Read frequency
result = scope.query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
frequency_hz = float(result)
```

### Timebase Calculation for Waveform Display

**Goal**: Show 2-2.5 cycles on screen for good visualization.

```python
def calculate_timebase(frequency_hz):
    """Calculate timebase to show ~2.5 cycles on 10 divisions"""
    period = 1.0 / frequency_hz
    # 10 divisions, want 2.5 cycles: each cycle needs 4 divisions
    target_scale = period / 4  # seconds per division
    
    # Round to nice oscilloscope values
    nice_values = [1e-9, 2e-9, 4e-9, 5e-9, 10e-9, 20e-9, 40e-9, 50e-9, 100e-9,
                   200e-9, 400e-9, 500e-9, 1e-6, 2e-6, 4e-6, 5e-6, 10e-6,
                   20e-6, 40e-6, 50e-6, 100e-6, 200e-6, 400e-6, 500e-6, 1e-3,
                   2e-3, 4e-3, 5e-3, 10e-3, 20e-3, 40e-3, 50e-3, 100e-3,
                   200e-3, 400e-3, 500e-3, 1, 2, 4, 5, 10]
    
    scale = min((s for s in nice_values if s >= target_scale), default=1e-3)
    return scale

# Apply
scope.write(f"HORizontal:SCAle {calculate_timebase(1000)}")  # For 1kHz
```

### Vertical Auto-Scaling

```python
def auto_scale_vertical(scope, ch, expected_peak_to_peak):
    """Set vertical scale to show signal at ~80% of screen"""
    # Want signal to fill ~80% of 8 divisions
    target_scale = expected_peak_to_peak / (8 * 0.8)
    
    nice_values = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 
                   0.1, 0.2, 0.5, 1, 2, 5, 10]
    scale = min((s for s in nice_values if s >= target_scale), default=1)
    
    scope.write(f"CH{ch}:SCAle {scale}")
```

---

## Pass/Fail Criteria

### Percentage Error Calculation

```python
def calculate_error_percent(measured, expected):
    """Calculate percentage error from expected value"""
    if expected == 0:
        return float('inf') if measured != 0 else 0
    return ((measured - expected) / expected) * 100

# Pass/fail check
tolerance_pct = 2.5  # ±2.5%
error = calculate_error_percent(scope_current, smu_current)

if abs(error) <= tolerance_pct:
    status = "PASS"
else:
    status = "FAIL"
```

### Limit Calculation

```python
def calculate_limits(nominal, tolerance_pct):
    """Calculate upper and lower limits from nominal value"""
    tolerance_fraction = tolerance_pct / 100
    lower = nominal * (1 - tolerance_fraction)
    upper = nominal * (1 + tolerance_fraction)
    return lower, upper
```

### Test Point Data Structure

```python
from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum

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
    enabled: bool = True
    status: TestStatus = TestStatus.NOT_RUN
    measured_value: float = 0.0
    error_pct: float = 0.0
    lower_limit: float = 0.0
    upper_limit: float = 0.0
    screenshot_path: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)
```

---

## Screenshot Capture

### Saving and Transferring Screenshots

MSO/MDO oscilloscopes with Linux OS save to `C:/` (which is actually root on Linux):

```python
def capture_screenshot(scope, local_path, test_id):
    """Capture screenshot from scope and transfer to local PC"""
    remote_filename = f"C:/screenshot_{test_id:03d}.png"
    
    # Save screenshot on scope
    scope.write(f'SAVe:IMAGe "{remote_filename}"')
    scope.query("*OPC?")  # Wait for save (timeout=10s usually enough)
    
    # Transfer file from scope to PC
    scope.write(f'FILESystem:READFile "{remote_filename}"')
    data = scope.read_raw()  # Binary PNG data
    
    # Save locally
    with open(local_path, 'wb') as f:
        f.write(data)
    
    # Clean up remote file (optional)
    scope.write(f'FILESystem:DELEte "{remote_filename}"')
    
    return str(local_path)
```

> ⚠️ **GOTCHA**: The file path on MSO6B (Linux-based) scopes is `C:/filename`, not `/tmp/filename` or Windows-style paths.

---

## Common Gotchas

### 1. Header Mode Breaking Parsing

**Problem**: `float(scope.query("ACQuire:STATE?"))` fails with `ValueError`

**Cause**: Header mode returns `:ACQUIRE:STATE 0` instead of `0`

**Solution**: Always send `HEADer OFF` after connecting and after `FACtory`

### 2. Double Unit Conversion

**Problem**: Current readings are 10x too small

**Cause**: External attenuation already converts V to A, but code divides by R_shunt again

**Solution**: When `EXTUnits:STATE ON` is set, scope returns current directly - don't divide again

### 3. TSP vs SCPI Mismatch

**Problem**: Error `-285: TSP syntax error`

**Cause**: Sending SCPI commands (with colons) to unit in TSP mode

**Solution**: Use TSP commands (`smu.source.func = smu.FUNC_DC_VOLTAGE`) or switch unit to SCPI mode

### 4. External Units Not Enabled

**Problem**: Scope still shows voltage despite setting `EXTAtten` and `EXTUnits`

**Cause**: `EXTUnits:STATE ON` was not sent

**Solution**: Must explicitly enable with `CH{n}:PROBEFunc:EXTUnits:STATE ON`

### 5. Acquisition State Polling

**Problem**: Measurement returns old/stale data

**Cause**: Not waiting for acquisition to complete

**Solution**: Poll `ACQuire:STATE?` until it returns `0` (stopped)

### 6. OPC Overuse Causing Timeouts

**Problem**: Simple commands timing out

**Cause**: Using `*OPC?` for commands that don't need it

**Solution**: Only use `*OPC?` for long operations (FACtory, AUTOSet, large data transfers)

### 7. SMU Output Left On

**Problem**: Circuit damage, unexpected behavior

**Cause**: Not disabling SMU output after test or on error

**Solution**: Always wrap test code in try/finally:

```python
try:
    smu.write("smu.source.output = smu.ON")
    # ... run tests ...
finally:
    smu.write("smu.source.output = smu.OFF")
```

### 8. Frequency Test at Wrong Termination

**Problem**: Signal amplitude wrong, reflections

**Cause**: Using 1MΩ termination with 50Ω source

**Solution**: Match termination to source impedance (50Ω for AFG/signal generators)

### 9. Insufficient Settling Time

**Problem**: Measurements vary, especially at voltage changes

**Cause**: Not allowing circuit to settle after changing voltage

**Solution**: Add delays after voltage changes:

```python
smu.write(f"smu.source.level = {new_voltage}")
time.sleep(0.2)  # Allow settling before measurement
```

---

## Test Engine Architecture

### Recommended Structure

```python
class TestEngine:
    def __init__(self, instrument_manager):
        self.inst = instrument_manager
        self.test_points: List[TestPoint] = []
        self.is_running = False
        self.should_stop = False
        
        # Callbacks for UI updates
        self.on_log = None           # (message) -> None
        self.on_test_start = None    # (test_point) -> None
        self.on_test_complete = None # (test_point) -> None
        self.on_progress = None      # (percent, message) -> None
        self.on_screenshot = None    # (path) -> None
        self.on_complete = None      # (pass_count, fail_count) -> None
    
    def generate_test_points(self, ...):
        """Create test point list based on configuration"""
        pass
    
    def configure_instruments(self, ...):
        """Set up scope and other instruments for test"""
        pass
    
    def run_single_test(self, test_point, ...):
        """Execute one test point"""
        pass
    
    def run_sequence(self, ...):
        """Run all enabled test points"""
        self.is_running = True
        try:
            for i, tp in enumerate(self.test_points):
                if self.should_stop:
                    break
                if not tp.enabled:
                    continue
                self.run_single_test(tp, ...)
        finally:
            self.is_running = False
            # Clean up (disable outputs, etc.)
    
    def stop(self):
        """Request stop (checked between tests)"""
        self.should_stop = True
```

### Thread Safety for GUI Updates

Run tests in a separate thread, use queue for GUI updates:

```python
import threading
import queue

class TestApp:
    def __init__(self):
        self.msg_queue = queue.Queue()
        
        # Set up callbacks to queue messages
        self.engine.on_log = lambda m: self.msg_queue.put(('log', m))
        self.engine.on_test_complete = lambda t: self.msg_queue.put(('complete', t))
        
        # Process queue periodically
        self.root.after(100, self._process_queue)
    
    def _process_queue(self):
        while not self.msg_queue.empty():
            msg_type, data = self.msg_queue.get_nowait()
            if msg_type == 'log':
                self._add_log(data)
            elif msg_type == 'complete':
                self._update_result(data)
        self.root.after(100, self._process_queue)
    
    def run_tests(self):
        thread = threading.Thread(target=self.engine.run_sequence, args=(...))
        thread.start()
```

---

## Reference Test Implementations

### AFG Frequency Sweep Test

**Purpose**: Verify oscilloscope's internal AFG frequency accuracy

**Equipment**: MSO/MDO oscilloscope with AFG option

**Connection**: AFG OUT → CH1 (50Ω BNC cable)

**Key Steps**:
1. Configure AFG for square wave at test frequency
2. Set up frequency measurement on scope
3. Set timebase to show 2-2.5 cycles
4. Trigger and acquire
5. Read frequency measurement
6. Compare to expected, calculate error %

**Typical Tolerance**: ±0.2% for most frequencies

### LED Current Test

**Purpose**: Compare SMU current measurement with oscilloscope measurement via shunt resistor

**Equipment**: 
- MSO/MDO oscilloscope
- Keithley 2450 SMU
- LED circuit with series resistor and shunt resistor

**Circuit**:
```
SMU HI → 470Ω → LED anode
LED cathode → 10Ω shunt → SMU LO
                 ↑
           Scope CH3 probe
```

**Key Steps**:
1. Configure SMU for voltage source, current measure (TSP commands)
2. Configure scope channel with external attenuation (1/R_shunt) and alternate units
3. Set SMU voltage
4. Take SMU current reading
5. Take scope current reading
6. Compare measurements, calculate error %

**Typical Tolerance**: ±2.5%

**Critical Setup**:
```python
# Scope external attenuation for 10Ω shunt
scope.write(f"CH{ch}:PROBEFunc:EXTAtten 0.1")  # 1/10 = 0.1
scope.write(f"CH{ch}:PROBEFunc:EXTUnits:STATE ON")
# Now scope returns current in Amps directly!
```

---

## Quick Reference Card

### Essential Commands After Scope Connect
```python
scope.write("*CLS")
scope.write("HEADer OFF")
scope.write("VERBose OFF")
```

### Essential Commands After FACtory Reset
```python
scope.write("FACtory")
scope.query("*OPC?")  # Wait
scope.write("HEADer OFF")  # Re-apply!
scope.write("VERBose OFF")
```

### SMU Voltage Source (TSP)
```python
smu.write("reset()")
smu.write("smu.source.func = smu.FUNC_DC_VOLTAGE")
smu.write(f"smu.source.level = {voltage}")
smu.write(f"smu.source.ilimit.level = {current_limit}")
smu.write("smu.measure.func = smu.FUNC_DC_CURRENT")
smu.write("smu.measure.autorange = smu.ON")
smu.write("smu.source.output = smu.ON")
```

### Current Measurement via Shunt
```python
scope.write(f"CH{ch}:PROBEFunc:EXTAtten {1.0/R_shunt}")
scope.write(f"CH{ch}:PROBEFunc:EXTUnits:STATE ON")
# Scope now returns Amps - don't divide by R_shunt again!
```

### Pass/Fail Check
```python
error_pct = ((measured - expected) / expected) * 100
passed = abs(error_pct) <= tolerance_pct
```

---

*Document Version: 1.0*
*Last Updated: January 2026*
*Based on: Tek PTA v5.1 development experience*

---

## Appendix: SpectrumView Programming

### Overview

SpectrumView is Tektronix's integrated spectrum analyzer feature on MSO5/6 series oscilloscopes. It provides real-time frequency domain analysis with independent controls from the time-domain view.

### Enabling SpectrumView

```python
ch = 2  # Channel number

# Enable channel display
scope.write(f"DISplay:WAVEView1:CH{ch}:STATE ON")

# Enable SpectrumView for this channel
scope.write(f"CH{ch}:SV:STATE ON")

# Display the Normal spectrum trace
scope.write(f"SV:CH{ch}:SELect:RF_NORMal ON")
```

### Setting Frequency Range

```python
# Set center frequency (Hz)
scope.write(f"CH{ch}:SV:CENTERFrequency 100E6")  # 100 MHz

# Set span (Hz) - applies to all SV channels
scope.write("SV:SPAN 50E6")  # 50 MHz span

# Query actual values
center = float(scope.query(f"CH{ch}:SV:CENTERFrequency?"))
span = float(scope.query("SV:SPAN?"))
start = float(scope.query(f"CH{ch}:SV:STARTFrequency?"))
stop = float(scope.query(f"CH{ch}:SV:STOPFrequency?"))
```

### Resolution Bandwidth (RBW)

```python
# Auto RBW (recommended) - tracks span in 1000:1 ratio
scope.write("SV:RBWMode AUTO")

# Manual RBW
scope.write("SV:RBWMode MANual")
scope.write("SV:RBW 10E3")  # 10 kHz RBW

# Set span:RBW ratio for auto mode
scope.write("SV:SPANRBWRatio 1000")  # Default is 1000:1
```

### Peak Markers

Peak markers automatically find and mark the strongest signals in the spectrum.

```python
# Enable peak markers
scope.write("SV:MARKER:PEAK:STATE ON")

# Configure peak detection
scope.write("SV:MARKER:PEAK:MAXimum 11")        # Max 11 markers
scope.write("SV:MARKER:PEAK:THReshold -80")     # Minimum -80 dBm to mark
scope.write("SV:MARKER:PEAK:EXCURsion 6")       # 6 dB min between peaks

# Set marker type (ABSolute or DELTa)
scope.write("SV:MARKER:TYPe ABSolute")

# Query peak frequencies and amplitudes
frequencies = scope.query("SV:MARKER:PEAKS:FREQuency?")  # Comma-separated Hz
amplitudes = scope.query("SV:MARKER:PEAKS:AMPLITUDE?")   # Comma-separated dBm

# Parse results
freq_list = [float(f) for f in frequencies.split(',') if f.strip()]
amp_list = [float(a) for a in amplitudes.split(',') if a.strip()]
```

### Reference Marker

```python
# Query reference marker
ref_freq = float(scope.query("SV:MARKER:REFERence:FREQuency?"))
ref_amp = float(scope.query("SV:MARKER:REFERence:AMPLITUDE?"))

# Move center frequency to reference marker
scope.write("SV:MARKER:REFERence")
```

### Amplitude Units

```python
# Set vertical units to dBm
scope.write(f"SV:CH{ch}:UNIts DBM")

# Other options: DBV, DBMV, DBUV, DBUA, DBUW
```

### Trace Types

```python
# Normal trace (default, real-time)
scope.write(f"SV:CH{ch}:SELect:RF_NORMal ON")

# Max Hold trace
scope.write(f"SV:CH{ch}:SELect:RF_MAXHold ON")

# Min Hold trace
scope.write(f"SV:CH{ch}:SELect:RF_MINHold ON")

# Average trace
scope.write(f"SV:CH{ch}:SELect:RF_AVErage ON")
scope.write(f"SV:CH{ch}:RF_AVErage:NUMAVg 16")  # 16 averages
```

### Spectrum Scanning Strategy

To scan a wide frequency range (e.g., 0-5 GHz), use overlapping spans:

```python
def scan_spectrum(scope, ch, start_freq, stop_freq, span_per_step=500e6):
    """Scan spectrum in steps with overlapping spans"""
    all_peaks = []
    overlap = span_per_step * 0.1  # 10% overlap
    
    # Calculate center frequencies
    current_center = start_freq + span_per_step / 2
    
    while current_center - span_per_step / 2 < stop_freq:
        # Set frequency range
        scope.write(f"CH{ch}:SV:CENTERFrequency {current_center}")
        scope.write(f"SV:SPAN {span_per_step}")
        
        # Wait for acquisition to settle
        time.sleep(1.0)
        
        # Trigger single acquisition
        scope.write("ACQuire:STOPAfter SEQuence")
        scope.write("ACQuire:STATE RUN")
        time.sleep(0.5)
        
        # Wait for acquisition complete
        while scope.query("ACQuire:STATE?").strip() != "0":
            time.sleep(0.1)
        
        # Get peaks
        freqs = scope.query("SV:MARKER:PEAKS:FREQuency?")
        amps = scope.query("SV:MARKER:PEAKS:AMPLITUDE?")
        
        # Process and deduplicate peaks
        # ... (check for duplicates from overlap regions)
        
        # Move to next span
        current_center += span_per_step - overlap
    
    return all_peaks
```

### Common RF Bands Reference

| Band | Frequency Range | Notes |
|------|-----------------|-------|
| FM Radio | 88-108 MHz | Strong signals with antenna |
| TV UHF | 470-608 MHz | Digital TV |
| 600 MHz LTE | 614-698 MHz | T-Mobile 5G |
| 700 MHz LTE | 698-806 MHz | Verizon, AT&T |
| Cellular 850 | 824-894 MHz | Legacy cellular |
| PCS 1900 | 1850-1990 MHz | Major carriers |
| AWS | 1710-2155 MHz | LTE bands |
| WiFi 2.4 GHz | 2400-2500 MHz | 802.11b/g/n |
| BRS/EBS | 2500-2700 MHz | Sprint/T-Mobile |
| CBRS | 3550-3700 MHz | Citizens Band Radio |
| WiFi 5 GHz | 5150-5850 MHz | 802.11a/n/ac |

### SpectrumView Gotchas

1. **Enable STATE ON**: Just setting center frequency won't display spectrum - must enable `CH{x}:SV:STATE ON`

2. **Span Affects All Channels**: `SV:SPAN` is global - changing it affects all SV-enabled channels

3. **Peak Markers Need Threshold**: Set `SV:MARKER:PEAK:THReshold` appropriately for your signal levels

4. **Acquisition Required**: Peak data updates after acquisitions - ensure acquisition completes before querying

5. **Use SpectrumView Averaging, NOT Acquisition Averaging**: For better signal-to-noise in spectrum analysis, use the SV averaging trace, not the time-domain acquisition average:

```python
# WRONG - This averages in time domain
scope.write("ACQuire:MODe AVErage")
scope.write("ACQuire:NUMAVg 256")

# RIGHT - This averages in SpectrumView
scope.write("ACQuire:MODe SAMple")  # Time domain stays Sample
scope.write(f"SV:CH{ch}:RF_AVErage:NUMAVg 256")  # SV averaging
scope.write(f"SV:CH{ch}:SELect:RF_AVErage ON")   # Show average trace
```

6. **Span:RBW Ratio for Resolution**: Default is 1000:1. For better frequency resolution, increase to 10000:1:

```python
scope.write("SV:RBWMode AUTO")
scope.write("SV:SPANRBWRatio 10000")  # Better resolution
```

7. **Stop Acquisition Before Screenshot**: Always stop the acquisition before taking a screenshot to get a clean, stable image:

```python
scope.write("ACQuire:STATE STOP")
time.sleep(0.2)  # Brief settle
# Now take screenshot
```

8. **Use 50Ω Termination for Antennas/Coax**: When connecting antennas or 50Ω coaxial cables, use 50Ω termination:

```python
scope.write(f"CH{ch}:TERmination 50")  # 50 ohm for antenna/coax
scope.write(f"CH{ch}:BANdwidth FULL")   # Full bandwidth for RF
```

9. **MSO4/5/6 Has 1 GHz Capture Bandwidth**: You can use larger spans (up to 1 GHz) for faster scanning:

```python
SPAN_PER_STEP = 500e6  # 500 MHz span per step (fast scanning)
```

10. **Check for Clipping**: Always check for time-domain clipping which affects spectrum accuracy:

```python
# Check for clipping on channel
clipping = scope.query(f"CH{ch}:CLIPping?")
if clipping.strip() == "1":
    # Increase vertical scale
    current_scale = float(scope.query(f"CH{ch}:SCAle?"))
    scope.write(f"CH{ch}:SCAle {current_scale * 2}")
```

---

## Appendix: Clipping Detection

### Always Check for Clipping

Clipping occurs when the signal exceeds the vertical range, causing measurement errors. **Always check for clipping before trusting measurements.**

```python
def auto_scale_no_clipping(scope, ch: int, max_attempts: int = 5):
    """Automatically adjust vertical scale until no clipping"""
    scales = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0]  # V/div progression
    
    for attempt in range(max_attempts):
        # Run a quick acquisition
        scope.write("ACQuire:STOPAfter SEQuence")
        scope.write("ACQuire:STATE RUN")
        time.sleep(0.3)
        
        # Check for clipping
        clipping = scope.query(f"CH{ch}:CLIPping?")
        if clipping.strip() == "1":
            # Clipping detected - increase scale
            current_scale = float(scope.query(f"CH{ch}:SCAle?"))
            for s in scales:
                if s > current_scale:
                    scope.write(f"CH{ch}:SCAle {s}")
                    break
        else:
            break  # No clipping, we're done
    
    scope.write("ACQuire:STATE STOP")
```

### When to Check for Clipping

- **Before any measurement** - Clipping invalidates MEAN, MAX, MIN, PK2PK measurements
- **After changing signal conditions** - When DUT output changes
- **After connecting probes** - Signal amplitude may differ from expected
- **In spectrum analysis** - Time domain clipping affects FFT accuracy

---

## Appendix: LED Current Test Gotchas

### Absolute vs Percentage Tolerance

For very low current measurements (sub-mA range), percentage tolerance can be problematic because small absolute variations become large percentages. Use absolute tolerance instead:

```python
# Bad: 1% of 0.5 mA = 5 µA (very tight!)
# Good: ±300 µA absolute tolerance

TOLERANCE_UA = 300  # Absolute tolerance in microamps

error_mA = scope_current - smu_current
error_uA = error_mA * 1000

if abs(error_uA) <= TOLERANCE_UA:
    status = "PASS"
```

### Horizontal Scale and Roll Mode

**Critical**: Keep horizontal scale below 40 ms/div. At 40 ms/div and above, the scope enters Roll Mode where triggers behave differently:

```python
# Good - stays in normal triggered mode
scope.write("HORizontal:SCAle 20e-3")  # 20 ms/div

# Bad - enters roll mode, triggers won't work as expected
scope.write("HORizontal:SCAle 100e-3")  # 100 ms/div = roll mode
```

### Correct LED Current Test Sequence

The proper measurement sequence is critical:

```python
def run_led_current_test(tp: TestPoint, ch: int):
    # Step 1: Turn on SMU voltage
    smu.write(f":SOURce:VOLTage {tp.nominal_value}")
    smu.write(":OUTPut ON")
    time.sleep(0.1)  # Let current stabilize
    
    # Step 2: Read SMU current (this is our expected value)
    smu_current_A = float(smu.query(":MEASure:CURRent?"))
    smu_current_mA = smu_current_A * 1000
    
    # Step 3: Configure scope trigger to measurement channel
    scope.write(f"TRIGger:A:EDGE:SOUrce CH{ch}")
    scope.write("TRIGger:A:TYPE EDGE")
    scope.write("TRIGger:A:MODe AUTO")  # AUTO for DC signals
    
    # Step 4: Set trigger level to 50% of expected current
    trigger_level_A = (smu_current_mA / 1000) * 0.5
    scope.write(f"TRIGger:A:LEVel:CH{ch} {trigger_level_A}")
    
    # Step 5: Single sequence capture
    scope.write("ACQuire:STOPAfter SEQuence")
    scope.write("ACQuire:STATE RUN")
    scope.wait_acquisition(timeout=5)
    
    # Step 6: Stop acquisition before taking measurement/screenshot
    scope.write("ACQuire:STATE STOP")
    time.sleep(0.2)
    
    # Step 7: Get measurement
    result = scope.query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
    scope_current_mA = float(result) * 1000
```

### Vertical Setup with Clipping Detection

Before taking measurements, verify the vertical scale is appropriate using the `CH<x>:CLIPping?` query:

```python
def setup_vertical_for_current(self, ch: int, expected_current_mA: float):
    """
    Set vertical scale with clipping detection.
    """
    current_A = expected_current_mA / 1000
    scales = [0.0005, 0.001, 0.002, 0.005]  # 500µA, 1mA, 2mA, 5mA per div
    
    for scale in scales:
        scope.write(f"CH{ch}:SCAle {scale}")
        scope.write(f"CH{ch}:OFFSet {current_A}")
        
        # Quick acquisition to check for clipping
        scope.write("ACQuire:STOPAfter SEQuence")
        scope.write("ACQuire:STATE RUN")
        time.sleep(0.3)
        scope.write("ACQuire:STATE STOP")
        
        # Check for clipping
        clipping = scope.query(f"CH{ch}:CLIPping?")
        if clipping and clipping.strip() == "1":
            print(f"Clipping at {scale*1e6:.0f} µA/div, increasing...")
            continue
        else:
            print(f"Scale OK: {scale*1e6:.0f} µA/div")
            break
```

### Use RUN Mode Instead of Single Sequence for DC Signals

For DC signals, single sequence mode may not trigger reliably. Use continuous run with a short wait:

```python
def measure_scope_current(ch: int, expected_current_mA: float) -> float:
    # Set trigger level to expected current
    trigger_level_A = expected_current_mA / 1000
    scope.write(f"TRIGger:A:LEVel:CH{ch} {trigger_level_A}")
    
    # RUN mode (not single seq) - acquire for 5 acquisitions
    scope.write("ACQuire:STOPAfter RUNSTop")
    scope.write("ACQuire:STATE RUN")
    time.sleep(1.0)  # Wait for ~5 acquisitions
    
    # STOP before reading measurement
    scope.write("ACQuire:STATE STOP")
    time.sleep(0.2)
    
    # Check for clipping
    clipping = scope.query(f"CH{ch}:CLIPping?")
    if clipping and clipping.strip() == "1":
        print("WARNING: Signal is clipping!")
    
    # Read measurement
    result = scope.query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
    return float(result) * 1000  # Convert to mA
```
        scope.write(f"TRIGger:A:LEVel:CH{ch} {current_A}")
        
        # Try to trigger with timeout
        scope.write("ACQuire:STOPAfter SEQuence")
        scope.write("ACQuire:STATE RUN")
        
        # Wait 3 seconds for trigger
        triggered = wait_for_trigger(timeout=3.0)
        if not triggered:
            scope.write("TRIGger FORCe")  # Force trigger if none
        
        # Check for clipping - if pk2pk exceeds 7 divisions, scale up
        if not check_clipping(ch, scale):
            return  # Good setup
        
        # Increase scale for next attempt
        scale *= 2
```

**Key Points:**
- Use SMU current reading as the expected value
- Set offset to POSITIVE value equal to expected current
- Set trigger level to same value
- Force trigger after 3 seconds if no trigger
- Check for clipping and increase scale if needed

### Turn Off Unused Channels

Factory default turns on CH1. If you're not using it, turn it off to avoid confusion:

```python
# Turn off all channels except the one we're using
for c in range(1, 5):
    if c != measurement_channel:
        scope.write(f"DISplay:WAVEView1:CH{c}:STATE OFF")

scope.write(f"DISplay:WAVEView1:CH{measurement_channel}:STATE ON")
```

---

## Future Features / Roadmap

The following features are commonly requested and could be added to Tek PTA:

### 1. Custom Output Location
- Allow user to specify where test results are saved
- Add file dialog to choose output directory
- Store preference in config file

### 2. Custom Report Naming
- Allow user to name the test results folder
- Allow user to customize PDF report filename
- Include DUT serial number in filename automatically

### 3. Custom Instrument Support
- Allow users to provide SCPI command sets for other instruments
- Generic instrument driver with user-defined commands
- Import/export instrument profiles (JSON format)
- Pattern: See `InstrumentManager.add_manual()` for connection example

### 4. Jitter and Eye Diagram Tests
- Use TIE (Time Interval Error) measurements
- DPOJET analysis for jitter components (RJ, DJ, TJ@BER)
- Eye height, eye width measurements
- Requires: pattern generator or real serial data source
- Key commands: `MEASUrement:MEAS<x>:TYPe TIE`, `EYEHEIGHT`, `EYEWIDTH`

### 5. Multi-Stage Tests with Setup Prompts
- Tests requiring configuration changes between sub-tests
- Multiple setup dialogs with user-provided connection diagrams
- Support for user-uploaded schematic images (PNG/JPG)
- State machine for test sequencing with pauses

### 6. User-Provided Setup Diagrams
- Allow users to upload their own connection diagrams
- Store diagrams with test suite definitions
- Support PNG, JPG, SVG formats

---

## Files Reference

### To RUN Tek PTA
Just one file: `tek_pta.py`

```bash
pip install pyvisa pyvisa-py Pillow reportlab matplotlib
python tek_pta.py
```

### To EDIT/DEVELOP Tek PTA
1. `tek_pta.py` - Main application (3650+ lines)
2. `TEK_PTA_AUTOMATION_GUIDE.md` - This document (lessons learned)
3. SCPI Command Database (via MCP tools):
   - `tek_search_commands` - Find commands by keyword
   - `tek_get_command` - Get detailed syntax
   - `tek_comprehensive_search` - Search procedures

### Code Structure in tek_pta.py

| Lines | Section |
|-------|---------|
| 1-70 | Imports, version info |
| 70-110 | TekColors, TekFonts constants |
| 115-260 | Setup diagram generators (matplotlib) |
| 260-320 | Data classes (TestStatus, InstrumentInfo, TestSuite, TestPoint, PeakSignal) |
| 320-620 | InstrumentManager (VISA discovery, connection, probe query) |
| 620-920 | AFGFrequencyEngine |
| 920-1340 | LEDCurrentEngine |
| 1340-1620 | SpectrumScannerEngine |
| 1620-1750 | RoundedButton widget |
| 1750-3600 | TekPTAApp (main GUI application) |

### Output Files Generated

Each test session creates a folder: `test_results/session_YYYYMMDD_HHMMSS/`

| File | Description |
|------|-------------|
| `test_report.txt` | Plain text summary of results |
| `test_report.pdf` | Professional PDF with logo, probes, plots, screenshots |
| `scpi_log.txt` | Complete SCPI command log (all commands sent/received) |
| `iv_characteristic.png` | I-V plot for LED current tests |
| `frequency_response.png` | Frequency response plot for AFG tests |
| `screenshots/` | Oscilloscope screenshots from each test point |

### Adding a New Test Type

1. Create a new engine class (like `LEDCurrentEngine`)
2. Add a `TestSuite` entry in `_create_suites()`
3. Add config panel in `_create_config_panel()`
4. Add handling in `_show_config_for_test_type()`
5. Add results columns in `_configure_results_tree_for_test_type()`
6. Add setup diagram generator function
7. Add setup instructions in `_show_setup_instructions()`
8. Add thread launch in `_run_tests()`
9. Add plot generation function (like `_save_iv_plot()`)
10. **Update this automation guide with lessons learned!**
