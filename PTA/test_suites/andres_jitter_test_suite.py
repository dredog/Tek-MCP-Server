#!/usr/bin/env python3
"""
Andre's Jitter Test Suite for Tek PTA
=====================================

Eye diagram and jitter analysis for high-speed serial signals.

Measurements (per input channel + differential):
- TIE (Time Interval Error) - Info only, no pass/fail
- PJ (Periodic Jitter) - < 40 ps
- RJ (Random Jitter) - < 12 ps  
- DJ (Deterministic Jitter) - < 60 ps
- Eye Width - > 100 ps
- Eye Height - > 250 mV (single-ended), > 500 mV (differential)
- Data Rate - 4.995 to 5.005 Gbps
- Pattern Length - Exactly 511 bits

Clock Recovery: PLL with PCIE_GEN2 standard (5 Gbps)

Plots captured:
- Eye Diagram
- Composite Jitter Histogram

Author: Andre Asbury
Date: 2026-02-03
"""

import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


# =============================================================================
# PLUGIN API DEFINITIONS (copied from tek_pta_plugin_api.py for portability)
# =============================================================================

class TestStatus(Enum):
    """Status of a test point"""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASSED = "Passed"
    FAILED = "Failed"
    ERROR = "Error"
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
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    measured_value: float = 0.0
    status: TestStatus = TestStatus.NOT_RUN
    error_pct: float = 0.0
    screenshot_path: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def evaluate(self) -> TestStatus:
        """Evaluate pass/fail based on limits"""
        if self.measured_value is None or self.measured_value == 0.0:
            # Check if it's a valid zero or just not measured
            if self.status == TestStatus.RUNNING:
                return TestStatus.ERROR
        
        # If no limits, it's info-only - always pass
        if self.lower_limit is None and self.upper_limit is None:
            return TestStatus.PASSED
            
        # Check limits
        if self.lower_limit is not None and self.measured_value < self.lower_limit:
            return TestStatus.FAILED
        if self.upper_limit is not None and self.measured_value > self.upper_limit:
            return TestStatus.FAILED
            
        return TestStatus.PASSED


@dataclass 
class TestSuitePlugin:
    """Definition of a test suite plugin"""
    name: str
    description: str
    test_type: str
    version: str = "1.0"
    author: str = ""
    required_instruments: List[str] = field(default_factory=list)
    setup_diagram_path: str = ""
    engine_class: Optional[type] = None


class TestEngineBase:
    """Base class for custom test engines"""
    
    def __init__(self, instrument_manager):
        self.inst = instrument_manager
        self.test_points: List[TestPoint] = []
        self.running = False
        self.output_dir = None
        self.reference_config = None
        self.screenshots: List[str] = []
        
        # Callbacks - set by main application
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[float, str], None]] = None
        self.on_test_start: Optional[Callable[[TestPoint], None]] = None
        self.on_test_complete: Optional[Callable[[TestPoint], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[int, int], None]] = None  # (passed, failed)
        
    def _log(self, msg: str):
        """Log a message"""
        if self.on_log:
            self.on_log(msg)
            
    def _progress(self, pct: float, msg: str = ""):
        """Update progress"""
        if self.on_progress:
            self.on_progress(pct, msg)
    
    def generate_test_points(self, config: Dict[str, Any] = None) -> List[TestPoint]:
        """
        Generate the list of test points from configuration.
        Override this method to define your test points.
        Called by Tek PTA when the test suite is selected.
        """
        raise NotImplementedError("Subclasses must implement generate_test_points()")
            
    def run(self, config: Dict[str, Any]) -> List[TestPoint]:
        """Override this method to implement test logic"""
        raise NotImplementedError("Subclasses must implement run()")
        
    def stop(self):
        """Override to handle stop requests"""
        self.running = False


# =============================================================================
# ANDRE'S JITTER TEST ENGINE
# =============================================================================

class AndresJitterTestEngine(TestEngineBase):
    """
    Eye diagram and jitter analysis test engine.
    
    Performs comprehensive jitter measurements using the MSO's built-in
    JITTERSUMMARY measurement plus individual eye measurements.
    """
    
    # Default test configuration
    DEFAULT_DATA_RATE_GBPS = 5.0
    DEFAULT_PATTERN_LENGTH = 511
    PLL_STANDARD = "PCIE_GEN2"  # For 5 Gbps
    
    # Measurement definitions with limits (in display units)
    # Format: (name_suffix, nominal, lower, upper, unit)
    MEASUREMENTS = [
        ('TIE', 0, None, None, 'ps'),           # Info only
        ('PJ', 0, None, 40, 'ps'),              # < 40 ps
        ('RJ', 0, None, 12, 'ps'),              # < 12 ps
        ('DJ', 0, None, 60, 'ps'),              # < 60 ps
        ('Eye Width', 0, 100, None, 'ps'),      # > 100 ps
        ('Eye Height', 0, 250, None, 'mV'),     # > 250 mV (SE), > 500 mV (Diff)
        ('Data Rate', 5.0, 4.995, 5.005, 'Gbps'),
        ('Pattern Length', 511, 511, 511, 'bits'),
    ]
    
    # Sources to test
    SOURCES = ['Input 1', 'Input 2', 'Differential']
    
    def __init__(self, instrument_manager):
        super().__init__(instrument_manager)
        self.inst = instrument_manager  # Alias for compatibility
        self._stop_requested = False
        self._measurement_slots = {}  # Track which MEAS<x> slots we're using
        self.running = False
        self.output_dir = None
        self.reference_config = None
        
    def generate_test_points(self, config: Dict[str, Any] = None) -> List[TestPoint]:
        """
        Generate the list of test points for display in the UI.
        Called by Tek PTA when the test suite is selected.
        """
        self.test_points = []
        test_id = 0
        
        for source in self.SOURCES:
            is_diff = (source == 'Differential')
            
            for meas_name, nominal, lower, upper, unit in self.MEASUREMENTS:
                test_id += 1
                
                # Double eye height limit for differential
                actual_lower = lower
                if meas_name == 'Eye Height' and is_diff:
                    actual_lower = 500  # 500 mV for differential
                    
                tp = TestPoint(
                    test_id=test_id,
                    name=f"{source} {meas_name}",
                    nominal_value=nominal,
                    lower_limit=actual_lower,
                    upper_limit=upper,
                    unit=unit,
                )
                self.test_points.append(tp)
                
        return self.test_points
        
    def stop(self):
        """Handle stop request"""
        self._stop_requested = True
        self.running = False
        self._log("Stop requested - will halt after current measurement")
        
    def _log(self, msg: str):
        """Log a message"""
        if self.on_log:
            self.on_log(msg)
            
    def _progress(self, pct: float, msg: str = ""):
        """Update progress"""
        if self.on_progress:
            self.on_progress(pct, msg)
        
    def _write(self, cmd: str):
        """Write SCPI command to scope"""
        self.inst.scope_write(cmd)
        
    def _query(self, cmd: str) -> str:
        """Query scope and return response"""
        return self.inst.scope_query(cmd).strip()
        
    def _query_float(self, cmd: str) -> Optional[float]:
        """Query scope and return float value"""
        try:
            response = self._query(cmd)
            # Handle special values
            if response in ['9.9E+37', '9.91E+37', 'NAN', 'INF', '-INF', '']:
                return None
            return float(response)
        except (ValueError, Exception) as e:
            self._log(f"Error querying {cmd}: {e}")
            return None
            
    def _wait_for_opc(self, timeout: float = 30.0):
        """Wait for operation complete"""
        self.inst.scope_query('*OPC?')
        
    def _take_screenshot(self, output_dir: Path, name: str) -> str:
        """Capture screenshot from scope using SAVe:IMAGe (more reliable than HARDCopy:DATA?)"""
        try:
            timestamp = time.strftime("%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = output_dir / filename
            
            # Scope temp file path (C:/Temp is usually available)
            scope_temp_path = "C:/Temp/tek_pta_screenshot.png"
            
            # Step 1: Save image to scope filesystem
            self._write(f'SAVe:IMAGe "{scope_temp_path}"')
            self._wait_for_opc(15)  # Wait for save to complete
            time.sleep(0.3)  # Brief settle time
            
            # Step 2: Transfer file from scope to PC
            self._write(f'FILESystem:READFile "{scope_temp_path}"')
            
            # Increase timeout for file transfer
            old_timeout = self.inst.scope.timeout
            self.inst.scope.timeout = 60000  # 60 seconds for large images
            try:
                raw_data = self.inst.scope.read_raw()
            finally:
                self.inst.scope.timeout = old_timeout
            
            # Step 3: Parse IEEE 488.2 block header (#<n><length><data>)
            if raw_data[0:1] == b'#':
                num_digits = int(raw_data[1:2])
                data_length = int(raw_data[2:2+num_digits])
                image_data = raw_data[2+num_digits:2+num_digits+data_length]
            else:
                image_data = raw_data
                
            # Step 4: Save to local file
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Step 5: Clean up temp file on scope
            try:
                self._write(f'FILESystem:DELEte "{scope_temp_path}"')
            except Exception:
                pass  # Ignore cleanup errors
                
            self._log(f"Screenshot saved: {filename}")
            self.screenshots.append(str(filepath))
            return str(filepath)
            
        except Exception as e:
            self._log(f"Screenshot error: {e}")
            return ""
            
    def _delete_all_measurements(self):
        """Delete all existing measurements"""
        self._write('MEASUrement:DELETEALL')
        self._wait_for_opc()
        self._measurement_slots.clear()
        
    def _delete_all_plots(self):
        """Delete all existing plots"""
        try:
            plot_list = self._query('PLOT:LIST?')
            if plot_list and plot_list != '""':
                plots = plot_list.replace('"', '').split(',')
                for plot in plots:
                    if plot.strip():
                        self._write(f'PLOT:DELete "{plot.strip()}"')
        except Exception as e:
            self._log(f"Note: Could not clear plots: {e}")
            
    def _setup_math_differential(self, source1: str, source2: str, math_num: int = 1) -> str:
        """Create a math channel for differential measurement."""
        math_name = f"MATH{math_num}"
        
        self._write(f'MATH:{math_name}:TYPe BASic')
        self._write(f'MATH:{math_name}:FUNCtion SUBtract')
        self._write(f'MATH:{math_name}:SOUrce1 {source1}')
        self._write(f'MATH:{math_name}:SOUrce2 {source2}')
        self._write(f'DISplay:GLObal:MATH{math_num}:STATE ON')
        
        self._log(f"Created {math_name} = {source1} - {source2}")
        return math_name
        
    def _add_measurement(self, meas_type: str, source: str) -> int:
        """Add a measurement and return its slot number."""
        self._write(f'MEASUrement:ADDMEAS {meas_type}')
        self._wait_for_opc()
        
        meas_list = self._query('MEASUrement:LIST?')
        slots = [int(s.replace('MEAS', '')) for s in meas_list.replace('"', '').split(',') if s.strip()]
        
        if not slots:
            raise RuntimeError(f"Failed to add {meas_type} measurement")
            
        meas_num = max(slots)
        self._write(f'MEASUrement:MEAS{meas_num}:SOUrce1 {source}')
        
        # Configure clock recovery for jitter measurements
        if meas_type in ['TIE', 'JITTERSUMMARY', 'RJ', 'DJ', 'PJ', 'WIDTH', 'HEIGHT', 'DATARATE']:
            self._write(f'MEASUrement:MEAS{meas_num}:CLOCKRecovery:METHod PLL')
            self._write(f'MEASUrement:MEAS{meas_num}:CLOCKRecovery:STAndard {self.PLL_STANDARD}')
            
        if meas_type == 'JITTERSUMMARY':
            self._write(f'MEASUrement:MEAS{meas_num}:JITTERSummary:TIE ON')
            self._write(f'MEASUrement:MEAS{meas_num}:JITTERSummary:RJ ON')
            self._write(f'MEASUrement:MEAS{meas_num}:JITTERSummary:DJ ON')
            self._write(f'MEASUrement:MEAS{meas_num}:JITTERSummary:PJ ON')
            
        self._measurement_slots[f"{meas_type}_{source}"] = meas_num
        self._log(f"Added MEAS{meas_num}: {meas_type} on {source}")
        
        return meas_num
        
    def _add_plot(self, plot_type: str, source_meas: int, plot_num: int) -> int:
        """Add a plot linked to a measurement"""
        plot_name = f"PLOT{plot_num}"
        
        self._write(f'PLOT:ADDNew "{plot_name}"')
        self._wait_for_opc()
        self._write(f'PLOT:{plot_name}:TYPe {plot_type}')
        self._write(f'PLOT:{plot_name}:SOUrce1 MEAS{source_meas}')
        
        self._log(f"Added {plot_name}: {plot_type} from MEAS{source_meas}")
        return plot_num
        
    def _get_jitter_summary_result(self, meas_num: int, component: str) -> Optional[float]:
        """Get a specific component from JITTERSUMMARY measurement."""
        cmd = f'MEASUrement:MEAS{meas_num}:SUBGROUP:RESUlts:CURRentacq:MEAN? "{component}"'
        return self._query_float(cmd)
        
    def _get_measurement_result(self, meas_num: int) -> Optional[float]:
        """Get the mean result from a standard measurement"""
        cmd = f'MEASUrement:MEAS{meas_num}:RESUlts:CURRentacq:MEAN?'
        return self._query_float(cmd)
        
    def _run_acquisition(self, use_refs: bool):
        """Run acquisition to populate measurements."""
        if use_refs:
            self._log("Using reference waveforms - no acquisition needed")
            time.sleep(2.0)
        else:
            self._write('ACQuire:STOPAfter SEQuence')
            self._write('ACQuire:STATE RUN')
            
            timeout = 30.0
            start = time.time()
            while time.time() - start < timeout:
                state = self._query('ACQuire:STATE?')
                if state == '0':
                    break
                time.sleep(0.5)
            else:
                self._log("Warning: Acquisition timeout")
                
        time.sleep(1.0)
        self._wait_for_opc()
        
    def _convert_to_display_units(self, value: Optional[float], unit: str) -> float:
        """Convert SI units to display units"""
        if value is None:
            return 0.0
            
        if unit == 'ps':
            return value * 1e12
        elif unit == 'mV':
            return value * 1e3
        elif unit == 'Gbps':
            return value / 1e9
        else:
            return value

    def run(self, config: Dict[str, Any]) -> List[TestPoint]:
        """Run the jitter test suite."""
        self._stop_requested = False
        self.running = True
        self.screenshots = []
        
        # Get configuration
        use_refs = config.get('use_references', False)
        if self.reference_config and self.reference_config.enabled:
            use_refs = True
            
        source1 = config.get('source1', 'REF1' if use_refs else 'CH1')
        source2 = config.get('source2', 'REF2' if use_refs else 'CH2')
        output_dir = Path(config.get('output_dir', self.output_dir or Path.cwd()))
        
        # Make sure test points are generated
        if not self.test_points:
            self.generate_test_points(config)
            
        try:
            self._log("=" * 60)
            self._log("ANDRE'S JITTER TEST")
            self._log("=" * 60)
            self._log(f"Source 1: {source1}")
            self._log(f"Source 2: {source2}")
            self._log(f"Differential: MATH1 = {source1} - {source2}")
            self._log(f"Clock Recovery: PLL with {self.PLL_STANDARD}")
            self._log("=" * 60)
            
            # Initialize scope
            self._progress(5, "Initializing scope...")
            self._delete_all_measurements()
            self._delete_all_plots()
            
            # Create differential math channel
            self._progress(10, "Setting up differential math...")
            math_diff = self._setup_math_differential(source1, source2, math_num=1)
            
            # Map source labels to actual SCPI sources
            source_map = {
                'Input 1': source1,
                'Input 2': source2,
                'Differential': math_diff,
            }
            
            plot_num = 1
            test_idx = 0
            
            for src_idx, source_label in enumerate(self.SOURCES):
                if self._stop_requested:
                    self._log("Test stopped by user")
                    break
                    
                source = source_map[source_label]
                is_diff = (source_label == 'Differential')
                base_progress = 15 + (src_idx * 25)
                
                self._progress(base_progress, f"Testing {source_label} ({source})...")
                self._log(f"\n--- {source_label}: {source} ---")
                
                # Add measurements
                jitter_meas = self._add_measurement('JITTERSUMMARY', source)
                height_meas = self._add_measurement('HEIGHT', source)
                width_meas = self._add_measurement('WIDTH', source)
                datarate_meas = self._add_measurement('DATARATE', source)
                pattern_meas = self._add_measurement('PATTERNLENGTH', source)
                
                # Add plots
                eye_plot = self._add_plot('EYEDIAGRAM', jitter_meas, plot_num)
                plot_num += 1
                hist_plot = self._add_plot('CJHIST', jitter_meas, plot_num)
                plot_num += 1
                
                # Run acquisition
                self._progress(base_progress + 5, f"Acquiring {source_label}...")
                self._run_acquisition(use_refs)
                
                # Measurement mapping: (measurement_name, scpi_type, meas_num, is_subgroup)
                meas_map = {
                    'TIE': (jitter_meas, True, 'TIE'),
                    'PJ': (jitter_meas, True, 'PJ'),
                    'RJ': (jitter_meas, True, 'RJ'),
                    'DJ': (jitter_meas, True, 'DJ'),
                    'Eye Width': (width_meas, False, None),
                    'Eye Height': (height_meas, False, None),
                    'Data Rate': (datarate_meas, False, None),
                    'Pattern Length': (pattern_meas, False, None),
                }
                
                self._progress(base_progress + 15, f"Reading {source_label} results...")
                
                # Update test points for this source
                for meas_name, (meas_num, is_subgroup, subgroup_name) in meas_map.items():
                    # Find the corresponding test point
                    tp = self.test_points[test_idx]
                    test_idx += 1
                    
                    tp.status = TestStatus.RUNNING
                    if self.on_test_start:
                        self.on_test_start(tp)
                    
                    # Get the raw result
                    if is_subgroup:
                        raw_value = self._get_jitter_summary_result(meas_num, subgroup_name)
                    else:
                        raw_value = self._get_measurement_result(meas_num)
                        
                    # Convert to display units
                    tp.measured_value = self._convert_to_display_units(raw_value, tp.unit)
                    
                    # Evaluate pass/fail
                    tp.status = tp.evaluate()
                    
                    if self.on_test_complete:
                        self.on_test_complete(tp)
                        
                    # Log result
                    limit_str = ""
                    if tp.lower_limit is not None:
                        limit_str += f">={tp.lower_limit}"
                    if tp.upper_limit is not None:
                        if limit_str:
                            limit_str += ", "
                        limit_str += f"<={tp.upper_limit}"
                    if not limit_str:
                        limit_str = "Info only"
                    self._log(f"  {meas_name}: {tp.measured_value:.3f} {tp.unit} [{limit_str}] - {tp.status.value}")
                    
                # Take screenshots
                self._progress(base_progress + 20, f"Capturing {source_label} screenshots...")
                
                self._write(f'DISplay:SELect:VIEW PLOTVIEW{eye_plot}')
                time.sleep(0.5)
                self._take_screenshot(output_dir, f"{source_label.replace(' ', '_')}_eye_diagram")
                
                self._write(f'DISplay:SELect:VIEW PLOTVIEW{hist_plot}')
                time.sleep(0.5)
                self._take_screenshot(output_dir, f"{source_label.replace(' ', '_')}_jitter_histogram")
                
            # Final summary
            self._progress(95, "Generating summary...")
            
            passed = sum(1 for tp in self.test_points if tp.status == TestStatus.PASSED)
            failed = sum(1 for tp in self.test_points if tp.status == TestStatus.FAILED)
            total = len(self.test_points)
            
            self._log("\n" + "=" * 60)
            self._log("TEST SUMMARY")
            self._log("=" * 60)
            self._log(f"Total Tests: {total}")
            self._log(f"Passed: {passed}")
            self._log(f"Failed: {failed}")
            self._log(f"Pass Rate: {passed/total*100:.1f}%" if total > 0 else "N/A")
            self._log("=" * 60)
            
            self._progress(100, "Complete")
            
            if self.on_complete:
                self.on_complete(passed, failed)
            
        except Exception as e:
            self._log(f"ERROR: {e}")
            import traceback
            self._log(traceback.format_exc())
            
        self.running = False
        return self.test_points


# =============================================================================
# PLUGIN REGISTRATION
# =============================================================================

def register_suites() -> List[TestSuitePlugin]:
    """Register this test suite with Tek PTA"""
    return [
        TestSuitePlugin(
            name="Andre's Jitter Test",
            description="Eye diagram and jitter analysis for 5 Gbps serial signals. "
                       "Measures TIE, RJ, DJ, PJ, eye width, eye height, data rate, "
                       "and pattern length on two inputs plus their differential.",
            test_type="andres_jitter",
            version="1.0",
            author="Andre Asbury",
            required_instruments=["Oscilloscope"],
            engine_class=AndresJitterTestEngine,
        )
    ]


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    print("Andre's Jitter Test Suite")
    print("=" * 40)
    print("This plugin should be loaded by Tek PTA.")
    print("Place this file in your test_suites folder.")
    print()
    print("Test Configuration:")
    print(f"  Data Rate: {AndresJitterTestEngine.DEFAULT_DATA_RATE_GBPS} Gbps")
    print(f"  Pattern Length: {AndresJitterTestEngine.DEFAULT_PATTERN_LENGTH} bits")
    print(f"  PLL Standard: {AndresJitterTestEngine.PLL_STANDARD}")
    print()
    print("Test Points (24 total):")
    print("-" * 60)
    
    # Create a dummy engine to generate test points
    class DummyInstrumentManager:
        def get(self, name):
            return None
    
    engine = AndresJitterTestEngine(DummyInstrumentManager())
    test_points = engine.generate_test_points()
    
    for tp in test_points:
        limit_str = ""
        if tp.lower_limit is not None and tp.upper_limit is not None:
            if tp.lower_limit == tp.upper_limit:
                limit_str = f"= {tp.lower_limit}"
            else:
                limit_str = f"{tp.lower_limit} to {tp.upper_limit}"
        elif tp.lower_limit is not None:
            limit_str = f"> {tp.lower_limit}"
        elif tp.upper_limit is not None:
            limit_str = f"< {tp.upper_limit}"
        else:
            limit_str = "Info only"
            
        print(f"  {tp.test_id:2d}. {tp.name:<30} [{limit_str}] {tp.unit}")
