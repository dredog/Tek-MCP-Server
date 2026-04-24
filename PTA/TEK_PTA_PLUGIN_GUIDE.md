# Tek PTA Plugin Development Guide

**Version:** 5.2  
**Keywords:** plugin, test suite, SCPI, measurement, oscilloscope, AWG, SMU, statistics, two-view, rise time, fall time, delay, screenshot, differential, single-ended, PRBS, serial, pattern length, setup diagram, eye diagram, jitter, HEIGHT, WIDTH, DJ, reference waveform, population limiting, plugin structure, silent failure, dataclass, instrument_manager, scope_write, scope_query, SCPI logging

This is the consolidated guide for creating test suite plugins for Tek PTA. It combines lessons learned, measurement philosophy, and architectural patterns.

---

## Table of Contents

1. [New Test Checklist](#1-new-test-checklist)
2. [Quick Start Template](#2-quick-start-template)
3. [CRITICAL: Plugin Structure Requirements](#3-critical-plugin-structure-requirements)
4. [SCPI Communication Best Practices](#4-scpi-communication-best-practices)
5. [Measurement Philosophy](#5-measurement-philosophy) (incl. Acquisition Strategy, SCALERATio, MSO2 Probes)
6. [Two-View Architecture](#6-two-view-architecture)
7. [Horizontal Scale Rules](#7-horizontal-scale-rules)
8. [Vertical Setup (Differential to Single-Ended)](#8-vertical-setup-differential-to-single-ended)
9. [Screenshot Capture Pattern](#9-screenshot-capture-pattern)
10. [Pass/Fail and Status Handling](#10-passfail-and-status-handling)
11. [Common Patterns](#11-common-patterns)
12. [Debugging Tips](#12-debugging-tips)
13. [AWG70000 HSS Plug-in for PRBS](#13-awg70000-hss-plug-in-for-prbs)
14. [Serial Pattern Measurements](#14-serial-pattern-measurements)
15. [Setup Diagram Creation](#15-setup-diagram-creation)
16. [Results Table Format](#16-results-table-format)
17. [Eye Diagram Measurements](#17-eye-diagram-measurements)
18. [Reference Waveform Handling](#18-reference-waveform-handling)

---

## 1. New Test Checklist

Use this checklist when creating a new test suite plugin:

### Before Writing Code

- [ ] **Define measurements**: What values are you measuring? (delay, rise time, frequency, amplitude, pattern length, data rate, etc.)
- [ ] **Determine nominals and tolerances**: What's the expected value and acceptable range?
- [ ] **Identify instruments needed**: Oscilloscope only? AWG? SMU? External DUT?
- [ ] **Document DUT connections**: How does the DUT connect to the scope/instruments?
- [ ] **Plan scope configuration**: Channels, coupling, termination, bandwidth
- [ ] **Choose measurement approach**: Single acquisition, statistics-based, or DC steady-state (run/wait/stop)?
- [ ] **Create setup diagram**: Generate matplotlib image for setup confirmation dialog

### Physical Setup Documentation

- [ ] **Connection diagram**: Create a matplotlib block diagram showing:
  - DUT outputs and which scope channels they connect to
  - Cable types (50Ω coax, probes, etc.)
  - Termination requirements
  - Ground connections
- [ ] **Setup instructions**: Text summary of connections for the setup dialog
- [ ] **DUT control**: Document if/how the DUT is controlled (Tek instrument, external, manual)

### Setup Diagram Images

Store setup diagrams in:
```
C:\Users\<username>\TektronixMCP\PTA\test_suites\images\
```

These pre-made professional diagrams are included in build packages and loaded by the setup confirmation dialog.

### Plugin Structure

- [ ] Create file in `test_suites/` folder (e.g., `my_test_suite.py`)
- [ ] **CRITICAL**: Copy Plugin API definitions EXACTLY from a working plugin (see Section 3)
- [ ] Define `MeasurementSpec` dataclass or similar for your test points
- [ ] Implement `register_suites()` function returning list of `TestSuitePlugin`
- [ ] Set unique `test_type` string (e.g., `"my_custom_test"`)

### Engine Implementation

- [ ] `generate_test_points()`: Create TestPoint list with nominals, tolerances, limits
- [ ] `setup_instruments()`: Configure scope channels, trigger, timebase
- [ ] `run()`: Main test loop with acquisition and measurement reading
- [ ] `run_single_test()`: Read single measurement, set status to PASS/FAIL/ERROR
- [ ] `cleanup()`: Disable outputs, close connections
- [ ] **Use SCPI wrapper methods**: `self.inst.scope_write()` and `self.inst.scope_query()` for logging (see Section 4)

### Measurement Setup

- [ ] For repetitive signals, use **measurement statistics** (not waveform averaging) - see Section 4
- [ ] For serial patterns, use **single acquisition** with pattern length measurement - see Section 13
- [ ] For edge measurements, use **two-view pattern** - see Section 5
- [ ] For **DC steady-state** (shunt current, power supply), use **run/wait/stop** (NOT single-seq) - see Section 5
- [ ] For **current shunt measurement**, use `CH<x>:SCALERATio` (NOT `PROBEFunc:EXTAtten`) - see Section 5
- [ ] Apply **H-scale rules**: 2× nominal for edge, wide for delay - see Section 6
- [ ] Handle **differential to single-ended** conversion if needed - see Section 7
- [ ] **MSO2 probe setup**: MSO2 doesn't auto-detect probes — set `PROBEFunc:EXTAtten` manually for BNC/passive

### Screenshot Handling

- [ ] Capture after each measurement or view change
- [ ] **Assign to test point**: `tp.screenshot_path = screenshot_path`
- [ ] **Share screenshot**: If multiple tests use same view, assign same path to all
- [ ] Use fallback paths: `C:/Temp/` then `C:/`
- [ ] Delete temp files from scope after transfer

### Invalid Measurement Handling

When measurements return 9.91E+37 (Tek's "invalid" value), the usual causes are:
- **Scope not triggering**: Wrong trigger level, source, or edge
- **Signal not visible**: V scale or offset wrong, signal clipped
- **Wrong timebase**: H scale too fast or slow to see the edge/feature
- **No signal**: DUT not outputting, cable disconnected

**Recovery strategy for plugins:**
```python
if measured > 1e30:  # Invalid measurement
    self.log("WARNING: Invalid measurement - checking setup...")
    tp.status = TestStatus.ERROR
    tp.extra_data['error'] = "Invalid measurement - check setup"
```

### Status and Results

- [ ] Set `tp.status` to appropriate `TestStatus` value
- [ ] Use `.value` comparisons for cross-module compatibility
- [ ] Calculate `tp.error_pct` for percentage error
- [ ] Store extra data in `tp.extra_data` dict (stdev, population, etc.)
- [ ] Print results table with: #, Test Name, Nominal, Lower Limit, Upper Limit, Measured, Status

### Testing

- [ ] Verify SCPI commands in programmer manual
- [ ] Test screenshot capture separately
- [ ] Check measurement values for 9.91E+37 (invalid)
- [ ] Verify pass/fail counts match between UI and PDF
- [ ] Test with disconnected DUT to verify error handling

---

## 2. Quick Start Template

```python
#!/usr/bin/env python3
"""
My Custom Test Suite for Tek PTA
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
    test_type: str  # Unique identifier - MUST be unique
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Optional[type] = None  # MUST be last!


class TestEngineBase:
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
        raise NotImplementedError
    
    def setup_instruments(self, config: Dict[str, Any]) -> bool:
        raise NotImplementedError
    
    def run_single_test(self, test_point: TestPoint, config: Dict[str, Any]) -> TestPoint:
        raise NotImplementedError
    
    def run(self, config: Dict[str, Any]):
        raise NotImplementedError
    
    def cleanup(self):
        pass
    
    def stop(self):
        self.running = False


# =============================================================================
# YOUR CUSTOM ENGINE
# =============================================================================

class MyCustomEngine(TestEngineBase):
    def __init__(self, instrument_manager):
        super().__init__(instrument_manager)
    
    def generate_test_points(self, config: Dict[str, Any]) -> List[TestPoint]:
        self.test_points = []
        # Create your test points here
        self.test_points.append(TestPoint(
            test_id=1,
            name="My Measurement",
            nominal_value=100.0,
            unit="mV",
            lower_limit=90.0,
            upper_limit=110.0,
        ))
        return self.test_points
    
    def setup_instruments(self, config: Dict[str, Any]) -> bool:
        # Configure scope here
        return True
    
    def run_single_test(self, test_point: TestPoint, config: Dict[str, Any]) -> TestPoint:
        # Implement measurement
        return test_point
    
    def run(self, config: Dict[str, Any]):
        self.running = True
        # Main test loop
        self.running = False


# =============================================================================
# PLUGIN REGISTRATION
# =============================================================================

def register_suites():
    return [
        TestSuitePlugin(
            name="My Custom Test",
            description="Description here",
            test_type="my_custom_test",
            config={},
            required_instruments=["Oscilloscope"],
            engine_class=MyCustomEngine,
        ),
    ]
```

---

## 3. CRITICAL: Plugin Structure Requirements

### The Problem: Silent Loading Failures

When a test suite plugin doesn't load in Tek PTA (clicking "Select" does nothing, no error shown), the cause is almost always **incorrect Plugin API dataclass structure**.

Tek PTA uses Python's dataclass system which is **very sensitive to field order and types**. If your local definitions don't match exactly, the plugin **silently fails to load**.

### GOLDEN RULE

**Always copy the Plugin API definitions from a known working plugin** (e.g., `awg70002b_pulse_timing_suite.py`). Never write them from scratch or "improve" them.

### Required Dataclass Structures

**COPY THESE EXACTLY** - field order, types, and defaults all matter:

```python
class TestStatus(Enum):
    """Status of a test point"""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"      # Don't forget ERROR!
    SKIPPED = "Skipped"


@dataclass
class TestPoint:
    """Represents a single test measurement point"""
    test_id: int
    name: str
    nominal_value: float
    unit: str
    tolerance_pct: float = 0.0
    has_limits: bool = True
    enabled: bool = True
    status: TestStatus = TestStatus.NOT_RUN
    measured_value: float = 0.0       # NOT Optional[float] = None!
    error_pct: float = 0.0
    lower_limit: float = 0.0
    upper_limit: float = 0.0
    screenshot_path: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class TestSuitePlugin:
    """Definition of a test suite plugin"""
    name: str
    description: str
    test_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Optional[type] = None   # MUST be last, MUST be Optional


class TestEngineBase:
    """Base class for custom test engines"""
    
    def __init__(self, instrument_manager):   # MUST take instrument_manager!
        self.inst = instrument_manager
        self.test_points: List[TestPoint] = []
        self.running = False
        self.output_dir = None
        self.reference_config = None
        
        # Callbacks - use these names exactly
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[float, str], None]] = None
        self.on_test_start: Optional[Callable[[TestPoint], None]] = None
        self.on_test_complete: Optional[Callable[[TestPoint], None]] = None
        self.on_screenshot: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[int, int], None]] = None
```

### Common Mistakes That Cause Silent Failures

| Mistake | Correct | Wrong |
|---------|---------|-------|
| TestSuitePlugin.engine_class position | **Last field** | Any other position |
| TestSuitePlugin config field name | `config` | `default_config` |
| TestEngineBase.__init__ signature | `__init__(self, instrument_manager)` | `__init__(self)` |
| TestPoint.measured_value type | `float = 0.0` | `Optional[float] = None` |
| TestStatus enum values | `PASS`, `FAIL`, `NOT_RUN` | `PASSED`, `FAILED`, `PENDING` |
| Missing TestStatus value | Include `ERROR` | Omit `ERROR` |
| Callback names | `on_log`, `on_progress` | `log_callback`, `progress_callback` |

### How to Debug Plugin Loading Issues

1. **Test import in Python console:**
   ```python
   import sys
   sys.path.append(r"C:\path\to\test_suites")
   from my_test_suite import register_suites
   suites = register_suites()
   print(suites[0].engine_class)
   engine = suites[0].engine_class(None)  # Pass None for testing
   ```

2. **Check for import errors:**
   ```python
   try:
       from my_test_suite import register_suites
   except Exception as e:
       print(f"Import error: {e}")
   ```

3. **Compare with working plugin:**
   - Diff your dataclass definitions against `awg70002b_pulse_timing_suite.py`
   - Check field order, names, types, and defaults

---

## 4. SCPI Communication Best Practices

### Use InstrumentManager Wrapper Methods

**Always use the `InstrumentManager` wrapper methods** for SCPI communication instead of accessing the raw PyVISA instrument directly:

| Use This (Logged) | Not This (Bypasses Logging) |
|-------------------|----------------------------|
| `self.inst.scope_write(cmd)` | `self.inst.scope.write(cmd)` |
| `self.inst.scope_query(cmd)` | `self.inst.scope.query(cmd)` |
| `self.inst.scope_opc(timeout)` | `self.inst.scope.query("*OPC?")` |

### Why Use Wrappers?

The wrapper methods provide:

1. **SCPI Logging**: All commands and responses appear in the SCPI Log panel with color-coding:
   - Light blue: Commands sent
   - Light green: Queries sent  
   - Plum: Responses received

2. **Consistent Error Handling**: Standardized timeout and error management across all plugins

3. **Debugging**: When tests fail, you can see exactly what SCPI traffic occurred

4. **PDF Reports**: SCPI transcript can be included in test reports

### Available Wrapper Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `scope_write` | `scope_write(cmd: str) -> None` | Send SCPI command |
| `scope_query` | `scope_query(cmd: str, timeout: int = None) -> str` | Query and return stripped response |
| `scope_opc` | `scope_opc(timeout: int = 30) -> None` | Wait for *OPC? with timeout (seconds) |

### Example: Correct vs Incorrect Usage

```python
# ✓ CORRECT - Uses wrappers, appears in SCPI log
def setup_instruments(self, config):
    self.inst.scope_write("MEASUrement:DELETEALL")
    self.inst.scope_write("HORizontal:SCAle 2.5E-6")
    self.inst.scope_write(f"CH1:SCAle 25E-3")
    response = self.inst.scope_query("CH1:SCAle?")
    self.log(f"CH1 scale set to: {response}")

# ✗ INCORRECT - Bypasses logging, harder to debug
def setup_instruments(self, config):
    self.inst.scope.write("MEASUrement:DELETEALL")
    self.inst.scope.write("HORizontal:SCAle 2.5E-6")
    self.inst.scope.write(f"CH1:SCAle 25E-3")
    response = self.inst.scope.query("CH1:SCAle?")
```

### When to Use Raw PyVISA

There are a few edge cases where direct PyVISA access is appropriate:

| Use Case | Method | Reason |
|----------|--------|--------|
| Binary waveform transfer | `self.inst.scope.read_raw()` | Binary data, not text |
| Binary data write | `self.inst.scope.write_binary_values()` | Binary data, not SCPI |
| Custom timeout per-call | `self.inst.scope.query(cmd, timeout=X)` | If wrapper doesn't support |

For these cases, access the underlying instrument via `self.inst.scope` (oscilloscope), `self.inst.awg` (AWG), or `self.inst.smu` (SMU).

### AWG and SMU Wrappers

Similar wrapper methods exist for other instruments:

```python
# AWG
self.inst.awg_write(cmd)
self.inst.awg_query(cmd)

# SMU  
self.inst.smu_write(cmd)
self.inst.smu_query(cmd)
```

---

## 5. Measurement Philosophy

### Statistics vs Waveform Averaging

For repetitive signals, **use measurement statistics**, not waveform averaging:

**Measurement Statistics** (RECOMMENDED):
- Each acquisition produces one measurement
- Mean and standard deviation calculated from N measurements
- Shows actual measurement repeatability
- Works correctly with triggering

**Waveform Averaging** (NOT RECOMMENDED for measurements):
- Averages waveform samples together
- Reduces noise in waveform display
- BUT: Measurements are still taken on single waveforms
- Can cause measurement confusion

### Statistics Implementation

```python
# Configure for statistics collection
self.inst.scope_write("ACQuire:STOPAfter SEQuence")

# Wait for target sample count
while population < target_count and time.time() - start < timeout:
    pop_str = self.inst.scope_query(
        f"MEASUrement:MEAS{n}:RESUlts:ALLAcqs:POPUlation?"
    ).strip()
    population = int(float(pop_str))
    time.sleep(0.5)

# Read statistics
mean = float(self.inst.scope_query(
    f"MEASUrement:MEAS{n}:RESUlts:ALLAcqs:MEAN?"
))
stdev = float(self.inst.scope_query(
    f"MEASUrement:MEAS{n}:RESUlts:ALLAcqs:STDDev?"
))
```

### Acquisition Strategy: Single-Sequence vs Run/Wait/Stop

Choose the right acquisition approach based on signal type:

**Single Sequence** (`ACQuire:STOPAfter SEQuence`) — for triggered events:
- Pulse edges, rise/fall time, delay measurements
- Serial data eye diagrams, jitter
- Any measurement where you need a specific trigger event
- Signal has clear transitions for the trigger to catch

**Run/Wait/Stop** (`ACQuire:STOPAfter RUNSTOP`) — for DC steady-state:
- DC voltage/current (shunt current with SMU)
- Mean/RMS of stable, continuous signals
- Power supply output validation
- Signal has no edges — trigger won't reliably fire in single-seq mode

```python
# DC Steady-State Pattern (shunt current, PSU output, etc.)
# CLEAR first to flush stale data (critical after changing DUT stimulus)
self.inst.scope_write("CLEAR")
self.inst.scope_write("ACQuire:STOPAfter RUNSTOP")
self.inst.scope_write("ACQuire:STATE RUN")
time.sleep(2.0)  # MSO2 needs ~2s at 20ms/div; MSO4/5/6 can be faster

# Verify at least one acquisition completed
acq_count = self.inst.scope_query("ACQuire:NUMACq?")
if int(acq_count.strip()) < 1:
    time.sleep(1.0)  # Wait longer if needed

# Stop and read
self.inst.scope_write("ACQuire:STATE STOP")
time.sleep(0.1)
result = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
```

> **Why CLEAR?** After changing the DUT input (e.g. SMU voltage), the scope's
> measurement statistics still contain values from the previous stimulus.
> `CLEAR` resets measurement stats so the next reading is purely from new data.
>
> **Why not single-seq for DC?** With a flat DC signal and AUTO trigger, the scope
> may auto-trigger but the single-sequence gate can miss it or hang waiting. 
> Run/wait/stop guarantees data capture for any stable signal.

### Current Shunt Measurement: Use SCALERATio

When measuring current through a shunt resistor, use `CH<x>:SCALERATio` — **not** `PROBEFunc:EXTAtten`.

`SCALERATio` tells the scope to multiply all voltage readings by a ratio, so the display and **all measurement readouts** (MEAN, MAX, etc.) return actual amps with no additional math needed.

```python
# REQUIRED: Enable external units BEFORE setting SCALERATio
self.inst.scope_write(f"CH{ch}:PROBEFunc:EXTUnits:STATE 1")

# For 10Ω shunt: I = V/R, ratio = 1/10 = 0.1
self.inst.scope_write(f"CH{ch}:SCALERATio 0.1")

# For 500mΩ shunt: ratio = 1/0.5 = 2.0
self.inst.scope_write(f"CH{ch}:SCALERATio 2.0")

# Measurement now returns actual amps — no division needed
result = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
current_amps = float(result)  # Already in amps
```

> **IMPORTANT:** `EXTUNITS:STATE 1` must be sent before `SCALERATio` — without it the ratio is ignored by the instrument.

> **When to use what:**
> - `CH<x>:SCALERATio` — Shunt current measurement (V→A conversion)
> - `CH<x>:PROBEFunc:EXTAtten 1` — MSO2 with BNC/SMA cable (no probe detected)
> - `CH<x>:PROBEFunc:EXTAtten 10` — MSO2 with passive 10× probe
> - Neither — MSO4/5/6 with TekVPI/TPA probe (auto-detected)

### MSO2 vs MSO4/5/6 Probe Differences

The MSO2 does **not** auto-detect probe attenuation. You must set it manually:

```python
# MSO2 with BNC cable (1:1)
self.inst.scope_write(f"CH{ch}:PROBEFunc:EXTAtten 1")

# MSO2 with passive 10x probe
self.inst.scope_write(f"CH{ch}:PROBEFunc:EXTAtten 10")
```

MSO4/5/6 auto-detects TekVPI and TPA probes. No `EXTAtten` needed unless using a passive probe without TekVPI interface.

---

## 6. Two-View Architecture

For tests requiring both delay measurements and edge timing (rise/fall time):

### View 1: Delay View (Wide)
- **Purpose**: Measure inter-channel timing
- **H scale**: 2.5 µs/div or similar (shows 2+ cycles)
- **Trigger**: Channel 1 rising edge at signal midpoint

### View 2: Edge View (Zoomed)
- **Purpose**: Measure rise/fall times
- **H scale**: 2× nominal rise time, rounded to 1-2-5 sequence
- **Trigger**: Signal edge being measured

### Implementation Pattern

```python
def run(self, config):
    # Phase 1: Delay measurements
    self._configure_delay_view()
    self._run_delay_measurements()
    
    # Phase 2: Edge measurements  
    self._configure_edge_view()
    self._run_edge_measurements()
```

---

## 7. Horizontal Scale Rules

### For Edge Measurements (Rise/Fall Time)

**Rule**: H_scale ≈ 2× nominal_value, rounded UP to 1-2-5 sequence

| Nominal | 2× Value | Rounded Scale |
|---------|----------|---------------|
| 100 ps | 200 ps | 200 ps/div |
| 165 ps | 330 ps | 500 ps/div |
| 200 ps | 400 ps | 500 ps/div |
| 500 ps | 1 ns | 1 ns/div |
| 1 ns | 2 ns | 2 ns/div |

### 1-2-5 Sequence Helper

```python
def round_to_125_sequence(value):
    """Round value UP to next 1-2-5 sequence value."""
    if value <= 0:
        return 1e-12
    
    exponent = math.floor(math.log10(value))
    mantissa = value / (10 ** exponent)
    
    if mantissa <= 1.0:
        new_mantissa = 1.0
    elif mantissa <= 2.0:
        new_mantissa = 2.0
    elif mantissa <= 5.0:
        new_mantissa = 5.0
    else:
        new_mantissa = 10.0
    
    return new_mantissa * (10 ** exponent)
```

### For Delay Measurements

Use a scale that shows 2-3 complete cycles of the signal:

```python
# For 100 kHz signal (10 µs period)
# Show ~2 cycles = 20 µs
# 20 µs / 10 div = 2 µs/div
h_scale = 2e-6
```

---

## 8. Vertical Setup (Differential to Single-Ended)

### AWG Differential Output Formula

When connecting AWG differential outputs to scope single-ended inputs:

```
Single-ended Vpp = AWG_amplitude / 2
```

### Vertical Scale Calculation

```python
# AWG amplitude (differential)
awg_amplitude = 0.25  # 250 mV

# Single-ended amplitude on scope
se_amplitude = awg_amplitude / 2  # 125 mV

# Trigger level (signal midpoint for 0-to-Vpp signal)
trigger_level = se_amplitude / 2  # 62.5 mV

# Scope offset = trigger level (centers signal)
scope_offset = trigger_level

# V scale: fit signal in ~6 divisions
v_scale = se_amplitude / 6  # ~20 mV/div
```

---

## 9. Screenshot Capture Pattern

### Robust Screenshot Implementation

```python
def _capture_screenshot(self, label: str) -> str:
    """Capture oscilloscope screenshot with fallback paths."""
    if not self.output_dir:
        return ""
    
    try:
        filename = f"{label}.png"
        filepath = Path(self.output_dir) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Try multiple scope paths
        scope_filename = f"temp_{label}.png"
        scope_paths = [f"C:/Temp/{scope_filename}", f"C:/{scope_filename}"]
        data = None
        used_path = None
        
        for scope_path in scope_paths:
            try:
                self.inst.scope_write(f'SAVe:IMAGe "{scope_path}"')
                self.inst.scope_query("*OPC?")
                self.inst.scope_write(f'FILESystem:READFile "{scope_path}"')
                data = self.inst.scope.read_raw()
                used_path = scope_path
                break
            except Exception:
                continue
        
        if data is None:
            self.log("Screenshot error: all scope paths failed")
            return ""
        
        with open(filepath, 'wb') as f:
            f.write(data)
        
        # Delete temp file from scope
        try:
            self.inst.scope_write(f'FILESystem:DELEte "{used_path}"')
        except:
            pass
        
        return str(filepath)
        
    except Exception as e:
        self.log(f"Screenshot error: {e}")
        return ""
```

### Assigning Screenshots to Test Points

```python
# Single screenshot for multiple measurements in same view
screenshot_path = self._capture_screenshot("delay_view")
for tp in delay_test_points:
    tp.screenshot_path = screenshot_path
```

---

## 10. Pass/Fail and Status Handling

### TestStatus Values

```python
class TestStatus(Enum):
    NOT_RUN = "Not Run"   # Initial state
    RUNNING = "Running"   # Test in progress
    PASS = "PASS"         # Within limits
    FAIL = "FAIL"         # Outside limits
    ERROR = "ERROR"       # Measurement error (9.9E37, timeout)
    SKIPPED = "Skipped"   # User disabled or dependency failed
```

### Status Assignment Pattern

```python
def run_single_test(self, tp: TestPoint, config: Dict) -> TestPoint:
    tp.status = TestStatus.RUNNING
    
    try:
        value = self._read_measurement(tp.test_id)
        
        if value is None or abs(value) > 1e30:
            tp.status = TestStatus.ERROR
            tp.extra_data['error'] = "Invalid measurement"
        else:
            tp.measured_value = value
            if tp.lower_limit <= value <= tp.upper_limit:
                tp.status = TestStatus.PASS
            else:
                tp.status = TestStatus.FAIL
                
    except Exception as e:
        tp.status = TestStatus.ERROR
        tp.extra_data['error'] = str(e)
    
    return tp
```

---

## 11. Common Patterns

### Measurement Clear and Setup

```python
self.inst.scope_write("MEASUrement:DELETEALL")
time.sleep(0.2)

for i, spec in enumerate(MEASUREMENTS, 1):
    self.inst.scope_write(f"MEASUrement:MEAS{i}:TYPe {spec.meas_type}")
    self.inst.scope_write(f"MEASUrement:MEAS{i}:SOUrce1 {spec.source1}")
    if spec.source2:
        self.inst.scope_write(f"MEASUrement:MEAS{i}:SOUrce2 {spec.source2}")
    self.inst.scope_write(f"MEASUrement:MEAS{i}:STATE ON")
```

### Reading Measurement with Unit Conversion

```python
def _read_measurement(self, meas_num: int, scale: float = 1.0) -> Optional[float]:
    try:
        response = self.inst.scope_query(
            f"MEASUrement:MEAS{meas_num}:RESUlts:CURRentacq:MEAN?"
        )
        value = float(response)
        
        if abs(value) > 1e30:  # Invalid (9.9E37)
            return None
        
        return value * scale
        
    except Exception as e:
        self.log(f"Read error: {e}")
        return None
```

---

## 12. Debugging Tips

### SCPI Command Verification

1. Test commands directly on scope via TekVISA or web interface
2. Check programmer manual for exact syntax
3. Use `*OPC?` after state-changing commands

### Measurement Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 9.9E37 returned | No trigger | Check trigger source/level |
| Wrong value | Wrong source | Verify SOUrce1/SOUrce2 |
| Timeout | Acquisition stuck | Check ACQuire:STATE |
| Screenshot blank | Wrong path | Try C:/Temp/ fallback |

### Logging Best Practices

```python
self.log(f"Configuring MEAS{n}: {spec.name}")
self.log(f"  Type: {spec.meas_type}")
self.log(f"  Source: {spec.source1}")
self.log(f"  Result: {value:.6f} {spec.unit}")
```

---

## 13. AWG70000 HSS Plug-in for PRBS

The HSS (High Speed Serial) plug-in enables PRBS pattern generation on AWG70000 series.

### PRBS7 Setup Example

```python
# Standard PRBS7: 2^7 - 1 = 127 bits
data_rate = 250e6  # 250 Mbps
amplitude = 0.5    # 500 mV differential

# Configure HSS for PRBS
self.awg.write(f"HSSources:HSSource1:DATA:PATTern:TYPE PRBS7")
self.awg.write(f"HSSources:HSSource1:DATA:DATARate {data_rate}")
self.awg.write(f"HSSources:HSSource1:OUTPut:LEVel:AMPLitude {amplitude}")
```

---

## 14. Serial Pattern Measurements

### Pattern Length Verification

```python
# Add pattern length measurement
self.inst.scope_write("MEASUrement:MEAS1:TYPe PATTERNLENGTH")
self.inst.scope_write("MEASUrement:MEAS1:SOUrce1 CH1")
self.inst.scope_write("MEASUrement:MEAS1:STATE ON")

# Read pattern length
pattern_len = int(float(self.inst.scope_query(
    "MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?"
)))

# For PRBS7, expect 127 bits
if pattern_len != 127:
    self.log(f"WARNING: Pattern length {pattern_len} != 127")
```

### Data Rate Measurement

```python
self.inst.scope_write("MEASUrement:MEAS2:TYPe DATARATE")
self.inst.scope_write("MEASUrement:MEAS2:SOUrce1 CH1")
self.inst.scope_write("MEASUrement:MEAS2:STATE ON")
```

---

## 15. Setup Diagram Creation

### Matplotlib Block Diagram Example

```python
def generate_setup_diagram(output_path: Path) -> str:
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#1E2A38')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    
    # Draw DUT box
    dut_box = plt.Rectangle((10, 40), 20, 20, 
                             facecolor='#2C3E50', edgecolor='#00A3E0', lw=2)
    ax.add_patch(dut_box)
    ax.text(20, 50, "DUT", ha='center', va='center', 
            color='white', fontsize=14, fontweight='bold')
    
    # Draw scope box
    scope_box = plt.Rectangle((70, 30), 25, 40,
                               facecolor='#2C3E50', edgecolor='#00A3E0', lw=2)
    ax.add_patch(scope_box)
    ax.text(82.5, 50, "MSO6B", ha='center', va='center',
            color='white', fontsize=12, fontweight='bold')
    
    # Draw connections
    ax.plot([30, 70], [55, 55], color='#F39C12', lw=2)
    ax.text(50, 58, "CH1 - 50Ω", ha='center', color='#BDC3C7')
    
    plt.savefig(output_path, facecolor='#1E2A38', dpi=150)
    plt.close()
    return str(output_path)
```

---

## 16. Results Table Format

### Standard Results Table

```python
self.log("=" * 110)
self.log(f"{'#':<4} {'Test Name':<20} {'Nominal':>14} {'Lower Limit':>14} "
         f"{'Upper Limit':>14} {'Measured':>14} {'Status':>8}")
self.log("-" * 110)

for tp in self.test_points:
    nominal_str = self._format_value(tp.nominal_value, tp.unit)
    lower_str = self._format_value(tp.lower_limit, tp.unit)
    upper_str = self._format_value(tp.upper_limit, tp.unit)
    measured_str = self._format_value(tp.measured_value, tp.unit)
    
    self.log(f"{tp.test_id:<4} {tp.name:<20} {nominal_str:>14} {lower_str:>14} "
             f"{upper_str:>14} {measured_str:>14} {tp.status.value:>8}")

self.log("=" * 110)
```

---

## 17. Eye Diagram Measurements

Eye diagram analysis requires specific measurement types and configuration.

### CRITICAL: SCPI Measurement Type Names

**Do NOT use "EYEHEIGHT" or "EYEWIDTH"** - these measurement types do not exist!

| Measurement | Correct SCPI Type | Wrong (Does Not Exist) |
|-------------|-------------------|------------------------|
| Eye Height | `HEIGHT` | ~~EYEHEIGHT~~ |
| Eye Width | `WIDTH` | ~~EYEWIDTH~~ |
| Pattern Length | `PATTERNLENGTH` | |
| Data Rate | `DATARATE` | |
| Deterministic Jitter | `DJ` | |

### Available Eye Diagram Measurements

| SCPI Type | Name | Unit | Description |
|-----------|------|------|-------------|
| HEIGHT | Eye Height | V | Vertical eye opening |
| WIDTH | Eye Width | s | Horizontal eye opening |
| PATTERNLENGTH | Pattern Length | bits | Bits in repeating pattern (e.g., 127 for PRBS7) |
| DATARATE | Data Rate | bps | Measured bit rate |
| DJ | Deterministic Jitter | s | DJ component of total jitter |

### Measurement Setup Example

```python
# Configure global clock recovery first
data_rate_hz = 1.62e9  # 1.62 Gbps
self.inst.scope_write("MEASUrement:CLOCKRecovery:MODel STANDARD")
self.inst.scope_write("MEASUrement:CLOCKRecovery:NOMINALOFFset:SELECTIONtype MANUAL")
self.inst.scope_write(f"MEASUrement:CLOCKRecovery:NOMINALOFFset {data_rate_hz}")

# Eye Height - uses HEIGHT, not EYEHEIGHT!
self.inst.scope_write('MEASUrement:ADDNew "MEAS1"')
self.inst.scope_write("MEASUrement:MEAS1:TYPe HEIGHT")
self.inst.scope_write(f"MEASUrement:MEAS1:SOUrce {source}")
self.inst.scope_write("MEASUrement:MEAS1:CLOCKRecovery:GLOBal 1")
self.inst.scope_write("MEASUrement:MEAS1:DISPlaystat:ENABle ON")
self.inst.scope_write("MEASUrement:MEAS1:STATE ON")

# Eye Width - uses WIDTH, not EYEWIDTH!
self.inst.scope_write('MEASUrement:ADDNew "MEAS2"')
self.inst.scope_write("MEASUrement:MEAS2:TYPe WIDTH")
self.inst.scope_write(f"MEASUrement:MEAS2:SOUrce {source}")
self.inst.scope_write("MEASUrement:MEAS2:CLOCKRecovery:GLOBal 1")
self.inst.scope_write("MEASUrement:MEAS2:DISPlaystat:ENABle ON")
self.inst.scope_write("MEASUrement:MEAS2:STATE ON")

# Deterministic Jitter
self.inst.scope_write('MEASUrement:ADDNew "MEAS3"')
self.inst.scope_write("MEASUrement:MEAS3:TYPe DJ")
self.inst.scope_write(f"MEASUrement:MEAS3:SOUrce {source}")
self.inst.scope_write("MEASUrement:MEAS3:CLOCKRecovery:GLOBal 1")
self.inst.scope_write("MEASUrement:MEAS3:STATE ON")
```

### Eye Diagram Plot Configuration

```python
self.inst.scope_write('PLOT:ADDNew "PLOT1"')
self.inst.scope_write("PLOT:PLOT1:TYPe EYEDIAGRAM")
self.inst.scope_write(f"PLOT:PLOT1:SOUrce {source}")
self.inst.scope_write("PLOT:PLOT1:CLOCKRecovery:GLOBal ON")
self.inst.scope_write("PLOT:PLOT1:BITType ALLBits")
self.inst.scope_write("PLOT:PLOT1:STATE ON")
```

### Acquisition Model: Single Long Capture

For eye diagram and jitter analysis, **one long acquisition is usually sufficient**:

- 10 µs/div at 1.62 Gbps captures ~162,000 UIs in a single acquisition
- This provides excellent statistics without multiple acquisitions
- Default to `num_acquisitions = 1`

```python
# Calculate captured UIs
ui_seconds = 1.0 / data_rate_hz
total_time = horizontal_scale * 10  # 10 divisions
num_uis = total_time / ui_seconds
# Example: 10 µs × 10 divs / 617 ps = ~162,000 UIs
```

### Multi-Acquisition: Population Limiting Required

If using multiple acquisitions, **you MUST enable population limiting** for correct statistics:

```python
if num_acquisitions > 1:
    for meas_num in measurement_numbers:
        self.inst.scope_write(f"MEASUrement:MEAS{meas_num}:POPUlation:LIMIT:STATE ON")
        self.inst.scope_write(f"MEASUrement:MEAS{meas_num}:POPUlation:LIMIT:VALue {num_acquisitions}")
```

Without population limiting, mean and standard deviation values are computed incorrectly across acquisitions.

---

## 18. Reference Waveform Handling

Reference waveforms (REF1, REF2, etc.) are **static, pre-captured data**. They require special handling.

### CRITICAL: No Acquisition for Reference Waveforms!

When the source is a reference waveform, **skip ALL acquisition commands**:

```python
ref_mode = source.startswith("REF")

if ref_mode:
    # REFERENCE MODE: Waveform is already captured
    self._log("REFERENCE MODE: Using pre-captured waveform")
    self.inst.scope_write(f"DISplay:GLObal:{source}:STATE ON")
    time.sleep(0.5)  # Brief wait for measurements to process
else:
    # CHANNEL MODE: Trigger and acquire
    self.inst.scope_write("ACQuire:STOPAfter SEQuence")
    self.inst.scope_write("ACQuire:STATE RUN")
    # ... wait for acquisition ...
```

### Commands to SKIP in Reference Mode

- `ACQuire:STATE RUN`
- `ACQuire:STOPAfter SEQuence` or `RUNSTop`
- `ACQuire:NUMACq?` queries
- Trigger configuration commands
- Acquisition wait loops

### Why Reference Mode Fails Without This

Reference waveforms have no trigger source - they're already captured. If you send `ACQuire:STATE RUN`, the scope waits for a trigger that never comes, causing timeouts.

### IMPORTANT: Reference Waveform File Location

**Reference waveforms must be accessible from the oscilloscope's file system, NOT the PC running Tek PTA.**

| Scenario | Works? | Notes |
|----------|--------|-------|
| TekScope PC | ✅ Yes | Scope and PC share filesystem |
| Networked drive (both see) | ✅ Yes | Map same share on scope and PC |
| Local PC drive only | ❌ No | Scope cannot see PC's local files |

When using Tek PTA's "Load Reference Waveform" feature, the file must be accessible from the scope's perspective. If the scope can't see the file path, the waveform won't load.

**Workarounds:**
1. Use TekScope PC where scope/PC share filesystem
2. Use a network share accessible by both scope and PC
3. Manually load waveforms on scope before running test

### Auto-Loading Reference Waveforms

```python
def _auto_load_references(self, config):
    """Load reference waveforms at test start."""
    if config.get("source_mode") != "REFERENCE":
        return
    
    for ref in ["ref_source", "ref_source_1", "ref_source_2"]:
        ref_name = config.get(ref)
        if ref_name:
            self.inst.scope_write(f"DISplay:GLObal:{ref_name}:STATE ON")
            self._log(f"Enabled display of {ref_name}")
```

---

## Reference Files

- **Production examples**: 
  - `test_suites/awg70002b_pulse_timing_suite.py` (statistics-based)
  - `test_suites/prbs7_dut_test_suite.py` (single acquisition, PRBS)
  - `test_suites/eye_diagram_test_suite.py` (eye diagram measurements)
  - `test_suites/dual_pulse_timing_suite.py` (reference waveform mode)
- **Built-in engines**: `tek_pta.py`
- **Plugin API**: `tek_pta_plugin_api.py`
- **Setup diagrams**: `test_suites/images/`
- **Lessons learned**: `lessons_learned/`

---

*End of Tek PTA Plugin Development Guide v5.2*
