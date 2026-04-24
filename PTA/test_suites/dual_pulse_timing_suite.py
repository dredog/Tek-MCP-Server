#!/usr/bin/env python3
"""
Dual-Channel Pulse Timing Test Suite for Tek PTA
=================================================

Measures timing and pulse characteristics between two input waveforms.
Designed for AWG → Scope testing but supports REF waveforms for development.

Signal Configuration:
- Source 1 (REF1 or CH1): AWG CH1+ → Scope CH1
- Source 2 (REF2 or CH3): AWG CH2+ → Scope CH3

Signal Parameters:
- Amplitude: 0V to 125 mV (single-ended)
- Frequency: ~104.2 kHz
- Duty Cycle: 10%

Measurements:
1. Delay (rising edge REF1 to REF2): 2.00 µs ± 0.01 µs
2. Amplitude (REF1): 125 mV ± 10 mV
3. Positive Duty Cycle (REF1): 10% ± 0.2%
4. Frequency (REF1): 104.2 kHz ± 1 kHz
5. Rise Time (REF1): 200 ps ± 50 ps

Author: Andre Asbury
Date: 2026-02-04
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


# =============================================================================
# PLUGIN API DEFINITIONS (copy these EXACTLY for portability)
# =============================================================================

class TestStatus(Enum):
    """Status of a test point - MUST match exactly!"""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "Skipped"


@dataclass
class TestPoint:
    """Represents a single test measurement point - field order matters!"""
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
    """Definition of a test suite plugin - engine_class MUST be last!"""
    name: str
    description: str
    test_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Optional[type] = None  # MUST be last field!


class TestEngineBase:
    """Base class for custom test engines"""
    
    def __init__(self, instrument_manager):
        self.inst = instrument_manager
        self.test_points: List[TestPoint] = []
        self.running = False
        self.output_dir = None
        self.reference_config = None
        
        # Callbacks
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


# =============================================================================
# TEST SPECIFICATIONS
# =============================================================================

# Measurement specifications: (nominal, lower_limit, upper_limit, unit)
MEASUREMENT_SPECS = {
    'delay': {
        'name': 'Rising Edge Delay (REF1→REF2)',
        'nominal': 2.0e-6,      # 2 µs
        'lower': 1.99e-6,       # 2 µs - 0.01 µs
        'upper': 2.01e-6,       # 2 µs + 0.01 µs
        'unit': 's',
        'display_mult': 1e6,    # Display as µs
        'display_unit': 'µs',
        'meas_type': 'DELAY',
        'source1': 'REF1',
        'source2': 'REF2',
    },
    'amplitude': {
        'name': 'Amplitude (REF1)',
        'nominal': 125e-3,      # 125 mV
        'lower': 115e-3,        # 125 mV - 10 mV
        'upper': 135e-3,        # 125 mV + 10 mV
        'unit': 'V',
        'display_mult': 1e3,    # Display as mV
        'display_unit': 'mV',
        'meas_type': 'AMPLITUDE',
        'source1': 'REF1',
        'source2': None,
    },
    'duty_cycle': {
        'name': 'Positive Duty Cycle (REF1)',
        'nominal': 10.0,        # 10%
        'lower': 9.8,           # 10% - 0.2%
        'upper': 10.2,          # 10% + 0.2%
        'unit': '%',
        'display_mult': 1,      # Already in %
        'display_unit': '%',
        'meas_type': 'PDUTY',
        'source1': 'REF1',
        'source2': None,
    },
    'frequency': {
        'name': 'Frequency (REF1)',
        'nominal': 104.2e3,     # 104.2 kHz
        'lower': 103.2e3,       # 104.2 kHz - 1 kHz
        'upper': 105.2e3,       # 104.2 kHz + 1 kHz
        'unit': 'Hz',
        'display_mult': 1e-3,   # Display as kHz
        'display_unit': 'kHz',
        'meas_type': 'FREQUENCY',
        'source1': 'REF1',
        'source2': None,
    },
    'rise_time': {
        'name': 'Rise Time (REF1)',
        'nominal': 200e-12,     # 200 ps
        'lower': 150e-12,       # 200 ps - 50 ps
        'upper': 250e-12,       # 200 ps + 50 ps
        'unit': 's',
        'display_mult': 1e12,   # Display as ps
        'display_unit': 'ps',
        'meas_type': 'RISETIME',
        'source1': 'REF1',
        'source2': None,
    },
}


# =============================================================================
# DUAL PULSE TIMING ENGINE
# =============================================================================

class DualPulseTimingEngine(TestEngineBase):
    """
    Test engine for dual-channel pulse timing verification.
    
    Key Features:
    - Supports reference waveforms (REF1, REF2) - NO acquisition needed
    - Supports live channels (CH1, CH3) with acquisition
    - Statistical measurements using scope's built-in statistics
    """
    
    def __init__(self, instrument_manager):
        super().__init__(instrument_manager)
        self.use_reference_waveforms = True  # Default to REF mode
        self.source1 = 'REF1'
        self.source2 = 'REF2'
    
    def generate_test_points(self, config: Dict[str, Any]) -> List[TestPoint]:
        """Generate test points from measurement specifications."""
        self.test_points = []
        
        # Update source configuration from config
        self.use_reference_waveforms = config.get('use_reference_waveforms', True)
        if self.use_reference_waveforms:
            self.source1 = config.get('ref_source1', 'REF1')
            self.source2 = config.get('ref_source2', 'REF2')
        else:
            self.source1 = config.get('live_source1', 'CH1')
            self.source2 = config.get('live_source2', 'CH3')
        
        # Update measurement specs with current sources
        for key, spec in MEASUREMENT_SPECS.items():
            if spec['source1'] in ['REF1', 'CH1']:
                spec['source1'] = self.source1
            if spec.get('source2') in ['REF2', 'CH3']:
                spec['source2'] = self.source2
        
        # Create test points from specs
        test_id = 1
        for key, spec in MEASUREMENT_SPECS.items():
            # Calculate tolerance percentage for display
            nominal = spec['nominal']
            lower = spec['lower']
            upper = spec['upper']
            tolerance_pct = ((upper - lower) / 2 / nominal) * 100 if nominal != 0 else 0
            
            tp = TestPoint(
                test_id=test_id,
                name=spec['name'].replace('REF1', self.source1).replace('REF2', self.source2),
                nominal_value=nominal * spec['display_mult'],
                unit=spec['display_unit'],
                tolerance_pct=tolerance_pct,
                has_limits=True,
                enabled=True,
                lower_limit=lower * spec['display_mult'],
                upper_limit=upper * spec['display_mult'],
                extra_data={
                    'spec_key': key,
                    'meas_type': spec['meas_type'],
                    'source1': spec['source1'],
                    'source2': spec.get('source2'),
                    'display_mult': spec['display_mult'],
                    'raw_nominal': nominal,
                    'raw_lower': lower,
                    'raw_upper': upper,
                }
            )
            self.test_points.append(tp)
            test_id += 1
        
        return self.test_points
    
    def setup_instruments(self, config: Dict[str, Any]) -> bool:
        """Configure scope for measurements."""
        try:
            scope = self.inst.scope
            
            self.log("Configuring oscilloscope for pulse timing measurements...")
            
            # Clear any existing measurements
            scope.write("MEASUrement:DELETEALL")
            time.sleep(0.2)
            
            # Signal parameters
            # Low: 0V, High: 125 mV, Frequency: ~104.2 kHz (period ~9.6 µs)
            # Want to capture two pulses per acquisition
            # Two pulses = ~19.2 µs, add margin → ~25 µs window
            
            if not self.use_reference_waveforms:
                # Only configure for live channels
                self.log("Configuring for LIVE channel acquisition...")
                
                # Configure horizontal scale
                # 25 µs / 10 divisions = 2.5 µs/div
                scope.write("HORizontal:SCAle 2.5E-6")
                
                # Configure vertical scale for CH1 (or source1)
                # 125 mV signal, want ~5 divisions → 25 mV/div
                ch1 = self.source1.replace('CH', '')
                scope.write(f"CH{ch1}:SCAle 25E-3")
                scope.write(f"CH{ch1}:OFFSet -62.5E-3")  # Center around 62.5 mV
                scope.write(f"CH{ch1}:TERmination 50")   # 50 ohm termination
                
                # Configure CH3 (or source2) similarly
                ch2 = self.source2.replace('CH', '')
                scope.write(f"CH{ch2}:SCAle 25E-3")
                scope.write(f"CH{ch2}:OFFSet -62.5E-3")
                scope.write(f"CH{ch2}:TERmination 50")
                
                # Configure trigger
                # Trigger on source1 at 50% level (62.5 mV)
                scope.write(f"TRIGger:A:EDGE:SOUrce {self.source1}")
                scope.write("TRIGger:A:EDGE:SLOpe RISE")
                scope.write("TRIGger:A:LEVel:CH1 62.5E-3")
                
                # Set acquisition mode
                scope.write("ACQuire:MODe SAMple")
                scope.write("ACQuire:STOPAfter SEQUENCE")
                
            else:
                # Reference waveforms are STATIC - no acquisition setup needed!
                self.log("Using REFERENCE waveforms (REF1, REF2) - no acquisition needed")
                self.log("Ensure reference waveforms are loaded before running test!")
            
            # Set up measurements
            self._setup_measurements()
            
            self.log("Instrument setup complete")
            return True
            
        except Exception as e:
            self.log(f"ERROR during setup: {e}")
            return False
    
    def _setup_measurements(self):
        """Configure scope measurements for all test points."""
        scope = self.inst.scope
        
        meas_num = 1
        for tp in self.test_points:
            spec = tp.extra_data
            meas_type = spec['meas_type']
            source1 = spec['source1']
            source2 = spec.get('source2')
            
            self.log(f"Setting up MEAS{meas_num}: {meas_type} on {source1}" + 
                    (f" to {source2}" if source2 else ""))
            
            # Add measurement
            scope.write(f"MEASUrement:ADDMEAS {meas_type}")
            time.sleep(0.1)
            
            # Configure measurement source(s)
            scope.write(f"MEASUrement:MEAS{meas_num}:SOUrce1 {source1}")
            
            if source2 and meas_type == 'DELAY':
                scope.write(f"MEASUrement:MEAS{meas_num}:SOUrce2 {source2}")
                # Configure delay edges (rising to rising)
                scope.write(f"MEASUrement:MEAS{meas_num}:DELay:EDGE1 RISE")
                scope.write(f"MEASUrement:MEAS{meas_num}:DELay:EDGE2 RISE")
            
            # Store measurement number for later retrieval
            tp.extra_data['meas_num'] = meas_num
            meas_num += 1
        
        time.sleep(0.3)  # Allow measurements to initialize
    
    def _trigger_acquisition(self):
        """Trigger single acquisition (only for live channels)."""
        if self.use_reference_waveforms:
            # Reference waveforms are already present - no trigger needed!
            self.log("Reference waveforms are static - skipping acquisition")
            return True
        
        scope = self.inst.scope
        
        try:
            # Clear any previous acquisition
            scope.write("ACQuire:STATE STOP")
            time.sleep(0.1)
            
            # Arm and trigger
            scope.write("ACQuire:STOPAfter SEQUENCE")
            scope.write("ACQuire:STATE RUN")
            
            # Wait for acquisition to complete
            timeout = 5.0
            start_time = time.time()
            while time.time() - start_time < timeout:
                state = scope.query("ACQuire:STATE?").strip()
                if state == '0':  # Stopped = acquisition complete
                    return True
                time.sleep(0.1)
            
            self.log("WARNING: Acquisition timeout")
            return False
            
        except Exception as e:
            self.log(f"ERROR during acquisition: {e}")
            return False
    
    def run_single_test(self, test_point: TestPoint, config: Dict[str, Any]) -> TestPoint:
        """Execute measurement for a single test point."""
        try:
            scope = self.inst.scope
            meas_num = test_point.extra_data.get('meas_num', 1)
            display_mult = test_point.extra_data.get('display_mult', 1)
            
            # Read measurement result
            # For reference waveforms, use CURRentacq since there's only one "acquisition"
            response = scope.query(f"MEASUrement:MEAS{meas_num}:RESUlts:CURRentacq:MEAN?")
            raw_value = float(response.strip())
            
            # Convert to display units
            test_point.measured_value = raw_value * display_mult
            
            # Calculate error percentage
            if test_point.nominal_value != 0:
                test_point.error_pct = ((test_point.measured_value - test_point.nominal_value) 
                                        / test_point.nominal_value) * 100
            
            # Determine pass/fail based on raw limits
            raw_lower = test_point.extra_data['raw_lower']
            raw_upper = test_point.extra_data['raw_upper']
            
            if raw_lower <= raw_value <= raw_upper:
                test_point.status = TestStatus.PASS
            else:
                test_point.status = TestStatus.FAIL
            
            # Log result
            status_str = "✓ PASS" if test_point.status == TestStatus.PASS else "✗ FAIL"
            self.log(f"  {test_point.name}: {test_point.measured_value:.4f} {test_point.unit} "
                    f"[{test_point.lower_limit:.4f} - {test_point.upper_limit:.4f}] {status_str}")
            
        except Exception as e:
            test_point.status = TestStatus.ERROR
            test_point.extra_data['error'] = str(e)
            self.log(f"  ERROR measuring {test_point.name}: {e}")
        
        return test_point
    
    def run(self, config: Dict[str, Any]):
        """Main test execution loop."""
        self.running = True
        
        # Generate test points if not already done
        if not self.test_points:
            self.generate_test_points(config)
        
        # Setup instruments
        if not self.setup_instruments(config):
            self.log("Setup failed - aborting test")
            if self.on_complete:
                self.on_complete(0, len(self.test_points))
            return
        
        # Trigger acquisition (only for live channels)
        self._trigger_acquisition()
        
        # Allow measurements to stabilize
        time.sleep(0.5)
        
        # Run all enabled tests
        pass_count = 0
        fail_count = 0
        total_enabled = sum(1 for tp in self.test_points if tp.enabled)
        
        self.log("\n" + "="*50)
        self.log("MEASUREMENT RESULTS")
        self.log("="*50)
        
        for i, tp in enumerate(self.test_points):
            if not self.running:
                self.log("Test stopped by user")
                break
            
            if not tp.enabled:
                tp.status = TestStatus.SKIPPED
                continue
            
            # Update progress
            tp.status = TestStatus.RUNNING
            if self.on_test_start:
                self.on_test_start(tp)
            
            progress_pct = ((i + 1) / total_enabled) * 100
            self.progress(progress_pct, f"Testing: {tp.name}")
            
            # Execute measurement
            tp = self.run_single_test(tp, config)
            
            # Track results
            if tp.status == TestStatus.PASS:
                pass_count += 1
            elif tp.status in [TestStatus.FAIL, TestStatus.ERROR]:
                fail_count += 1
            
            if self.on_test_complete:
                self.on_test_complete(tp)
        
        # Summary
        self.log("\n" + "="*50)
        self.log(f"TEST COMPLETE: {pass_count} PASS, {fail_count} FAIL")
        self.log("="*50)
        
        self.cleanup()
        self.progress(100, "Complete")
        
        if self.on_complete:
            self.on_complete(pass_count, fail_count)
    
    def cleanup(self):
        """Cleanup after test run."""
        try:
            if self.inst and self.inst.scope:
                # Optionally clear measurements
                # self.inst.scope.write("MEASUrement:DELETEALL")
                pass
        except Exception as e:
            self.log(f"Cleanup warning: {e}")
    
    def stop(self):
        """Signal the test to stop."""
        self.running = False
        self.log("Stop requested")


# =============================================================================
# PLUGIN REGISTRATION (REQUIRED!)
# =============================================================================

def register_suites():
    """
    Register test suites with Tek PTA.
    
    This function is REQUIRED for Tek PTA to discover and load the plugin!
    """
    return [
        TestSuitePlugin(
            name="Dual Pulse Timing Test",
            description="Measures timing and pulse characteristics between two channels.\n"
                       "Supports REF waveforms (development) and live channels (production).\n\n"
                       "Measurements:\n"
                       "• Delay (rising edge to rising edge)\n"
                       "• Amplitude\n"
                       "• Positive Duty Cycle\n"
                       "• Frequency\n"
                       "• Rise Time",
            test_type="dual_pulse_timing",
            config={
                # Waveform source mode
                'use_reference_waveforms': True,  # True = REF mode, False = live channels
                
                # Reference waveform sources (when use_reference_waveforms = True)
                'ref_source1': 'REF1',
                'ref_source2': 'REF2',
                
                # Live channel sources (when use_reference_waveforms = False)
                'live_source1': 'CH1',
                'live_source2': 'CH3',
            },
            required_instruments=["Oscilloscope"],
            engine_class=DualPulseTimingEngine,  # MUST be last field!
        ),
    ]


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    print("Dual Pulse Timing Test Suite")
    print("="*40)
    
    # Verify plugin loads correctly
    suites = register_suites()
    print(f"\nRegistered {len(suites)} suite(s):")
    for suite in suites:
        print(f"  - {suite.name}")
        print(f"    Type: {suite.test_type}")
        print(f"    Required: {suite.required_instruments}")
    
    # Test engine in simulation mode
    print("\nSimulating test point generation...")
    engine = DualPulseTimingEngine(instrument_manager=None)
    engine.on_log = print
    
    config = {
        'use_reference_waveforms': True,
        'ref_source1': 'REF1',
        'ref_source2': 'REF2',
    }
    
    test_points = engine.generate_test_points(config)
    print(f"\nGenerated {len(test_points)} test points:")
    print("-"*80)
    print(f"{'ID':<4} {'Name':<35} {'Nominal':<15} {'Lower':<15} {'Upper':<15}")
    print("-"*80)
    for tp in test_points:
        print(f"{tp.test_id:<4} {tp.name:<35} {tp.nominal_value:<15.4f} "
              f"{tp.lower_limit:<15.4f} {tp.upper_limit:<15.4f} {tp.unit}")
    
    print("\n✓ Plugin validation complete!")
