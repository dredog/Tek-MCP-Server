# Lessons Learned: Dual-Channel Pulse Timing Test & Plugin Structure

**Date:** 2026-02-04  
**Test Name:** Dual-Channel Pulse Timing Test Suite  
**Keywords:** plugin structure, TestSuitePlugin, TestEngineBase, TestPoint, register_suites, silent failure, reference waveform, REF1, REF2, instrument_manager, field order, dataclass

---

## Summary

Created a dual-channel pulse timing test suite for REF1/REF2 reference waveforms. During development, discovered critical plugin structure requirements that cause **silent loading failures** in Tek PTA when not followed exactly.

## Instruments Used

- MSO4/5/6 Series Oscilloscope
- Reference waveforms (REF1, REF2)

## Test Specifications

| Measurement | Nominal | Tolerance | Unit |
|-------------|---------|-----------|------|
| Delay (REF1→REF2) | 2.0 | ±0.01 | µs |
| Frequency | 104.2 | ±1.0 | kHz |
| Amplitude | 125.0 | ±0.1 | mV |
| Positive Duty Cycle | 10.0 | ±0.2 | % |
| Rise Time | 200.0 | ±50.0 | ps |

---

## CRITICAL: Plugin Structure Requirements

### The Problem

When a test suite plugin doesn't load in Tek PTA (clicking "Select" does nothing, no error shown), the cause is almost always **incorrect Plugin API dataclass structure**.

Tek PTA uses Python's dataclass system which is **very sensitive to field order and types**. If your local definitions don't match exactly, the plugin silently fails to load.

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
| TestSuitePlugin.engine_class position | Last field | Any other position |
| TestSuitePlugin config field name | `config` | `default_config` |
| TestEngineBase.__init__ signature | `__init__(self, instrument_manager)` | `__init__(self)` |
| TestPoint.measured_value type | `float = 0.0` | `Optional[float] = None` |
| TestStatus enum values | `PASS`, `FAIL`, `NOT_RUN` | `PASSED`, `FAILED`, `PENDING` |
| Missing TestStatus value | Include `ERROR` | Omit `ERROR` |
| Callback names | `on_log`, `on_progress` | `log_callback`, `progress_callback` |

### How to Debug

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
   - Copy the exact dataclass definitions from `awg70002b_pulse_timing_suite.py`
   - Don't try to "improve" or "simplify" them

---

## Reference Waveform Limitations

### IMPORTANT: Waveform File Location

**Reference waveforms must be accessible from the oscilloscope's file system, NOT the PC running Tek PTA.**

- ✅ Works: TekScope PC (scope and PC share filesystem)
- ✅ Works: Networked drive mapped on both PC and scope
- ❌ Does NOT work: Loading from local PC drive that scope cannot see

When using Tek PTA's "Load Reference Waveform" feature:
- The file is uploaded to the scope via SCPI
- But the upload goes to the PC's understanding of the path
- If the scope can't see that path, the waveform doesn't load

**Workaround:** 
1. Use TekScope PC where scope/PC share filesystem
2. Use a network share accessible by both
3. Manually load waveforms on scope before running test

### Reference Mode Considerations

When using REF1/REF2 as measurement sources:
- Skip all acquisition commands (no `ACQuire:STATE RUN`)
- Skip trigger configuration
- Just enable display and configure measurements
- Measurements work on static data

---

## Key SCPI Commands Used

### Measurement Setup
```
MEASUrement:DELETEALL
MEASUrement:MEAS<n>:TYPe DELAY|FREQUENCY|AMPLITUDE|PDUTY|RISETIME
MEASUrement:MEAS<n>:SOUrce1 REF1|REF2|CH1|CH3
MEASUrement:MEAS<n>:SOUrce2 REF1|REF2  (for DELAY)
MEASUrement:MEAS<n>:DELay:EDGE1 RISe|FALL
MEASUrement:MEAS<n>:DELay:EDGE2 RISe|FALL
MEASUrement:MEAS<n>:STATE ON
```

### Reading Measurements
```
MEASUrement:MEAS<n>:RESUlts:CURRentacq:MEAN?
```

### Reference Waveform Display
```
DISplay:WAVEView1:REF:REF1:STATE ON
DISplay:WAVEView1:REF:REF2:STATE ON
REF:REF1:VERTical:SCAle <volts_per_div>
REF:REF1:VERTical:POSition <divisions>
```

---

## Unit Conversions

| Measurement | Scope Returns | Display Unit | Scale Factor |
|-------------|---------------|--------------|--------------|
| Delay | seconds | µs | × 1e6 |
| Frequency | Hz | kHz | × 1e-3 |
| Amplitude | V | mV | × 1e3 |
| Duty Cycle | % | % | × 1.0 |
| Rise Time | seconds | ps | × 1e12 |

---

## Files Created

- `dual_pulse_timing_suite.py` - Complete test suite plugin

---

## Additional Notes

- Always copy Plugin API definitions from a **known working plugin** rather than writing from scratch
- When a plugin fails to load silently, it's almost always a dataclass structure issue
- The plugin system uses duck typing and dataclass field matching - mismatches fail silently
- Test your plugin import in a Python console before expecting it to work in Tek PTA

---

*End of Lessons Learned*
