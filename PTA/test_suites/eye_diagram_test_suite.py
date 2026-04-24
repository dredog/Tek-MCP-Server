#!/usr/bin/env python3
"""
Eye Diagram Test Suite for Tek PTA
==================================

Automated eye diagram analysis for high-speed serial signals.

This test suite defines the specific measurements used for eye diagram testing:
- Eye Height (HEIGHT) - Voltage opening of the eye in mV
- Eye Width (WIDTH) - Timing opening of the eye in ps and %UI
- Pattern Length (PATTERNLENGTH) - Number of bits in repeating pattern
- Data Rate (DATARATE) - Measured data rate in Gbps
- Deterministic Jitter (DJ) - DJ component in ps

IMPORTANT - SCPI Measurement Types:
- Eye Height uses "HEIGHT" (NOT "EYEHEIGHT" - that doesn't exist!)
- Eye Width uses "WIDTH" (NOT "EYEWIDTH" - that doesn't exist!)

Features:
- Pass/fail testing against configurable limits
- Single long acquisition (10 µs/div) captures thousands of UIs
- Multi-acquisition mode with population limiting for statistics
- Reference waveform support (no acquisition needed)

Requirements:
- MSO4/5/6 series oscilloscope
- DJA (Jitter and Eye Analysis) license for jitter measurements

Author: Andre / Tek PTA Framework
Date: 2026-02-03
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import time
import os
import math
from datetime import datetime


# =============================================================================
# TEST SUITE PLUGIN DEFINITION (matches tek_pta_plugin_api.py)
# =============================================================================

class TestStatus(Enum):
    """Status of a test point measurement"""
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "Skipped"


@dataclass
class TestPoint:
    """Individual test measurement result"""
    name: str
    measured: float
    unit: str
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    status: TestStatus = TestStatus.PASS
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuitePlugin:
    """Definition of a test suite that can be loaded by Tek PTA."""
    name: str
    description: str
    test_type: str
    engine_class: type
    default_config: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# MEASUREMENT DEFINITIONS - Specific to this eye diagram test
# =============================================================================
# This is where we define WHICH measurements this particular test uses.
# Each entry maps a measurement key to its SCPI configuration.

MEASUREMENTS = {
    "eye_height": {
        "scpi_type": "HEIGHT",      # SCPI measurement type (NOT "EYEHEIGHT"!)
        "name": "Eye Height",        # Display name
        "unit": "mV",               # Display unit
        "scale": 1000,              # Scale factor: V → mV
        "enabled": True,            # Enable/disable this measurement
    },
    "eye_width": {
        "scpi_type": "WIDTH",       # SCPI measurement type (NOT "EYEWIDTH"!)
        "name": "Eye Width", 
        "unit": "ps",
        "scale": 1e12,              # Scale factor: s → ps
        "enabled": True,
    },
    "pattern_length": {
        "scpi_type": "PATTERNLENGTH",
        "name": "Pattern Length",
        "unit": "bits",
        "scale": 1,                 # No scaling needed
        "enabled": True,
    },
    "data_rate": {
        "scpi_type": "DATARATE",
        "name": "Data Rate",
        "unit": "Gbps",
        "scale": 1e-9,              # Scale factor: bps → Gbps
        "enabled": True,
    },
    "dj": {
        "scpi_type": "DJ",          # Deterministic Jitter
        "name": "DJ (Det. Jitter)",
        "unit": "ps",
        "scale": 1e12,              # Scale factor: s → ps
        "enabled": True,
    },
}


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    # Source configuration
    "source_mode": "CHANNEL",       # "REFERENCE" or "CHANNEL"
    "channel": 1,                   # Channel number for live acquisition
    "ref_source": "REF1",           # Reference waveform (for REFERENCE mode)
    
    # Data rate configuration
    "data_rate_gbps": 1.62,         # Expected data rate in Gbps (DisplayPort RBR)
    
    # Acquisition settings
    "num_acquisitions": 1,          # 1 = single long acquisition (recommended)
    "horizontal_scale_us": 10,      # Horizontal scale in µs/div
    
    # Signal parameters
    "expected_vpp_mv": 650,         # Expected peak-to-peak voltage in mV
    "expected_offset_mv": 350,      # Expected DC offset in mV
    
    # Measurement limits (set to None to skip limit checking)
    "eye_height_min_mv": 200,       # Minimum eye height in mV
    "eye_height_max_mv": None,      # Maximum eye height in mV
    "eye_width_min_ps": 100,        # Minimum eye width in ps
    "eye_width_max_ps": None,       # Maximum eye width in ps
    "pattern_length_expected": None, # Expected pattern length (e.g., 127 for PRBS7)
    "data_rate_tolerance_pct": 1.0, # Data rate tolerance in percent
    "dj_max_ps": None,              # Maximum deterministic jitter in ps
    
    # Which measurements to enable (keys from MEASUREMENTS dict)
    "measurements_enabled": ["eye_height", "eye_width", "pattern_length", "data_rate", "dj"],
    
    # Output configuration
    "output_dir": "./eye_diagram_results",
    "save_screenshots": True,
    
    # Connection
    "scope_visa_address": "TCPIP::192.168.1.100::INSTR",
    "timeout_ms": 60000,
}


# =============================================================================
# EYE DIAGRAM TEST ENGINE
# =============================================================================

class EyeDiagramTestEngine:
    """
    Eye Diagram measurement engine for MSO4/5/6 series oscilloscopes.
    
    This engine sets up and runs the measurements defined in MEASUREMENTS dict.
    Measurements can be enabled/disabled via the measurements_enabled config.
    """
    
    def __init__(self, scope=None, config: dict = None):
        """
        Initialize the test engine.
        
        Args:
            scope: PyVISA resource for oscilloscope
            config: Configuration dictionary (uses DEFAULT_CONFIG if not provided)
        """
        self.scope = scope
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.rm = None
        self.results: List[TestPoint] = []
        self.screenshots: List[str] = []
        self._owns_connection = False
        self.measurement_data: Dict[str, Dict] = {}
        self.meas_map: Dict[str, int] = {}  # Maps measurement key to MEAS number
        
    def connect(self) -> bool:
        """Connect to the oscilloscope if not already connected."""
        if self.scope is not None:
            return True
            
        try:
            import pyvisa
            self.rm = pyvisa.ResourceManager()
            self.scope = self.rm.open_resource(self.config.get("scope_visa_address"))
            self.scope.timeout = self.config.get("timeout_ms", 60000)
            self._owns_connection = True
            
            idn = self.scope.query("*IDN?").strip()
            print(f"Connected to: {idn}")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to connect to scope: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the oscilloscope if we own the connection."""
        if self._owns_connection and self.scope:
            try:
                self.scope.close()
            except:
                pass
            self.scope = None
            
        if self.rm:
            try:
                self.rm.close()
            except:
                pass
            self.rm = None
            
    def _write(self, cmd: str):
        """Write a command to the scope."""
        self.scope.write(cmd)
        
    def _query(self, cmd: str) -> str:
        """Query the scope and return response."""
        return self.scope.query(cmd).strip()
        
    def _opc(self):
        """Wait for operation complete."""
        self._query("*OPC?")
        
    def _get_source(self) -> str:
        """Get the measurement source based on config."""
        if self.config["source_mode"] == "REFERENCE":
            return self.config["ref_source"]
        else:
            return f"CH{self.config['channel']}"
    
    def _setup_measurements(self, source: str):
        """
        Configure all enabled measurements on the scope.
        
        Sets up measurements based on the MEASUREMENTS dict and
        the measurements_enabled config option.
        """
        enabled = self.config.get("measurements_enabled", list(MEASUREMENTS.keys()))
        print(f"Setting up measurements: {', '.join(enabled)}")
        
        # Delete existing measurements
        self._write("MEASUrement:DELETEALL")
        self._opc()
        
        # Configure global clock recovery
        data_rate_hz = self.config["data_rate_gbps"] * 1e9
        self._write("MEASUrement:CLOCKRecovery:MODel STANDARD")
        self._write("MEASUrement:CLOCKRecovery:NOMINALOFFset:SELECTIONtype MANUAL")
        self._write(f"MEASUrement:CLOCKRecovery:NOMINALOFFset {data_rate_hz}")
        
        # Add each enabled measurement
        meas_num = 1
        self.meas_map = {}
        
        for meas_key, meas_def in MEASUREMENTS.items():
            if meas_key not in enabled or not meas_def.get("enabled", True):
                continue
                
            meas_name = f"MEAS{meas_num}"
            self._write(f'MEASUrement:ADDNew "{meas_name}"')
            self._write(f"MEASUrement:{meas_name}:TYPe {meas_def['scpi_type']}")
            self._write(f"MEASUrement:{meas_name}:SOUrce {source}")
            self._write(f"MEASUrement:{meas_name}:CLOCKRecovery:GLOBal 1")
            self._write(f"MEASUrement:{meas_name}:DISPlaystat:ENABle ON")
            self._write(f"MEASUrement:{meas_name}:STATE ON")
            
            self.meas_map[meas_key] = meas_num
            print(f"  {meas_name}: {meas_def['name']} ({meas_def['scpi_type']})")
            meas_num += 1
        
        # Enable statistics
        self._write("MEASUrement:STATistics:STATE ON")
        
        # If multi-acquisition mode, set population limiting
        num_acq = self.config.get("num_acquisitions", 1)
        if num_acq > 1:
            print(f"Configuring population limit to {num_acq}")
            for mnum in self.meas_map.values():
                self._write(f"MEASUrement:MEAS{mnum}:POPUlation:LIMIT:STATE ON")
                self._write(f"MEASUrement:MEAS{mnum}:POPUlation:LIMIT:VALue {num_acq}")
        
        self._opc()
    
    def _setup_horizontal(self):
        """Configure horizontal timebase for eye diagram."""
        scale_us = self.config.get("horizontal_scale_us", 10)
        scale_s = scale_us * 1e-6
        
        self._write(f"HORizontal:SCAle {scale_s}")
        self._write("HORizontal:SAMPLERate:ANALYZemode:MAXimum ON")
        self._write("HORizontal:RECOrdlength 10000000")
        
        # Calculate UIs captured
        data_rate_hz = self.config["data_rate_gbps"] * 1e9
        ui_seconds = 1.0 / data_rate_hz
        num_uis = (scale_s * 10) / ui_seconds
        print(f"Horizontal: {scale_us} µs/div (~{num_uis:.0f} UIs captured)")
    
    def _setup_eye_diagram_plot(self, source: str):
        """Configure eye diagram plot view."""
        print("Setting up eye diagram plot...")
        
        self._write('PLOT:ADDNew "PLOT1"')
        self._write("PLOT:PLOT1:TYPe EYEDIAGRAM")
        self._write(f"PLOT:PLOT1:SOUrce {source}")
        self._write("PLOT:PLOT1:CLOCKRecovery:GLOBal ON")
        self._write("PLOT:PLOT1:BITType ALLBits")
        self._write("PLOT:PLOT1:STATE ON")
        self._opc()
    
    def _run_acquisition(self, source: str):
        """Run acquisition (only for live channels, not reference waveforms)."""
        if self.config["source_mode"] == "REFERENCE":
            print("REFERENCE MODE: Using pre-captured waveform (no acquisition)")
            self._write(f"DISplay:GLObal:{source}:STATE ON")
            time.sleep(0.5)
            return
        
        num_acq = self.config.get("num_acquisitions", 1)
        print(f"Running {num_acq} acquisition(s)...")
        
        if num_acq == 1:
            self._write("ACQuire:STOPAfter SEQuence")
            self._write("ACQuire:STATE RUN")
            
            timeout = 30
            start = time.time()
            while time.time() - start < timeout:
                try:
                    state = self._query("ACQuire:STATE?")
                    if state == "0":
                        break
                except:
                    pass
                time.sleep(0.2)
        else:
            self._write("ACQuire:STOPAfter RUNSTop")
            self._write("ACQuire:STATE RUN")
            
            start = time.time()
            timeout = 300
            while time.time() - start < timeout:
                try:
                    acq_count = int(self._query("ACQuire:NUMACq?"))
                    if acq_count >= num_acq:
                        break
                    if acq_count % 20 == 0 and acq_count > 0:
                        print(f"  Progress: {acq_count}/{num_acq}")
                except:
                    pass
                time.sleep(0.2)
            
            self._write("ACQuire:STATE STOP")
        
        print("Acquisition complete")
    
    def _query_measurements(self):
        """Query all measurement results from scope."""
        print("Collecting measurement results...")
        
        for meas_key, meas_num in self.meas_map.items():
            meas_def = MEASUREMENTS[meas_key]
            
            try:
                mean = self._query(f"MEASUrement:MEAS{meas_num}:RESUlts:ALLAcqs:MEAN?")
                minimum = self._query(f"MEASUrement:MEAS{meas_num}:RESUlts:ALLAcqs:MINimum?")
                maximum = self._query(f"MEASUrement:MEAS{meas_num}:RESUlts:ALLAcqs:MAXimum?")
                stddev = self._query(f"MEASUrement:MEAS{meas_num}:RESUlts:ALLAcqs:STDDev?")
                
                if mean:
                    mean_val = float(mean)
                    if abs(mean_val) > 1e30 or math.isnan(mean_val) or math.isinf(mean_val):
                        self.measurement_data[meas_key] = None
                        print(f"  {meas_def['name']}: Invalid")
                    else:
                        self.measurement_data[meas_key] = {
                            'mean': mean_val,
                            'min': float(minimum) if minimum else mean_val,
                            'max': float(maximum) if maximum else mean_val,
                            'std_dev': float(stddev) if stddev else 0,
                        }
                        display_val = mean_val * meas_def['scale']
                        print(f"  {meas_def['name']}: {display_val:.3f} {meas_def['unit']}")
                else:
                    self.measurement_data[meas_key] = None
                    
            except Exception as e:
                print(f"  {meas_def['name']}: Error - {e}")
                self.measurement_data[meas_key] = None
    
    def _evaluate_results(self):
        """Evaluate measurement results against limits and create TestPoints."""
        self.results = []
        config = self.config
        
        # Eye Height
        if 'eye_height' in self.measurement_data and self.measurement_data['eye_height']:
            data = self.measurement_data['eye_height']
            measured_mv = data['mean'] * 1000
            lower = config.get('eye_height_min_mv')
            upper = config.get('eye_height_max_mv')
            
            status = self._check_limits(measured_mv, lower, upper)
            self.results.append(TestPoint(
                name="Eye Height",
                measured=measured_mv,
                unit="mV",
                lower_limit=lower,
                upper_limit=upper,
                status=status,
                extra_data={'raw': data}
            ))
        
        # Eye Width
        if 'eye_width' in self.measurement_data and self.measurement_data['eye_width']:
            data = self.measurement_data['eye_width']
            measured_ps = data['mean'] * 1e12
            lower = config.get('eye_width_min_ps')
            upper = config.get('eye_width_max_ps')
            
            data_rate_hz = config['data_rate_gbps'] * 1e9
            ui_seconds = 1.0 / data_rate_hz
            ui_pct = (data['mean'] / ui_seconds) * 100
            
            status = self._check_limits(measured_ps, lower, upper)
            self.results.append(TestPoint(
                name="Eye Width",
                measured=measured_ps,
                unit=f"ps ({ui_pct:.1f}%UI)",
                lower_limit=lower,
                upper_limit=upper,
                status=status,
                extra_data={'raw': data, 'ui_pct': ui_pct}
            ))
        
        # Pattern Length
        if 'pattern_length' in self.measurement_data and self.measurement_data['pattern_length']:
            data = self.measurement_data['pattern_length']
            measured = int(round(data['mean']))
            expected = config.get('pattern_length_expected')
            
            if expected is not None:
                status = TestStatus.PASS if measured == expected else TestStatus.FAIL
                lower = upper = expected
            else:
                status = TestStatus.PASS
                lower = upper = None
            
            self.results.append(TestPoint(
                name="Pattern Length",
                measured=measured,
                unit="bits",
                lower_limit=lower,
                upper_limit=upper,
                status=status,
                extra_data={'raw': data}
            ))
        
        # Data Rate
        if 'data_rate' in self.measurement_data and self.measurement_data['data_rate']:
            data = self.measurement_data['data_rate']
            measured_gbps = data['mean'] * 1e-9
            expected = config['data_rate_gbps']
            tolerance = config.get('data_rate_tolerance_pct', 1.0) / 100.0
            lower = expected * (1 - tolerance)
            upper = expected * (1 + tolerance)
            
            status = self._check_limits(measured_gbps, lower, upper)
            self.results.append(TestPoint(
                name="Data Rate",
                measured=measured_gbps,
                unit="Gbps",
                lower_limit=lower,
                upper_limit=upper,
                status=status,
                extra_data={'raw': data}
            ))
        
        # Deterministic Jitter (DJ)
        if 'dj' in self.measurement_data and self.measurement_data['dj']:
            data = self.measurement_data['dj']
            measured_ps = data['mean'] * 1e12
            upper = config.get('dj_max_ps')
            
            status = self._check_limits(measured_ps, None, upper)
            self.results.append(TestPoint(
                name="DJ (Det. Jitter)",
                measured=measured_ps,
                unit="ps",
                lower_limit=None,
                upper_limit=upper,
                status=status,
                extra_data={'raw': data}
            ))
    
    def _check_limits(self, value: float, lower: Optional[float], upper: Optional[float]) -> TestStatus:
        """Check if value is within limits."""
        if lower is not None and value < lower:
            return TestStatus.FAIL
        if upper is not None and value > upper:
            return TestStatus.FAIL
        return TestStatus.PASS
    
    def _capture_screenshot(self, prefix: str) -> Optional[str]:
        """Capture screenshot from scope."""
        if not self.config.get("save_screenshots", True):
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            
            scope_path = f"C:/Temp/{filename}"
            self._write(f'SAVe:IMAGe "{scope_path}"')
            self._opc()
            
            self._write(f'FILESystem:READFile "{scope_path}"')
            data = self.scope.read_raw()
            
            output_dir = self.config.get("output_dir", ".")
            os.makedirs(output_dir, exist_ok=True)
            local_path = os.path.join(output_dir, filename)
            
            with open(local_path, 'wb') as f:
                f.write(data)
            
            self.screenshots.append(local_path)
            print(f"Screenshot saved: {local_path}")
            return local_path
            
        except Exception as e:
            print(f"Screenshot capture failed: {e}")
            return None
    
    def run(self) -> List[TestPoint]:
        """Run the complete eye diagram test sequence."""
        print("\n" + "="*60)
        print("EYE DIAGRAM TEST SUITE")
        print("="*60)
        
        try:
            if not self.connect():
                return [TestPoint(name="Connection", measured=0, unit="", status=TestStatus.ERROR)]
            
            source = self._get_source()
            print(f"\nSource: {source}")
            print(f"Data Rate: {self.config['data_rate_gbps']} Gbps")
            print(f"Mode: {self.config['source_mode']}")
            print(f"Measurements: {', '.join(self.config.get('measurements_enabled', []))}")
            
            # Setup
            self._write("*CLS")
            self._write("HEADer OFF")
            
            if self.config["source_mode"] == "CHANNEL":
                self._setup_horizontal()
            
            self._setup_eye_diagram_plot(source)
            self._setup_measurements(source)
            
            # Run acquisition
            self._run_acquisition(source)
            
            # Query results
            self._query_measurements()
            
            # Evaluate against limits
            self._evaluate_results()
            
            # Capture screenshot
            self._capture_screenshot("eye_diagram")
            
            # Print summary
            print("\n" + "-"*40)
            print("RESULTS SUMMARY")
            print("-"*40)
            
            for r in self.results:
                limit_str = ""
                if r.lower_limit is not None or r.upper_limit is not None:
                    low = f"{r.lower_limit:.3f}" if r.lower_limit is not None else "---"
                    high = f"{r.upper_limit:.3f}" if r.upper_limit is not None else "---"
                    limit_str = f" [{low} - {high}]"
                print(f"  {r.name}: {r.measured:.3f} {r.unit}{limit_str} - {r.status.value}")
            
            pass_count = sum(1 for r in self.results if r.status == TestStatus.PASS)
            fail_count = sum(1 for r in self.results if r.status == TestStatus.FAIL)
            error_count = sum(1 for r in self.results if r.status == TestStatus.ERROR)
            
            print(f"\n  PASS: {pass_count}, FAIL: {fail_count}, ERROR: {error_count}")
            overall = "PASS" if fail_count == 0 and error_count == 0 else "FAIL"
            print(f"  OVERALL: {overall}")
            print("="*60 + "\n")
            
            return self.results
            
        except Exception as e:
            print(f"\nERROR: Test failed: {e}")
            import traceback
            traceback.print_exc()
            return [TestPoint(name="Test Execution", measured=0, unit="", status=TestStatus.ERROR)]
            
        finally:
            self.disconnect()
    
    def get_results_dict(self) -> Dict[str, Any]:
        """Get test results as a dictionary for reporting."""
        return {
            "test_name": "Eye Diagram Analysis",
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
            "measurements_enabled": self.config.get("measurements_enabled", []),
            "results": [
                {
                    "name": r.name,
                    "measured": r.measured,
                    "unit": r.unit,
                    "lower_limit": r.lower_limit,
                    "upper_limit": r.upper_limit,
                    "status": r.status.value,
                    "extra_data": r.extra_data
                }
                for r in self.results
            ],
            "measurement_data": self.measurement_data,
            "screenshots": self.screenshots,
        }


# =============================================================================
# PLUGIN REGISTRATION - Required by Tek PTA
# =============================================================================

def register_suites():
    """
    Register test suites with Tek PTA.
    
    This function is called by Tek PTA when loading plugin files.
    Returns a list of TestSuitePlugin objects.
    """
    return [
        TestSuitePlugin(
            name="Eye Diagram Analysis",
            description=(
                "Automated eye diagram measurements with pass/fail limits.\n\n"
                "Measurements:\n"
                "• Eye Height (mV) - vertical opening\n"
                "• Eye Width (ps, %UI) - horizontal opening\n"
                "• Pattern Length (bits) - e.g., 127 for PRBS7\n"
                "• Data Rate (Gbps) - measured vs expected\n"
                "• DJ - Deterministic Jitter (ps)\n\n"
                "Single long acquisition captures thousands of UIs.\n"
                "Multi-acquisition mode uses population limiting for statistics.\n\n"
                "Requirements: MSO4/5/6 series, DJA license for DJ measurement."
            ),
            test_type="eye_diagram",
            engine_class=EyeDiagramTestEngine,
            default_config=DEFAULT_CONFIG
        )
    ]


# =============================================================================
# STANDALONE EXECUTION
# =============================================================================

def main():
    """Run the eye diagram test as a standalone script."""
    
    # Configuration for standalone testing
    config = {
        # Source
        "source_mode": "CHANNEL",
        "channel": 1,
        
        # Data rate
        "data_rate_gbps": 1.62,  # DisplayPort RBR
        
        # Acquisition
        "num_acquisitions": 1,
        "horizontal_scale_us": 10,
        
        # Limits
        "eye_height_min_mv": 200,
        "eye_width_min_ps": 100,
        "pattern_length_expected": 127,  # PRBS7
        "data_rate_tolerance_pct": 1.0,
        "dj_max_ps": 50,
        
        # Which measurements to run
        "measurements_enabled": ["eye_height", "eye_width", "pattern_length", "data_rate", "dj"],
        
        # Output
        "output_dir": "./eye_diagram_results",
        "save_screenshots": True,
        
        # Connection - UPDATE THIS
        "scope_visa_address": "TCPIP::192.168.1.100::INSTR",
    }
    
    engine = EyeDiagramTestEngine(config=config)
    results = engine.run()
    
    return 0 if all(r.status == TestStatus.PASS for r in results) else 1


if __name__ == "__main__":
    exit(main())
