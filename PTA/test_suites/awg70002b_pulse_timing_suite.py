#!/usr/bin/env python3
"""
AWG70002B Pulse Timing Test Suite for Tek PTA
==============================================

Verifies AWG70002B dual-channel pulse timing using oscilloscope measurements.

Test Configuration:
- CH1: 100 kHz pulse (1µs ON, 9µs OFF)
- CH2: Same pulse, delayed 2µs from CH1
- Amplitude: 250 mV differential (125 mV single-ended on scope)

IMPORTANT - Differential to Single-Ended:
AWG70002B outputs are differential. When using single-ended connection
(one output to scope), the amplitude seen on scope is HALF the AWG setting.

Measurement Philosophy:
Uses measurement statistics (average of individual measurements) rather than
waveform averaging. This provides:
- More accurate mean values
- Standard deviation for measurement repeatability
- Population count for verification

Vertical Setup Formulas:
- Single-ended Vpp = AWG_amplitude / 2
- Trigger level = signal midpoint = (V_low + V_high) / 2
- Scope offset = trigger level (centers signal)
- V_scale = Vpp_se / 6 (fits signal in ~6 divisions)

Horizontal Scale for Edge Measurements:
- H_scale ≈ 2 × nominal_rise_time, rounded UP to 1-2-5 sequence
- Example: 200ps rise → 500ps/div, 1ns rise → 2ns/div

Measurements:
- Delay CH1↑ to CH3↑ (rise-to-rise): 2.0 µs ±10 ns
- Delay CH1↓ to CH3↑ (fall-to-rise): 1.0 µs ±10 ns  
- Rise time CH1: 160 ps ±10 ps
- Rise time CH3: 160 ps ±10 ps
- Fall time CH1: 160 ps ±10 ps
- Fall time CH3: 160 ps ±10 ps

Connections:
- AWG CH1 → Oscilloscope CH1 (single-ended)
- AWG CH2 → Oscilloscope CH3 (single-ended)
"""

import time
import math
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
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
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
    measured_value: float = 0.0
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
    engine_class: Optional[type] = None


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
# MEASUREMENT SPECIFICATIONS
# =============================================================================

@dataclass
class MeasurementSpec:
    """Specification for a single measurement
    
    Live mode: AWG CH1 → Scope CH1, AWG CH2 → Scope CH3
    Reference mode: Pre-recorded waveforms in REF1, REF2
    
    view: Which scope view this measurement belongs to.
      - "delay": Wide horizontal scale showing multiple cycles (2.5 µs/div).
            Trigger: CH1 rising edge at signal midpoint.
      - "edge": Zoomed-in view for rise/fall time. 
            H scale ≈ 2× nominal value, rounded to 1-2-5 sequence.
            Examples: 200ps rise → 500ps/div; 1ns rise → 2ns/div.
            Trigger: Signal midpoint on the measured channel.
            Rising edge for RISETIME, falling edge for FALLTIME.
    
    Note: AWG differential → single-ended = half amplitude for trigger/offset.
    """
    name: str
    meas_type: str      # DELAY, RISETIME, FALLTIME
    source1_live: str   # CH1, CH3 for live mode
    source2_live: str   # For DELAY: CH1, CH3; for others: None
    source1_ref: str    # REF1, REF2 for reference mode  
    source2_ref: str    # For DELAY: REF1, REF2; for others: None
    edge1: str          # RISE, FALL (for DELAY)
    edge2: str          # RISE, FALL (for DELAY)
    nominal: float      # Expected value in seconds
    tolerance: float    # Absolute tolerance in seconds
    unit: str           # Display unit
    view: str = "delay" # "delay" or "edge" - determines scope timebase/trigger


MEASUREMENTS = [
    # Delay measurements - wide view (2.5 µs/div, trigger CH1 rising)
    MeasurementSpec("Delay CH1↑→CH2↑", "DELAY", "CH1", "CH3", "REF1", "REF2", "RISE", "RISE", 2.0e-6, 10e-9, "µs", "delay"),
    MeasurementSpec("Delay CH1↓→CH2↑", "DELAY", "CH1", "CH3", "REF1", "REF2", "FALL", "RISE", 1.0e-6, 10e-9, "µs", "delay"),
    # Rise/fall time measurements - zoomed edge view (H scale ≈ 2× nominal, rounded to 1-2-5)
    # Nominal 165 ps with ±15 ps tolerance gives limits of 150-180 ps
    MeasurementSpec("Rise Time CH1", "RISETIME", "CH1", None, "REF1", None, "RISE", None, 165e-12, 15e-12, "s", "edge"),
    MeasurementSpec("Rise Time CH2", "RISETIME", "CH3", None, "REF2", None, "RISE", None, 165e-12, 15e-12, "s", "edge"),
    MeasurementSpec("Fall Time CH1", "FALLTIME", "CH1", None, "REF1", None, "FALL", None, 165e-12, 15e-12, "s", "edge"),
    MeasurementSpec("Fall Time CH2", "FALLTIME", "CH3", None, "REF2", None, "FALL", None, 165e-12, 15e-12, "s", "edge"),
]


# =============================================================================
# AWG70002B PULSE TIMING ENGINE
# =============================================================================

class AWG70002BPulseTimingEngine(TestEngineBase):
    """
    Test engine for AWG70002B dual-channel pulse timing verification.
    
    Supports two modes:
    - Live mode: Uses AWG to generate signals, measures on CH1/CH3
    - Reference mode: Uses pre-recorded waveforms in REF1/REF2, no AWG needed
    
    Subclasses TestEngineBase and implements required methods:
    - generate_test_points(config)
    - setup_instruments(config)
    - run_single_test(test_point, config)
    - cleanup()
    """
    
    def __init__(self, instrument_manager):
        super().__init__(instrument_manager)
        self.awg = None
        self.awg_owned = False  # Track if we opened the AWG ourselves
        self.config = {}
        self.ref_mode = False  # True when using reference waveforms
    
    def generate_test_points(self, config: Dict[str, Any]) -> List[TestPoint]:
        """Generate test points from measurement specifications."""
        self.test_points = []
        
        for i, spec in enumerate(MEASUREMENTS, start=1):
            lower, upper = spec.nominal - spec.tolerance, spec.nominal + spec.tolerance
            tp = TestPoint(
                test_id=i,
                name=spec.name,
                nominal_value=spec.nominal,
                unit=spec.unit,
                tolerance_pct=(spec.tolerance / spec.nominal * 100) if spec.nominal > 0 else 0,
                has_limits=True,
                lower_limit=lower,
                upper_limit=upper,
                enabled=True,
            )
            tp.extra_data['spec'] = spec
            self.test_points.append(tp)
        
        return self.test_points
    
    def setup_instruments(self, config: Dict[str, Any]) -> bool:
        """Configure instruments for the test.
        
        Reference mode (ref waveforms checkbox checked):
        - AWG is NOT needed at all
        - Do *RST first (which clears REF waveforms)
        - Reload REF waveforms from files
        - Configure REF1/REF2 display and scale only (no CH commands)
        - No termination/coupling/bandwidth (those are acquisition params)
        - Setup measurements on REF1/REF2
        
        Live mode:
        - Connect and configure AWG
        - Setup scope channels (CH1/CH3) with full acquisition params
        - Setup measurements on CH1/CH3
        """
        self.config = config
        
        # Check if we're in reference mode
        self.ref_mode = (self.reference_config is not None and 
                         self.reference_config.enabled)
        
        try:
            if self.ref_mode:
                # Reference mode - NO AWG needed
                self.log("=" * 50)
                self.log("REFERENCE MODE - Using pre-recorded waveforms")
                self.log("AWG not required")
                self.log("=" * 50)
                
                # Setup scope for reference waveforms
                if not self._setup_oscilloscope_ref_mode(config):
                    return False
                
                # Setup measurements on REF1/REF2 with statistics
                if not self._setup_measurements(config):
                    return False
                
                return True
            else:
                # Live mode - need AWG
                self.log("=" * 50)
                self.log("LIVE MODE - Using AWG")
                self.log("=" * 50)
                
                # Connect to AWG
                if not self._connect_awg(config):
                    return False
                
                # Setup AWG waveforms
                if not self._setup_awg(config):
                    return False
                
                # Setup oscilloscope channels/trigger (live mode)
                if not self._setup_oscilloscope(config):
                    return False
                
                # Configure measurements on CH1/CH3 with statistics
                if not self._setup_measurements(config):
                    return False
                
                return True
            
        except Exception as e:
            self.log(f"Setup error: {e}")
            return False
    
    def _setup_oscilloscope_ref_mode(self, config: Dict[str, Any]) -> bool:
        """Configure oscilloscope for reference waveform mode.
        
        - Do *RST (which clears REF waveforms)
        - Reload REF waveforms from files
        - Display and scale REF1/REF2 only
        - No CH commands, no termination/coupling/bandwidth
        """
        amplitude = config.get("amplitude_v", 0.25)
        
        self.log("Configuring oscilloscope for reference mode...")
        
        # Reset to known state (this clears REF waveforms!)
        self.inst.scope_write("*RST")
        self.inst.scope_opc(10)
        self.inst.scope_write("HEADer OFF")
        
        # Reload reference waveforms (they were cleared by *RST)
        if not self._reload_reference_waveforms():
            return False
        
        # Turn off all CH channels (we only want REF displayed)
        for ch in range(1, 5):
            self.inst.scope_write(f"DISplay:WAVEView1:CH{ch}:STATE OFF")
        
        # Enable REF1 and REF2 display
        self.inst.scope_write("DISplay:WAVEView1:REF1:STATE ON")
        self.inst.scope_write("DISplay:WAVEView1:REF2:STATE ON")
        
        # Calculate vertical scale
        raw_scale = amplitude / 8
        nice_scales = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
        v_scale = min((s for s in nice_scales if s >= raw_scale), default=0.1)
        v_offset = amplitude / 2
        
        # Configure REF1 and REF2 scale/offset only
        # No termination/coupling/bandwidth - those are acquisition parameters
        for ref in ["REF1", "REF2"]:
            self.inst.scope_write(f"{ref}:VERTical:SCAle {v_scale}")
            self.inst.scope_write(f"{ref}:VERTical:POSition 0")
        
        self.log(f"  REF1, REF2: {v_scale*1000:.0f}mV/div")
        
        return True
    
    def _reload_reference_waveforms(self) -> bool:
        """Reload reference waveforms after *RST cleared them."""
        if not self.reference_config:
            self.log("ERROR: No reference config available")
            return False
        
        self.log("Reloading reference waveforms (cleared by *RST)...")
        
        # Get the waveform files from reference_config.ref_files
        # ref_files is a dict like {"REF1": "path/to/file.wfm", "REF2": "..."}
        ref_files = self.reference_config.ref_files
        
        if not ref_files:
            self.log("ERROR: No reference waveform files specified")
            return False
        
        for ref_name, file_path in ref_files.items():
            if not file_path:
                continue
            self.log(f"  Loading {ref_name} from: {file_path}")
            try:
                self.inst.scope_write(f'RECAll:WAVEform "{file_path}",{ref_name}')
                self.inst.scope_opc(10)
                self.log(f"  ✓ {ref_name} loaded")
            except Exception as e:
                self.log(f"  ERROR loading {ref_name}: {e}")
                return False
        
        return True
    
    def _connect_awg(self, config: Dict[str, Any]) -> bool:
        """Connect to AWG - use InstrumentManager's AWG if available."""
        # Check if AWG already connected via InstrumentManager
        if self.inst.awg is not None:
            self.awg = self.inst.awg
            self.awg_owned = False
            self.log(f"Using connected AWG: {self.inst.awg_info.model if self.inst.awg_info else 'AWG'}")
            return True
        
        # Connect directly
        awg_address = config.get("awg_address", "TCPIP0::169.254.165.92::inst0::INSTR")
        self.log(f"Connecting to AWG at {awg_address}...")
        
        try:
            import pyvisa
            rm = pyvisa.ResourceManager()
            self.awg = rm.open_resource(awg_address)
            self.awg.timeout = 30000
            self.awg.write_termination = '\n'
            self.awg.read_termination = '\n'
            idn = self.awg.query("*IDN?").strip()
            self.log(f"  Connected: {idn}")
            self.awg_owned = True
            return True
        except Exception as e:
            self.log(f"ERROR: Could not connect to AWG: {e}")
            return False
    
    def _awg_write(self, cmd: str):
        """Write command to AWG with logging."""
        self.log(f"AWG << {cmd}")
        self.awg.write(cmd)
    
    def _awg_query(self, cmd: str) -> str:
        """Query AWG with logging."""
        self.log(f"AWG << {cmd}")
        response = self.awg.query(cmd).strip()
        self.log(f"AWG >> {response}")
        return response
    
    def _setup_awg(self, config: Dict[str, Any]) -> bool:
        """Configure AWG waveforms."""
        try:
            import numpy as np
        except ImportError:
            self.log("ERROR: numpy required for waveform generation")
            return False
        
        pulse_width = config.get("pulse_width_us", 1) * 1e-6
        period = config.get("period_us", 10) * 1e-6
        phase_offset = config.get("phase_offset_us", 2) * 1e-6
        amplitude = config.get("amplitude_v", 0.25)
        sample_rate = config.get("sample_rate", 250e6)
        
        self.log(f"AWG config: {pulse_width*1e6:.1f}µs pulse, {period*1e6:.1f}µs period, {phase_offset*1e6:.1f}µs offset")
        
        # Calculate waveform parameters
        samples_per_period = int(period * sample_rate)
        samples_on = int(pulse_width * sample_rate)
        phase_samples = int(phase_offset * sample_rate)
        
        # Ensure minimum granularity (AWG70000 requires multiples of specific values)
        samples_per_period = max(2400, (samples_per_period // 240) * 240)
        
        self.log(f"  Samples/period: {samples_per_period}, ON: {samples_on}, Phase offset: {phase_samples}")
        
        # Create waveforms as floating point (-1 to +1)
        wfm1 = np.zeros(samples_per_period, dtype=np.float32)
        wfm1[:samples_on] = 1.0
        
        wfm2 = np.zeros(samples_per_period, dtype=np.float32)
        start2 = phase_samples
        end2 = min(start2 + samples_on, samples_per_period)
        wfm2[start2:end2] = 1.0
        if end2 < start2 + samples_on:
            wfm2[:samples_on - (end2 - start2)] = 1.0
        
        # Stop outputs first
        self._awg_write("AWGControl:STOP")
        self._awg_write("OUTPut1:STATe OFF")
        self._awg_write("OUTPut2:STATe OFF")
        time.sleep(0.2)
        
        # Set sample rate
        self._awg_write(f"CLOCk:SRATe {sample_rate:.0f}")
        self.log(f"  Sample rate: {sample_rate/1e6:.1f} MS/s")
        
        # Upload waveforms
        self._upload_waveform("PulseCH1", wfm1)
        self._upload_waveform("PulseCH2", wfm2)
        
        # Assign to channels
        self._awg_write('SOURce1:CASSet:WAVeform "PulseCH1"')
        self._awg_write('SOURce2:CASSet:WAVeform "PulseCH2"')
        
        # Set amplitude and offset
        # Waveform data is 0 to 1.0, AWG amplitude is peak-to-peak
        # To get 0 to 250mV output: amplitude = 250mV, offset = 125mV (centers at 125mV)
        self._awg_write(f"SOURce1:VOLTage:LEVel:IMMediate:AMPLitude {amplitude}")
        self._awg_write(f"SOURce2:VOLTage:LEVel:IMMediate:AMPLitude {amplitude}")
        # Offset shifts the center point - set to amplitude/2 so signal goes from 0 to amplitude
        awg_offset = amplitude / 2
        self._awg_write(f"SOURce1:VOLTage:LEVel:IMMediate:OFFSet {awg_offset}")
        self._awg_write(f"SOURce2:VOLTage:LEVel:IMMediate:OFFSet {awg_offset}")
        
        self.log(f"  Amplitude: {amplitude*1000:.0f} mV")
        
        # Verify setup
        self._awg_query("*OPC?")
        
        return True
    
    def _upload_waveform(self, name: str, data):
        """Upload waveform data to AWG."""
        import numpy as np
        
        # Delete if exists
        try:
            self._awg_write(f'WLISt:WAVeform:DELete "{name}"')
        except:
            pass
        
        # Create new waveform
        length = len(data)
        self._awg_write(f'WLISt:WAVeform:NEW "{name}",{length},REAL')
        
        # Convert to bytes (IEEE 754 float32, little-endian)
        float_data = data.astype(np.float32)
        byte_data = float_data.tobytes()
        
        # Send with IEEE block header
        header = f'WLISt:WAVeform:DATA "{name}",0,{length},'
        length_bytes = len(byte_data)
        digits = len(str(length_bytes))
        block_header = f"#{digits}{length_bytes}".encode()
        
        self.log(f"AWG << WLISt:WAVeform:DATA \"{name}\" ({length_bytes} bytes)")
        self.awg.write_raw(header.encode() + block_header + byte_data + b'\n')
        self._awg_query("*OPC?")
        
        self.log(f"  Uploaded waveform '{name}' ({length} samples)")
    
    def _setup_oscilloscope(self, config: Dict[str, Any]) -> bool:
        """Configure oscilloscope channels and timebase for delay (wide) view.
        
        IMPORTANT - Differential to Single-Ended Conversion:
        AWG70k outputs are differential. When measuring single-ended (one output),
        the amplitude seen on scope is HALF the AWG's configured amplitude.
        
        Example: AWG amplitude_v=0.25 (250mV differential) → 125mV single-ended
        
        Vertical Setup Formulas:
        - Single-ended Vpp = AWG_amplitude / 2
        - Signal swings from V_low to V_high (typically 0 to Vpp_se)
        - Trigger level = (V_low + V_high) / 2 = signal midpoint
        - Scope offset = trigger level (centers signal on screen)
        - V_scale = Vpp_se / 6 (fits signal in ~6 divisions with margin)
        """
        awg_amplitude = config.get("amplitude_v", 0.25)  # AWG differential amplitude
        awg_offset = config.get("awg_offset_v", None)    # AWG offset (optional)
        
        # Calculate single-ended amplitude (half of differential)
        se_amplitude = awg_amplitude / 2
        
        # Determine signal voltage bounds
        # Default: signal swings from 0 to se_amplitude (AWG offset = amplitude/2)
        if awg_offset is not None:
            v_low = awg_offset - se_amplitude / 2
            v_high = awg_offset + se_amplitude / 2
        else:
            # Standard case: 0 to se_amplitude
            v_low = 0
            v_high = se_amplitude
        
        # Trigger and offset at signal midpoint
        v_midpoint = (v_low + v_high) / 2
        
        self.log("Configuring oscilloscope (delay view)...")
        self.log(f"  AWG differential: {awg_amplitude*1000:.0f}mV → Single-ended: {se_amplitude*1000:.0f}mV")
        self.log(f"  Signal range: {v_low*1000:.1f}mV to {v_high*1000:.1f}mV")
        
        # Reset to known state
        self.inst.scope_write("*RST")
        self.inst.scope_opc(10)
        self.inst.scope_write("HEADer OFF")
        
        # Turn off all channels, enable CH1 and CH3
        for ch in range(1, 5):
            self.inst.scope_write(f"DISplay:WAVEView1:CH{ch}:STATE OFF")
        self.inst.scope_write("DISplay:WAVEView1:CH1:STATE ON")
        self.inst.scope_write("DISplay:WAVEView1:CH3:STATE ON")
        
        # Calculate vertical scale: fit signal in ~6 divisions
        raw_scale = se_amplitude / 6
        nice_scales = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
        v_scale = min((s for s in nice_scales if s >= raw_scale), default=0.1)
        
        # Offset to center the signal
        v_offset = v_midpoint
        
        # Configure CH1 and CH3
        for ch in [1, 3]:
            self.inst.scope_write(f"CH{ch}:TERmination 50")
            self.inst.scope_write(f"CH{ch}:COUPling DC")
            self.inst.scope_write(f"CH{ch}:BANdwidth FULL")
            self.inst.scope_write(f"CH{ch}:SCAle {v_scale}")
            self.inst.scope_write(f"CH{ch}:OFFSet {v_offset}")
        
        self.log(f"  CH1, CH3: 50Ω, {v_scale*1000:.0f}mV/div, offset={v_offset*1000:.1f}mV")
        
        # Horizontal: 2.5µs/div to show ~2.5 periods (delay view)
        h_scale = 2.5e-6
        self.inst.scope_write(f"HORizontal:SCAle {h_scale}")
        self.inst.scope_write("HORizontal:POSition 10")
        self.log(f"  Horizontal: {h_scale*1e6:.1f} µs/div (delay view)")
        
        # Trigger on CH1 rising edge at signal midpoint
        trigger_level = v_midpoint
        self.inst.scope_write("TRIGger:A:TYPe EDGE")
        self.inst.scope_write("TRIGger:A:EDGE:SOUrce CH1")
        self.inst.scope_write("TRIGger:A:EDGE:SLOpe RISE")
        self.inst.scope_write(f"TRIGger:A:LEVel:CH1 {trigger_level}")
        self.inst.scope_write("TRIGger:A:MODe NORMal")
        self.log(f"  Trigger: CH1 rising @ {trigger_level*1000:.1f}mV")
        
        # Use SAMPLE mode - we'll use measurement statistics instead of waveform averaging
        # This gives us average of measurements, not measurement of averaged waveform
        self.inst.scope_write("ACQuire:MODe SAMple")
        self.log(f"  Acquisition: Sample mode (using measurement statistics)")
        
        return True
    
    def _nice_h_scale(self, target: float) -> float:
        """Round a horizontal scale to a nice oscilloscope value.
        
        Oscilloscopes use 1-2-5 sequence: 100ps, 200ps, 500ps, 1ns, 2ns, 5ns, etc.
        """
        nice = [1e-12, 2e-12, 5e-12,
                10e-12, 20e-12, 50e-12, 100e-12, 200e-12, 500e-12,
                1e-9, 2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9, 500e-9,
                1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6, 200e-6, 500e-6,
                1e-3, 2e-3, 5e-3, 10e-3]
        return min((s for s in nice if s >= target), default=target)
    
    def _configure_edge_view(self, spec: MeasurementSpec, config: Dict[str, Any]):
        """Configure scope for rise/fall time measurement (zoomed edge view).
        
        Horizontal Scale Formula (derived from requirements):
        - 200ps nominal → 500ps/div (2.5×)
        - 1ns nominal → 2ns/div (2×)
        - Formula: H_scale ≈ 2.5 × nominal_rise_time, rounded to 1-2-5 sequence
        
        Trigger: Signal midpoint on the measured channel, appropriate edge.
        For rise time: trigger on rising edge
        For fall time: trigger on falling edge
        
        Note: Uses single-ended amplitude (AWG differential / 2)
        """
        awg_amplitude = config.get("amplitude_v", 0.25)
        awg_offset = config.get("awg_offset_v", None)
        
        # Calculate single-ended signal bounds
        se_amplitude = awg_amplitude / 2
        if awg_offset is not None:
            v_low = awg_offset - se_amplitude / 2
            v_high = awg_offset + se_amplitude / 2
        else:
            v_low = 0
            v_high = se_amplitude
        v_midpoint = (v_low + v_high) / 2
        
        # Determine source channel for trigger
        if self.ref_mode:
            # In reference mode, we can't trigger on REF - use existing trigger
            self.log(f"  Edge view (ref mode): keeping existing trigger")
        else:
            source_ch = spec.source1_live  # e.g., "CH1" or "CH3"
            trigger_edge = "RISE" if spec.meas_type == "RISETIME" else "FALL"
            trigger_level = v_midpoint  # Signal midpoint
            
            self.inst.scope_write(f"TRIGger:A:EDGE:SOUrce {source_ch}")
            self.inst.scope_write(f"TRIGger:A:EDGE:SLOpe {trigger_edge}")
            self.inst.scope_write(f"TRIGger:A:LEVel:{source_ch} {trigger_level}")
            self.log(f"  Trigger: {source_ch} {trigger_edge.lower()} @ {trigger_level*1000:.1f}mV")
        
        # H scale ≈ 2× nominal rise/fall time, rounded UP to 1-2-5 sequence
        # Examples: 200ps × 2 = 400ps → 500ps/div; 1ns × 2 = 2ns → 2ns/div
        target_h_scale = spec.nominal * 2.0
        h_scale = self._nice_h_scale(target_h_scale)
        
        self.inst.scope_write(f"HORizontal:SCAle {h_scale}")
        self.inst.scope_write("HORizontal:POSition 50")  # Center the edge
        self.log(f"  Horizontal: {self._format_time(h_scale)}/div (edge view, ~2×{self._format_time(spec.nominal)})")
    
    def _configure_delay_view(self, config: Dict[str, Any]):
        """Restore scope to delay (wide) view after edge measurements."""
        awg_amplitude = config.get("amplitude_v", 0.25)
        awg_offset = config.get("awg_offset_v", None)
        
        # Calculate single-ended trigger level
        se_amplitude = awg_amplitude / 2
        if awg_offset is not None:
            v_midpoint = awg_offset
        else:
            v_midpoint = se_amplitude / 2
        
        h_scale = 2.5e-6
        self.inst.scope_write(f"HORizontal:SCAle {h_scale}")
        self.inst.scope_write("HORizontal:POSition 10")
        
        if not self.ref_mode:
            # Restore trigger to CH1 rising at signal midpoint
            self.inst.scope_write("TRIGger:A:EDGE:SOUrce CH1")
            self.inst.scope_write("TRIGger:A:EDGE:SLOpe RISE")
            self.inst.scope_write(f"TRIGger:A:LEVel:CH1 {v_midpoint}")
        
        self.log(f"  Horizontal: {h_scale*1e6:.1f} µs/div (delay view)")
    
    def _format_time(self, seconds: float) -> str:
        """Format time value with appropriate unit."""
        if seconds >= 1e-3:
            return f"{seconds*1e3:.1f}ms"
        elif seconds >= 1e-6:
            return f"{seconds*1e6:.1f}µs"
        elif seconds >= 1e-9:
            return f"{seconds*1e9:.1f}ns"
        else:
            return f"{seconds*1e12:.0f}ps"
    
    def _setup_measurements(self, config: Dict[str, Any]) -> bool:
        """Configure oscilloscope measurements for DELAY view with statistics.
        
        Uses measurement statistics (mean of individual measurements) instead of
        waveform averaging. This provides:
        - More accurate representation of measurement variation
        - Standard deviation calculation
        - Population limit to control sample count
        
        Key SCPI commands for statistics:
        - MEASUrement:MEAS<x>:DISPlaystat:ENABle ON  - Enable statistics display
        - MEASUrement:MEAS<x>:POPUlation:LIMIT:STATE ON - Enable population limit
        - MEASUrement:MEAS<x>:POPUlation:LIMIT:VALue <n> - Set limit (e.g., 50)
        - MEASUrement:MEAS<x>:RESUlts:ALLAcqs:MEAN? - Read mean of all acquisitions
        - MEASUrement:MEAS<x>:RESUlts:ALLAcqs:STDDev? - Read standard deviation
        
        Edge measurements (rise/fall time) are configured individually in Pass 2
        because each needs its own trigger and horizontal scale.
        
        Live mode: Uses CH1, CH3
        Reference mode: Uses REF1, REF2 directly
        """
        mode_str = "reference" if self.ref_mode else "live"
        num_samples = config.get("num_samples", 100)
        
        self.log(f"Setting up delay measurements ({mode_str} mode)...")
        self.log(f"  Statistics: {num_samples} samples per measurement")
        
        self.inst.scope_write("MEASUrement:DELETEALL")
        time.sleep(0.1)
        
        for i, spec in enumerate(MEASUREMENTS, start=1):
            # Only set up delay measurements here; edge measurements are per-acquisition
            if spec.view != "delay":
                continue
                
            meas_name = f"MEAS{i}"
            
            # Select sources based on mode
            if self.ref_mode:
                source1 = spec.source1_ref
                source2 = spec.source2_ref
            else:
                source1 = spec.source1_live
                source2 = spec.source2_live
            
            self.inst.scope_write(f'MEASUrement:ADDNew "{meas_name}"')
            self.inst.scope_write(f"MEASUrement:{meas_name}:TYPe {spec.meas_type}")
            
            if spec.meas_type == "DELAY":
                self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce1 {source1}")
                self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce2 {source2}")
                self.inst.scope_write(f"MEASUrement:{meas_name}:DELay:EDGE1 {spec.edge1}")
                self.inst.scope_write(f"MEASUrement:{meas_name}:DELay:EDGE2 {spec.edge2}")
            else:
                self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce {source1}")
            
            self.inst.scope_write(f"MEASUrement:{meas_name}:STATE ON")
            
            # Enable statistics with population limit
            self.inst.scope_write(f"MEASUrement:{meas_name}:DISPlaystat:ENABle ON")
            self.inst.scope_write(f"MEASUrement:{meas_name}:POPUlation:LIMIT:STATE ON")
            self.inst.scope_write(f"MEASUrement:{meas_name}:POPUlation:LIMIT:VALue {num_samples}")
            
            self.log(f"  {meas_name}: {spec.name} → {source1} (stats: {num_samples} samples)")
        
        return True
    
    def run_single_test(self, test_point: TestPoint, config: Dict[str, Any]) -> TestPoint:
        """
        Execute a single measurement reading.
        
        Reads the mean from accumulated statistics (ALLAcqs:MEAN) which gives the
        average of individual measurements across multiple acquisitions.
        Also captures standard deviation for extra data.
        
        Note: Statistics should already be populated before calling this.
        """
        spec = test_point.extra_data.get('spec')
        if not spec:
            test_point.status = TestStatus.ERROR
            return test_point
        
        meas_idx = test_point.test_id
        
        try:
            # Read mean from accumulated statistics
            result_str = self.inst.scope_query(
                f"MEASUrement:MEAS{meas_idx}:RESUlts:ALLAcqs:MEAN?"
            )
            measured = float(result_str)
            
            # Check for invalid measurement (9.91E+37 is Tek's "Not a Number")
            if math.isnan(measured) or math.isinf(measured) or measured > 1e30:
                test_point.status = TestStatus.ERROR
                test_point.extra_data['error'] = "No valid measurement (check signal/connections)"
                self.log(f"  {spec.name}: ERROR - No valid measurement")
                return test_point
            
            test_point.measured_value = measured
            
            # Also read standard deviation and population count
            try:
                stdev_str = self.inst.scope_query(
                    f"MEASUrement:MEAS{meas_idx}:RESUlts:ALLAcqs:STDDev?"
                )
                stdev = float(stdev_str)
                if not (math.isnan(stdev) or math.isinf(stdev) or stdev > 1e30):
                    test_point.extra_data['stdev'] = stdev
                    
                pop_str = self.inst.scope_query(
                    f"MEASUrement:MEAS{meas_idx}:RESUlts:ALLAcqs:POPUlation?"
                )
                population = int(float(pop_str))
                test_point.extra_data['population'] = population
            except:
                pass
            
            # Check pass/fail
            if test_point.lower_limit <= measured <= test_point.upper_limit:
                test_point.status = TestStatus.PASS
            else:
                test_point.status = TestStatus.FAIL
            
            # Calculate error percentage
            if test_point.nominal_value > 0:
                test_point.error_pct = ((measured - test_point.nominal_value) / 
                                        test_point.nominal_value * 100)
            
            # Format for logging with optional stdev
            measured_fmt = self._format_value(measured, spec.unit)
            nominal_fmt = self._format_value(test_point.nominal_value, spec.unit)
            stdev_info = ""
            if 'stdev' in test_point.extra_data:
                stdev_fmt = self._format_value(test_point.extra_data['stdev'], spec.unit)
                stdev_info = f" σ={stdev_fmt}"
            pop_info = f" n={test_point.extra_data.get('population', '?')}"
            
            self.log(f"  {spec.name}: {measured_fmt}{stdev_info}{pop_info} (nom: {nominal_fmt}) [{test_point.status.value}]")
            
        except Exception as e:
            test_point.status = TestStatus.ERROR
            test_point.extra_data['error'] = str(e)
            self.log(f"  {spec.name}: ERROR - {e}")
        
        return test_point
    
    def _format_value(self, value: float, unit: str) -> str:
        """Format value with appropriate scaling."""
        if unit == "µs":
            return f"{value*1e6:.3f} µs"
        elif unit == "ns":
            return f"{value*1e9:.3f} ns"
        elif unit == "ps":
            return f"{value*1e12:.1f} ps"
        else:
            return f"{value:.6g} {unit}"
    
    def run(self, config: Dict[str, Any]):
        """
        Run the pulse timing test with two scope views using measurement statistics.
        
        Philosophy: Average of measurements (not measurement of averaged waveform)
        - Uses ACQuire:MODe SAMple (not AVErage)
        - Enables measurement statistics with population limit
        - Reads ALLAcqs:MEAN for the average of individual measurements
        - Also captures standard deviation
        
        Pass 1 - Delay View (wide timebase):
          - H scale: 2.5 µs/div to show multiple cycles
          - Trigger: CH1 rising edge at signal midpoint
          - Measures: delay between channels
          - Acquires N samples for statistics
          
        Pass 2 - Edge View (zoomed per measurement):
          - H scale: 2.5 × nominal rise/fall time (200ps → 500ps/div)
          - Trigger: signal midpoint on measured channel, matching edge direction
          - Measures: rise time (trigger rising), fall time (trigger falling)
          - Re-acquires for each edge measurement with appropriate trigger
        
        Reference mode:
          - Waveforms already in REF1/REF2
          - No AWG, no acquisition needed
          - Just reconfigure horizontal scale and read measurements
        """
        self.running = True
        num_samples = config.get("num_samples", 100)
        
        # Setup instruments (handles ref_mode internally)
        if not self.setup_instruments(config):
            self.log("ERROR: Instrument setup failed")
            if self.on_complete:
                self.on_complete(0, len(self.test_points))
            return
        
        pass_count = 0
        fail_count = 0
        
        try:
            # Separate tests by view type
            delay_tests = [(i, tp) for i, tp in enumerate(self.test_points) 
                          if tp.extra_data.get('spec') and tp.extra_data['spec'].view == "delay"]
            edge_tests = [(i, tp) for i, tp in enumerate(self.test_points)
                         if tp.extra_data.get('spec') and tp.extra_data['spec'].view == "edge"]
            
            total = len(self.test_points)
            
            # ================================================================
            # PASS 1: DELAY VIEW - wide horizontal scale
            # ================================================================
            if delay_tests:
                self.log("=" * 50)
                self.log("PASS 1: Delay View (wide timebase)")
                self.log("=" * 50)
                
                if not self.ref_mode:
                    # Live mode - enable AWG and acquire statistics
                    self.log("Enabling AWG outputs...")
                    self._awg_write("OUTPut1:STATe ON")
                    self._awg_write("OUTPut2:STATe ON")
                    self._awg_write("AWGControl:RUN")
                    self._awg_query("*OPC?")
                    time.sleep(0.5)
                    
                    self.progress(10, "AWG running, collecting statistics (delay view)...")
                    
                    # Clear statistics and start continuous acquisition
                    self.log(f"Starting acquisition for {num_samples} samples (delay view)...")
                    self.inst.scope_write("CLEAR")  # Clear existing statistics
                    self.inst.scope_write("ACQuire:STOPAfter RUNStop")  # Continuous mode
                    self.inst.scope_write("ACQuire:STATE RUN")
                    
                    # Wait for statistics to accumulate
                    timeout = max(30, num_samples * 0.5)  # ~0.5s per sample typical
                    if not self._wait_statistics(num_samples, timeout):
                        self.log("ERROR: Statistics acquisition timeout (delay view)")
                        if self.on_complete:
                            self.on_complete(0, len(self.test_points))
                        return
                    
                    # Stop acquisition
                    self.inst.scope_write("ACQuire:STATE STOP")
                else:
                    self.log("Reference mode - reading delay measurements...")
                    time.sleep(0.3)
                
                # Capture delay view screenshot
                delay_screenshot_path = ""
                if self.output_dir:
                    delay_screenshot_path = self._capture_screenshot("delay_view")
                    if delay_screenshot_path and self.on_screenshot:
                        self.on_screenshot(delay_screenshot_path)
                
                # Read delay measurements
                self.progress(30, "Reading delay measurements...")
                for idx, tp in delay_tests:
                    if not self.running:
                        break
                    if not tp.enabled:
                        tp.status = TestStatus.SKIPPED
                        continue
                    
                    tp.status = TestStatus.RUNNING
                    if self.on_test_start:
                        self.on_test_start(tp)
                    
                    tp = self.run_single_test(tp, config)
                    
                    # Assign delay screenshot to this test point
                    if delay_screenshot_path and not tp.screenshot_path:
                        tp.screenshot_path = delay_screenshot_path
                    
                    if tp.status == TestStatus.PASS:
                        pass_count += 1
                    elif tp.status in (TestStatus.FAIL, TestStatus.ERROR):
                        fail_count += 1
                    
                    if self.on_test_complete:
                        self.on_test_complete(tp)
                    
                    done_so_far = sum(1 for _, t in delay_tests + edge_tests 
                                     if t.status not in (TestStatus.NOT_RUN, TestStatus.RUNNING))
                    self.progress(30 + done_so_far / total * 60, f"Test {done_so_far}/{total}")
            
            # ================================================================
            # PASS 2: EDGE VIEW - zoomed per measurement
            # ================================================================
            if edge_tests and self.running:
                self.log("")
                self.log("=" * 50)
                self.log("PASS 2: Edge View (zoomed timebase)")
                self.log("=" * 50)
                
                for idx, tp in edge_tests:
                    if not self.running:
                        break
                    if not tp.enabled:
                        tp.status = TestStatus.SKIPPED
                        continue
                    
                    spec = tp.extra_data.get('spec')
                    if not spec:
                        continue
                    
                    tp.status = TestStatus.RUNNING
                    if self.on_test_start:
                        self.on_test_start(tp)
                    
                    # Reconfigure scope for this edge measurement
                    self.log(f"\n--- {spec.name} ---")
                    self._configure_edge_view(spec, config)
                    
                    # Delete old measurements and set up just this one with statistics
                    num_samples = config.get("num_samples", 100)
                    self.inst.scope_write("MEASUrement:DELETEALL")
                    time.sleep(0.1)
                    meas_idx = tp.test_id
                    source1 = spec.source1_ref if self.ref_mode else spec.source1_live
                    
                    self.inst.scope_write(f'MEASUrement:ADDNew "MEAS{meas_idx}"')
                    self.inst.scope_write(f"MEASUrement:MEAS{meas_idx}:TYPe {spec.meas_type}")
                    self.inst.scope_write(f"MEASUrement:MEAS{meas_idx}:SOUrce {source1}")
                    self.inst.scope_write(f"MEASUrement:MEAS{meas_idx}:STATE ON")
                    
                    # Enable statistics with population limit for this measurement
                    self.inst.scope_write(f"MEASUrement:MEAS{meas_idx}:DISPlaystat:ENABle ON")
                    self.inst.scope_write(f"MEASUrement:MEAS{meas_idx}:POPUlation:LIMIT:STATE ON")
                    self.inst.scope_write(f"MEASUrement:MEAS{meas_idx}:POPUlation:LIMIT:VALue {num_samples}")
                    
                    self.log(f"  Measurement: {spec.meas_type} on {source1} (stats: {num_samples} samples)")
                    
                    if not self.ref_mode:
                        # Clear statistics and acquire with new trigger/timebase
                        self.log(f"  Acquiring {num_samples} samples...")
                        self.inst.scope_write("CLEAR")
                        self.inst.scope_write("ACQuire:STOPAfter RUNStop")
                        self.inst.scope_write("ACQuire:STATE RUN")
                        
                        timeout = max(30, num_samples * 0.5)
                        
                        if not self._wait_statistics_single(meas_idx, num_samples, timeout):
                            self.log(f"  WARNING: Statistics timeout for {spec.name}")
                            tp.status = TestStatus.ERROR
                            tp.extra_data['error'] = "Statistics acquisition timeout"
                            if self.on_test_complete:
                                self.on_test_complete(tp)
                            fail_count += 1
                            self.inst.scope_write("ACQuire:STATE STOP")
                            continue
                        
                        self.inst.scope_write("ACQuire:STATE STOP")
                    else:
                        time.sleep(0.3)  # Let measurement settle on REF waveforms
                    
                    # Read measurement
                    tp = self.run_single_test(tp, config)
                    
                    if tp.status == TestStatus.PASS:
                        pass_count += 1
                    elif tp.status in (TestStatus.FAIL, TestStatus.ERROR):
                        fail_count += 1
                    
                    # Capture screenshot for each edge measurement (shows zoomed view)
                    if self.output_dir:
                        safe_name = spec.name.lower().replace(" ", "_").replace("↑", "rise").replace("↓", "fall")
                        screenshot_path = self._capture_screenshot(safe_name)
                        if screenshot_path:
                            tp.screenshot_path = screenshot_path
                            if self.on_screenshot:
                                self.on_screenshot(screenshot_path)
                    
                    if self.on_test_complete:
                        self.on_test_complete(tp)
                    
                    done_so_far = sum(1 for _, t in delay_tests + edge_tests 
                                     if t.status not in (TestStatus.NOT_RUN, TestStatus.RUNNING))
                    self.progress(30 + done_so_far / total * 60, f"Test {done_so_far}/{total}")
            
            self.log(f"\nTest complete: {pass_count} passed, {fail_count} failed")
            
        except Exception as e:
            self.log(f"Test error: {e}")
            fail_count = len(self.test_points) - pass_count
        
        finally:
            # Only disable AWG in live mode
            if not self.ref_mode and self.awg:
                self.log("Disabling AWG outputs...")
                try:
                    self._awg_write("AWGControl:STOP")
                    self._awg_write("OUTPut1:STATe OFF")
                    self._awg_write("OUTPut2:STATe OFF")
                except:
                    pass
            
            self.running = False
            self.progress(100, "Complete")
            
            if self.on_complete:
                self.on_complete(pass_count, fail_count)
    
    def _wait_statistics(self, target_count: int, timeout: float) -> bool:
        """Wait for measurement statistics to accumulate to target count.
        
        Uses MEAS1 (first delay measurement) as the reference for population count.
        
        Args:
            target_count: Number of measurement samples to collect
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if target reached, False on timeout or stop
        """
        start = time.time()
        check_interval = 0.5
        last_count = 0
        
        while time.time() - start < timeout:
            if not self.running:
                return False
            
            try:
                pop_str = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:ALLAcqs:POPUlation?").strip()
                current_count = int(float(pop_str))
                
                if current_count >= target_count:
                    self.log(f"  Statistics complete: {current_count}/{target_count} samples")
                    return True
                
                if current_count != last_count:
                    elapsed = time.time() - start
                    pct = 10 + (current_count / target_count) * 20
                    self.progress(pct, f"Collecting statistics... {current_count}/{target_count}")
                    last_count = current_count
                    
            except Exception as e:
                pass  # Query may fail briefly during acquisition
            
            time.sleep(check_interval)
        
        return False
    
    def _wait_statistics_single(self, meas_idx: int, target_count: int, timeout: float) -> bool:
        """Wait for a specific measurement's statistics to accumulate.
        
        Args:
            meas_idx: Measurement index (e.g., 3 for MEAS3)
            target_count: Number of measurement samples to collect
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if target reached, False on timeout or stop
        """
        start = time.time()
        check_interval = 0.5
        last_count = 0
        
        while time.time() - start < timeout:
            if not self.running:
                return False
            
            try:
                pop_str = self.inst.scope_query(
                    f"MEASUrement:MEAS{meas_idx}:RESUlts:ALLAcqs:POPUlation?"
                ).strip()
                current_count = int(float(pop_str))
                
                if current_count >= target_count:
                    return True
                
                if current_count != last_count:
                    self.log(f"    {current_count}/{target_count} samples...")
                    last_count = current_count
                    
            except Exception:
                pass
            
            time.sleep(check_interval)
        
        return False
    
    def _capture_screenshot(self, label: str = "awg_pulse_timing") -> str:
        """Capture oscilloscope screenshot."""
        if not self.output_dir:
            return ""
        
        try:
            filename = f"{label}.png"
            filepath = Path(self.output_dir) / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Try multiple scope paths - C:/Temp preferred, C:/ as fallback
            scope_filename = f"awg_{label}.png"
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
            
            self.log(f"Screenshot saved: {filename}")
            return str(filepath)
            
        except Exception as e:
            self.log(f"Screenshot error: {e}")
            return ""
    
    def cleanup(self):
        """Cleanup after test."""
        self.running = False
        
        if self.awg:
            try:
                self._awg_write("AWGControl:STOP")
                self._awg_write("OUTPut1:STATe OFF")
                self._awg_write("OUTPut2:STATe OFF")
            except:
                pass
            
            # Only close if we opened it
            if self.awg_owned:
                try:
                    self.awg.close()
                    self.log("AWG connection closed.")
                except:
                    pass
            else:
                self.log("AWG outputs disabled.")
    
    def stop(self):
        """Stop the test."""
        self.running = False
        self.log("Stop requested.")


# =============================================================================
# PLUGIN REGISTRATION
# =============================================================================

def register_suites():
    """Register test suites with Tek PTA."""
    return [
        TestSuitePlugin(
            name="AWG70002B Pulse Timing Test",
            description=(
                "Verifies AWG70002B dual-channel pulse timing.\n\n"
                "Generates 100 kHz pulses (1µs ON, 9µs OFF) with CH2 "
                "delayed 2µs from CH1. Measures rise/fall times and "
                "inter-channel delays using measurement statistics "
                "(average of 50 individual measurements).\n\n"
                "Note: AWG differential output → single-ended scope input "
                "means scope sees half the configured amplitude."
            ),
            test_type="awg70002b_pulse",
            config={
                "awg_address": "TCPIP0::169.254.165.92::inst0::INSTR",
                "pulse_width_us": 1,
                "period_us": 10,
                "phase_offset_us": 2,
                "amplitude_v": 0.25,         # AWG differential amplitude (scope sees half)
                "sample_rate": 250e6,
                "num_samples": 100,           # Number of measurement samples for statistics
                # Setup instructions shown in dialog when Run Tests is clicked
                "setup_instructions": (
                    "AWG70002B Pulse Timing Test\n\n"
                    "Required Connections:\n"
                    "  • AWG CH1 → Scope CH1 (single-ended)\n"
                    "  • AWG CH2 → Scope CH3 (single-ended)\n\n"
                    "Note: Using single-ended connection means scope\n"
                    "sees half the AWG's differential amplitude.\n\n"
                    "Ensure AWG is connected and powered on."
                ),
            },
            required_instruments=[
                "AWG70002B",
                "MSO5/6 Series Oscilloscope"
            ],
            engine_class=AWG70002BPulseTimingEngine,
        ),
    ]
