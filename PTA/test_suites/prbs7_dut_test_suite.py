#!/usr/bin/env python3
"""
PRBS7 DUT Test Suite for Tek PTA
================================

Tests a Device Under Test (DUT) using AWG70000 series PRBS7 stimulus and 
MSO4/5/6 series oscilloscope measurements.

Test Configuration:
- AWG70000 CH1: PRBS7 pattern, 1Vpp differential, 250 Mbps (using HSS plug-in)
- Scope CH1: DUT output signal 1 (single-ended, sees ±250mV)
- Scope CH2: DUT output signal 2 (single-ended, sees ±250mV)
- Scope MATH1: CH1 - CH2 (differential, sees ±500mV)

Signal Levels:
- AWG differential output: ±0.5V on each leg (CH1+, CH1-)
- Single-ended scope input: ±250mV swing centered at 0V
- Differential (MATH): ±500mV swing centered at 0V

Measurements (per channel):
- Data Rate: 250 Mbps ±1%
- Amplitude: 500 mV ±25 mV (single-ended), 1V ±50 mV (differential)
- Pattern Length: 127 bits (2^7 - 1, exact match required)

PRBS7 Pattern Info:
- Pattern length: 2^7 - 1 = 127 bits
- Polynomial: x^7 + x^6 + 1
- At 250 Mbps: bit period = 4 ns
- Pattern duration: 127 × 4 ns = 508 ns

Setup Diagram Images:
- Location: C:\\Users\\u610842\\TektronixMCP\\PTA\\test_suites\\images\\
- These pre-made professional diagrams can be loaded for setup confirmation dialogs

Connections:
- AWG CH1 → DUT Input
- DUT Output 1 → Oscilloscope CH1 (50Ω)
- DUT Output 2 → Oscilloscope CH2 (50Ω)
"""

import time
import math
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


# =============================================================================
# PLUGIN API DEFINITIONS (copied for portability)
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
# SETUP DIALOG
# =============================================================================

class SetupDialog:
    """Graphical setup dialog with block diagram."""
    
    def __init__(self, parent, config: Dict[str, Any], has_awg: bool, ref_mode: bool):
        self.result = False
        self.config = config
        self.has_awg = has_awg
        self.ref_mode = ref_mode
        
        self.dialog = tk.Toplevel(parent) if parent else tk.Tk()
        self.dialog.title("Test Setup Required")
        self.dialog.configure(bg='#1a1a2e')
        
        self.dialog.transient(parent) if parent else None
        self.dialog.grab_set()
        
        width, height = 750, 700
        self.dialog.geometry(f"{width}x{height}")
        self.dialog.resizable(False, False)
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - width) // 2
        y = (self.dialog.winfo_screenheight() - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        self._create_widgets()
        
    def _create_widgets(self):
        bg_color = '#1a1a2e'
        box_bg = '#16213e'
        awg_border = '#e6a117'
        scope_border = '#00a8cc'
        dut_border = '#888888'
        text_color = '#ffffff'
        accent_color = '#00a8cc'
        label_color = '#e6a117'
        
        main_frame = tk.Frame(self.dialog, bg=bg_color)
        main_frame.pack(fill='both', expand=True, padx=20, pady=15)
        
        title_label = tk.Label(main_frame, text="Setup Diagram", 
                              font=('Segoe UI', 14, 'bold'),
                              fg=accent_color, bg=bg_color)
        title_label.pack(pady=(0, 5))
        
        amplitude = self.config.get('amplitude_v', 1.0)
        data_rate = self.config.get('data_rate_mbps', 250)
        
        subtitle = tk.Label(main_frame, text="PRBS7 DUT Test Setup",
                           font=('Segoe UI', 12, 'bold'),
                           fg=text_color, bg=bg_color)
        subtitle.pack(pady=(0, 15))
        
        # Canvas for block diagram
        canvas_frame = tk.Frame(main_frame, bg=bg_color)
        canvas_frame.pack(fill='x', pady=10)
        
        canvas = tk.Canvas(canvas_frame, width=700, height=200, 
                          bg=bg_color, highlightthickness=0)
        canvas.pack()
        
        # Draw AWG box
        awg_x1, awg_y1, awg_x2, awg_y2 = 50, 40, 200, 160
        canvas.create_rectangle(awg_x1, awg_y1, awg_x2, awg_y2,
                               outline=awg_border, width=2, fill=box_bg)
        canvas.create_text((awg_x1 + awg_x2) / 2, awg_y1 + 25,
                          text="AWG70000", font=('Segoe UI', 11, 'bold'),
                          fill=text_color)
        canvas.create_text((awg_x1 + awg_x2) / 2, awg_y1 + 50,
                          text="PRBS7", font=('Segoe UI', 9),
                          fill=label_color)
        canvas.create_text((awg_x1 + awg_x2) / 2, awg_y1 + 70,
                          text=f"{amplitude} Vpp diff", font=('Segoe UI', 9),
                          fill=label_color)
        canvas.create_text((awg_x1 + awg_x2) / 2, awg_y1 + 90,
                          text=f"{data_rate} Mbps", font=('Segoe UI', 9),
                          fill=label_color)
        
        # Draw DUT box
        dut_x1, dut_y1, dut_x2, dut_y2 = 300, 40, 430, 160
        canvas.create_rectangle(dut_x1, dut_y1, dut_x2, dut_y2,
                               outline=dut_border, width=2, fill=box_bg)
        canvas.create_text((dut_x1 + dut_x2) / 2, (dut_y1 + dut_y2) / 2,
                          text="DUT", font=('Segoe UI', 14, 'bold'),
                          fill=text_color)
        
        # Draw Scope box
        scope_x1, scope_y1, scope_x2, scope_y2 = 530, 40, 680, 160
        canvas.create_rectangle(scope_x1, scope_y1, scope_x2, scope_y2,
                               outline=scope_border, width=2, fill=box_bg)
        canvas.create_text((scope_x1 + scope_x2) / 2, scope_y1 + 25,
                          text="MSO4/5/6", font=('Segoe UI', 11, 'bold'),
                          fill=text_color)
        canvas.create_text(scope_x2 - 25, scope_y1 + 55,
                          text="50Ω", font=('Segoe UI', 9), fill=text_color)
        canvas.create_text(scope_x2 - 25, scope_y1 + 95,
                          text="50Ω", font=('Segoe UI', 9), fill=text_color)
        canvas.create_text((scope_x1 + scope_x2) / 2, scope_y2 - 15,
                          text="MATH1=CH1-CH2", font=('Segoe UI', 8),
                          fill=accent_color)
        
        # Connection lines
        y_ch1 = 70
        canvas.create_line(awg_x2, y_ch1, dut_x1, y_ch1, fill=text_color, width=2, arrow=tk.LAST)
        canvas.create_text(awg_x2 + 15, y_ch1 - 12, text="CH1",
                          font=('Segoe UI', 9, 'bold'), fill=label_color, anchor='w')
        canvas.create_text(dut_x1 - 15, y_ch1 - 12, text="IN",
                          font=('Segoe UI', 9), fill=text_color, anchor='e')
        canvas.create_text((awg_x2 + dut_x1) / 2, y_ch1 - 12, text="50Ω Coax",
                          font=('Segoe UI', 8), fill='#888888')
        
        y_out1 = 70
        canvas.create_line(dut_x2, y_out1, scope_x1, y_out1, fill=text_color, width=2, arrow=tk.LAST)
        canvas.create_text(dut_x2 + 15, y_out1 - 12, text="OUT1",
                          font=('Segoe UI', 9), fill=text_color, anchor='w')
        canvas.create_text(scope_x1 - 15, y_out1 - 12, text="CH1",
                          font=('Segoe UI', 9, 'bold'), fill=accent_color, anchor='e')
        
        y_out2 = 130
        canvas.create_line(dut_x2, y_out2, scope_x1, y_out2, fill=text_color, width=2, arrow=tk.LAST)
        canvas.create_text(dut_x2 + 15, y_out2 - 12, text="OUT2",
                          font=('Segoe UI', 9), fill=text_color, anchor='w')
        canvas.create_text(scope_x1 - 15, y_out2 - 12, text="CH2",
                          font=('Segoe UI', 9, 'bold'), fill=accent_color, anchor='e')
        canvas.create_text((dut_x2 + scope_x1) / 2, y_out2 + 15, text="50Ω Coax",
                          font=('Segoe UI', 8), fill='#888888')
        
        # Info section
        info_frame = tk.Frame(main_frame, bg=bg_color)
        info_frame.pack(fill='x', pady=15)
        
        left_frame = tk.Frame(info_frame, bg=bg_color)
        left_frame.pack(side='left', anchor='nw', padx=20)
        
        conn_title = tk.Label(left_frame, text="Connections:",
                             font=('Segoe UI', 10, 'bold'),
                             fg=text_color, bg=bg_color)
        conn_title.pack(anchor='w')
        
        connections = [
            "• AWG CH1 → DUT Input (50Ω)",
            "• DUT Output 1 → Scope CH1 (50Ω)",
            "• DUT Output 2 → Scope CH2 (50Ω)",
            "• MATH1 = CH1 - CH2 (differential)",
        ]
        for conn in connections:
            lbl = tk.Label(left_frame, text=conn, font=('Segoe UI', 9),
                          fg=text_color, bg=bg_color)
            lbl.pack(anchor='w', pady=1)
        
        right_frame = tk.Frame(info_frame, bg=bg_color)
        right_frame.pack(side='right', anchor='ne', padx=20)
        
        meas_title = tk.Label(right_frame, text="Measurements:",
                             font=('Segoe UI', 10, 'bold'),
                             fg=text_color, bg=bg_color)
        meas_title.pack(anchor='w')
        
        measurements = [
            "Data Rate, Amplitude, Pattern Length",
            "• CH1, CH2: 500 mV ±25 mV",
            "• MATH1 (diff): 1.0 V ±50 mV",
            "• Pattern: 127 bits (PRBS7)",
        ]
        for meas in measurements:
            color = accent_color if meas.startswith("Data") else text_color
            lbl = tk.Label(right_frame, text=meas, font=('Segoe UI', 9),
                          fg=color, bg=bg_color)
            lbl.pack(anchor='w', pady=1)
        
        # Summary box
        summary_frame = tk.Frame(main_frame, bg=box_bg, padx=15, pady=10)
        summary_frame.pack(fill='x', pady=15)
        
        summary_title = tk.Label(summary_frame, text="PRBS7 DUT TEST",
                                font=('Segoe UI', 10, 'bold'),
                                fg=text_color, bg=box_bg)
        summary_title.pack()
        
        bit_period = 1000 / data_rate
        pattern_time = 127 * bit_period
        
        summary_lines = [
            f"AWG CH1 → DUT → Scope CH1/CH2 (50Ω)",
            f"Pattern: PRBS7 (127 bits, x⁷+x⁶+1)",
            f"Data Rate: {data_rate} Mbps ({bit_period:.1f} ns/bit)",
            f"Pattern Duration: {pattern_time:.1f} ns",
            f"Captures: 4+ complete patterns",
        ]
        
        for line in summary_lines:
            lbl = tk.Label(summary_frame, text=line, font=('Segoe UI', 9),
                          fg='#aaaaaa', bg=box_bg)
            lbl.pack()
        
        if not self.has_awg and not self.ref_mode:
            warn_label = tk.Label(main_frame, 
                                 text="⚠ No AWG connected - enable Reference Mode or connect AWG",
                                 font=('Segoe UI', 10, 'bold'),
                                 fg='#ff6b6b', bg=bg_color)
            warn_label.pack(pady=5)
        elif self.ref_mode:
            ref_label = tk.Label(main_frame,
                                text="📁 Reference Mode - Using pre-recorded waveforms",
                                font=('Segoe UI', 10),
                                fg=accent_color, bg=bg_color)
            ref_label.pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=bg_color)
        button_frame.pack(pady=20)
        
        start_btn = tk.Button(button_frame, text="Start Test",
                             font=('Segoe UI', 11, 'bold'),
                             bg='#28a745', fg='white',
                             activebackground='#218838', activeforeground='white',
                             width=15, height=1, bd=0,
                             command=self._on_start)
        start_btn.pack(side='left', padx=10)
        
        cancel_btn = tk.Button(button_frame, text="Cancel",
                              font=('Segoe UI', 11),
                              bg='#6c757d', fg='white',
                              activebackground='#5a6268', activeforeground='white',
                              width=12, height=1, bd=0,
                              command=self._on_cancel)
        cancel_btn.pack(side='left', padx=10)
    
    def _on_start(self):
        self.result = True
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.result = False
        self.dialog.destroy()
    
    def show(self) -> bool:
        self.dialog.wait_window()
        return self.result


def show_setup_dialog(config: Dict[str, Any], has_awg: bool, ref_mode: bool) -> bool:
    try:
        root = tk._default_root
        dialog = SetupDialog(root, config, has_awg, ref_mode)
        return dialog.show()
    except Exception as e:
        print(f"Dialog error: {e}")
        return True


# =============================================================================
# MEASUREMENT SPECIFICATIONS
# =============================================================================

@dataclass
class MeasurementSpec:
    """Specification for a single measurement"""
    name: str
    meas_type: str      # DATARATE, AMPLITUDE, PATTERNLENGTH
    source: str         # CH1, CH2, MATH1
    nominal: float      # Expected value (raw)
    lower_limit: float  # Absolute lower limit (raw)
    upper_limit: float  # Absolute upper limit (raw)
    unit: str           # Display unit
    display_scale: float = 1.0  # For converting raw to display


def get_measurement_specs(data_rate_mbps: float) -> List[MeasurementSpec]:
    """Generate measurement specifications."""
    data_rate_hz = data_rate_mbps * 1e6
    pattern_length = 127  # PRBS7 = 2^7 - 1
    
    # Single-ended amplitude: 500 mV ±25 mV (scope sees ±250mV swing = 500mV p-p)
    se_amp_nom = 0.500
    se_amp_low = 0.475
    se_amp_high = 0.525
    
    # Differential amplitude: 1.0 V ±50 mV
    diff_amp_nom = 1.0
    diff_amp_low = 0.95
    diff_amp_high = 1.05
    
    # Data rate tolerance: ±1%
    dr_low = data_rate_hz * 0.99
    dr_high = data_rate_hz * 1.01
    
    # Pattern length: exact match (±0)
    pl_low = pattern_length
    pl_high = pattern_length
    
    return [
        # CH1 measurements
        MeasurementSpec("CH1 Data Rate", "DATARATE", "CH1", 
                       data_rate_hz, dr_low, dr_high, "Mbps", 1e-6),
        MeasurementSpec("CH1 Amplitude", "AMPLITUDE", "CH1",
                       se_amp_nom, se_amp_low, se_amp_high, "V", 1.0),
        MeasurementSpec("CH1 Pattern Length", "PATTERNLENGTH", "CH1",
                       pattern_length, pl_low, pl_high, "bits", 1.0),
        
        # CH2 measurements
        MeasurementSpec("CH2 Data Rate", "DATARATE", "CH2",
                       data_rate_hz, dr_low, dr_high, "Mbps", 1e-6),
        MeasurementSpec("CH2 Amplitude", "AMPLITUDE", "CH2",
                       se_amp_nom, se_amp_low, se_amp_high, "V", 1.0),
        MeasurementSpec("CH2 Pattern Length", "PATTERNLENGTH", "CH2",
                       pattern_length, pl_low, pl_high, "bits", 1.0),
        
        # MATH1 (differential) measurements
        MeasurementSpec("Diff Data Rate", "DATARATE", "MATH1",
                       data_rate_hz, dr_low, dr_high, "Mbps", 1e-6),
        MeasurementSpec("Diff Amplitude", "AMPLITUDE", "MATH1",
                       diff_amp_nom, diff_amp_low, diff_amp_high, "V", 1.0),
        MeasurementSpec("Diff Pattern Length", "PATTERNLENGTH", "MATH1",
                       pattern_length, pl_low, pl_high, "bits", 1.0),
    ]


# =============================================================================
# PRBS7 DUT TEST ENGINE
# =============================================================================

class PRBS7DUTTestEngine(TestEngineBase):
    """Test engine for PRBS7 DUT testing."""
    
    def __init__(self, instrument_manager):
        super().__init__(instrument_manager)
        self.awg = None
        self.awg_owned = False
        self.config = {}
        self.ref_mode = False
        self.meas_specs = []
    
    def generate_test_points(self, config: Dict[str, Any]) -> List[TestPoint]:
        """Generate test points from measurement specifications."""
        data_rate_mbps = config.get('data_rate_mbps', 250)
        self.meas_specs = get_measurement_specs(data_rate_mbps)
        self.test_points = []
        
        for i, spec in enumerate(self.meas_specs, start=1):
            # Apply display scale to values
            display_nominal = spec.nominal * spec.display_scale
            display_lower = spec.lower_limit * spec.display_scale
            display_upper = spec.upper_limit * spec.display_scale
            
            # Calculate tolerance percentage for display
            if spec.nominal != 0:
                tol_pct = abs((spec.upper_limit - spec.nominal) / spec.nominal) * 100
            else:
                tol_pct = 0
            
            tp = TestPoint(
                test_id=i,
                name=spec.name,
                nominal_value=display_nominal,
                unit=spec.unit,
                tolerance_pct=tol_pct,
                has_limits=True,
                lower_limit=display_lower,
                upper_limit=display_upper,
                enabled=True,
            )
            tp.extra_data['spec'] = spec
            tp.extra_data['raw_nominal'] = spec.nominal
            tp.extra_data['raw_lower'] = spec.lower_limit
            tp.extra_data['raw_upper'] = spec.upper_limit
            self.test_points.append(tp)
        
        return self.test_points
    
    def _nice_scale(self, value: float) -> float:
        """Round to nice oscilloscope scale (1-2-5 sequence)."""
        if value <= 0:
            return 0.001
        
        exp = math.floor(math.log10(value))
        mantissa = value / (10 ** exp)
        
        if mantissa < 1.5:
            nice_mantissa = 1
        elif mantissa < 3.5:
            nice_mantissa = 2
        elif mantissa < 7.5:
            nice_mantissa = 5
        else:
            nice_mantissa = 10
        
        return nice_mantissa * (10 ** exp)
    
    def _connect_awg(self, config: Dict[str, Any]) -> bool:
        """Connect to AWG via InstrumentManager."""
        if self.inst.awg is not None:
            self.awg = self.inst.awg
            self.awg_owned = False
            self.log(f"Using connected AWG: {self.inst.awg_info.model if self.inst.awg_info else 'AWG'}")
            return True
        
        self.log("No AWG connected via Instrument Manager")
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
    
    def setup_instruments(self, config: Dict[str, Any]) -> bool:
        """Configure instruments for the test."""
        self.config = config
        
        self.ref_mode = (self.reference_config is not None and 
                         self.reference_config.enabled)
        
        has_awg = self.inst.awg is not None
        
        if not show_setup_dialog(config, has_awg, self.ref_mode):
            self.log("Test cancelled by user")
            return False
        
        try:
            if self.ref_mode:
                self.log("=" * 60)
                self.log("REFERENCE MODE - Using pre-recorded waveforms")
                self.log("=" * 60)
                
                if not self._setup_oscilloscope_ref_mode(config):
                    return False
                if not self._setup_measurements(config):
                    return False
                return True
            else:
                self.log("=" * 60)
                self.log("LIVE MODE - Using AWG")
                self.log("=" * 60)
                
                if not self._connect_awg(config):
                    self.log("ERROR: No AWG available. Connect an AWG or enable Reference Mode.")
                    return False
                if not self._setup_awg(config):
                    return False
                if not self._setup_oscilloscope(config):
                    return False
                if not self._setup_measurements(config):
                    return False
                return True
            
        except Exception as e:
            self.log(f"Setup error: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False
    
    def _setup_awg(self, config: Dict[str, Any]) -> bool:
        """Configure AWG70000 using HSS Plug-in for PRBS7."""
        amplitude_v = config.get('amplitude_v', 1.0)
        data_rate_mbps = config.get('data_rate_mbps', 250)
        
        self.log("Configuring AWG with HSS plug-in for PRBS7...")
        
        try:
            self._awg_write('OUTPut1:STATe OFF')
            self._awg_query('*OPC?')
            self._awg_write('AWGControl:STOP')
            self._awg_query('*OPC?')
            
            # Select High Speed Serial plug-in
            self.log("Selecting High Speed Serial plug-in...")
            self._awg_write('WPLUGin:ACTive "High Speed Serial"')
            self._awg_query('*OPC?')
            
            active_plugin = self._awg_query('WPLUGin:ACTive?')
            self.log(f"  Active plug-in: {active_plugin}")
            
            # Configure PRBS7
            self._awg_write('HSSerial:BDATa PRBS')
            self._awg_query('*OPC?')
            
            self._awg_write('HSSerial:BDATa:PRBS PRBS7')
            self._awg_query('*OPC?')
            self.log(f"  Pattern: PRBS7 (127 bits)")
            
            self._awg_write(f'HSSerial:DRATe {data_rate_mbps * 1e6}')
            self._awg_query('*OPC?')
            self.log(f"  Data rate: {data_rate_mbps} Mbps")
            
            high_v = amplitude_v / 2.0
            low_v = -amplitude_v / 2.0
            self._awg_write(f'HSSerial:AMPLitude:MAXimum {high_v}')
            self._awg_write(f'HSSerial:AMPLitude:MINimum {low_v}')
            self._awg_query('*OPC?')
            self.log(f"  Amplitude: {amplitude_v} Vpp diff ({low_v}V to {high_v}V each leg)")
            
            wfm_name = "PRBS7_DUT"
            self._awg_write(f'HSSerial:COMPile:NAME "{wfm_name}"')
            self._awg_query('*OPC?')
            
            self._awg_write('HSSerial:COMPile:OPTions ON')
            self._awg_query('*OPC?')
            self.log("  Compile and assign: ON")
            
            self._awg_write('HSSerial:COMPile:OVERwrite ON')
            self._awg_query('*OPC?')
            
            self.log("  Compiling PRBS7 waveform...")
            self._awg_write('HSSerial:COMPile')
            self._awg_query('*OPC?')
            self.log(f"  Compiled and assigned waveform '{wfm_name}' to CH1")
            
            try:
                assigned_wfm = self._awg_query('SOURce1:WAVeform?')
                self.log(f"  CH1 waveform: {assigned_wfm}")
            except:
                pass
            
            self._awg_write('AWGControl:RMODe CONTinuous')
            self._awg_query('*OPC?')
            self.log("  Run mode: Continuous")
            
            return True
            
        except Exception as e:
            self.log(f"AWG setup error: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False
    
    def _setup_oscilloscope(self, config: Dict[str, Any]) -> bool:
        """Configure oscilloscope for live mode."""
        amplitude_v = config.get('amplitude_v', 1.0)
        data_rate_mbps = config.get('data_rate_mbps', 250)
        
        self.log("Configuring oscilloscope...")
        
        # AWG differential output: ±0.5V on each leg (CH1+, CH1-)
        # Single-ended scope input sees ±250mV swing centered at 0V
        se_amplitude = amplitude_v / 2.0  # 500mV peak-to-peak
        v_scale = self._nice_scale(se_amplitude / 6.0)  # ~83mV/div -> 100mV/div
        
        # Horizontal: capture 4+ PRBS7 patterns for pattern length measurement
        bit_period_s = 1.0 / (data_rate_mbps * 1e6)
        pattern_time_s = 127 * bit_period_s  # One PRBS7 pattern = 508ns at 250Mbps
        total_time_s = 4 * pattern_time_s  # 4 patterns = ~2µs
        h_scale = self._nice_scale(total_time_s / 10.0)
        
        self.inst.scope_write('*RST')
        self.inst.scope_opc(10)
        self.inst.scope_write('HEADer OFF')
        
        # Enable CH1 and CH2
        self.inst.scope_write('DISplay:WAVEView1:CH1:STATE ON')
        self.inst.scope_write('DISplay:WAVEView1:CH2:STATE ON')
        self.inst.scope_write('DISplay:WAVEView1:CH3:STATE OFF')
        self.inst.scope_write('DISplay:WAVEView1:CH4:STATE OFF')
        
        # 50 ohm termination for high-speed signals
        self.inst.scope_write('CH1:TERmination 50')
        self.inst.scope_write('CH2:TERmination 50')
        
        # Vertical scale - signal swings ±250mV centered at 0V
        # Offset = 0, Trigger = 0
        self.inst.scope_write(f'CH1:SCAle {v_scale}')
        self.inst.scope_write(f'CH2:SCAle {v_scale}')
        self.inst.scope_write('CH1:OFFSet 0')
        self.inst.scope_write('CH2:OFFSet 0')
        
        self.log(f"  CH1, CH2: {v_scale*1000:.1f} mV/div, 50Ω, offset 0V")
        
        # Horizontal scale - show 4+ patterns
        self.inst.scope_write(f'HORizontal:SCAle {h_scale}')
        self.inst.scope_write('HORizontal:POSition 10')
        self.log(f"  Horizontal: {h_scale*1e6:.3f} µs/div (captures ~{total_time_s/pattern_time_s:.0f} patterns)")
        
        # Setup MATH1 = CH1 - CH2 (differential)
        self.log("  Setting up MATH1 = CH1 - CH2 (differential)...")
        self.inst.scope_write('MATH:ADDNew "MATH1"')
        self.inst.scope_write('MATH:MATH1:TYPe BASic')
        self.inst.scope_write('MATH:MATH1:FUNCtion SUBtract')
        self.inst.scope_write('MATH:MATH1:SOUrce1 CH1')
        self.inst.scope_write('MATH:MATH1:SOUrce2 CH2')
        self.inst.scope_write('DISplay:WAVEView1:MATH:MATH1:STATE ON')
        
        # MATH scale (differential = 2x single-ended, also centered at 0V)
        math_scale = self._nice_scale(amplitude_v / 6.0)
        self.inst.scope_write(f'DISplay:WAVEView1:MATH:MATH1:VERTical:SCAle {math_scale}')
        self.log(f"  MATH1: {math_scale*1000:.1f} mV/div")
        
        # Trigger at 0V (middle of ±250mV swing)
        self.inst.scope_write('TRIGger:A:TYPE EDGE')
        self.inst.scope_write('TRIGger:A:EDGE:SOURce CH1')
        self.inst.scope_write('TRIGger:A:EDGE:SLOpe RISE')
        self.inst.scope_write('TRIGger:A:LEVel:CH1 0')
        self.inst.scope_write('TRIGger:A:MODE NORMAL')
        self.log("  Trigger: CH1 rising edge at 0V")
        
        return True
    
    def _setup_oscilloscope_ref_mode(self, config: Dict[str, Any]) -> bool:
        """Configure oscilloscope for reference waveform mode."""
        self.log("Configuring oscilloscope for reference mode...")
        
        self.inst.scope_write('*RST')
        self.inst.scope_opc(10)
        self.inst.scope_write('HEADer OFF')
        
        if not self._reload_reference_waveforms():
            return False
        
        for ch in range(1, 5):
            self.inst.scope_write(f'DISplay:WAVEView1:CH{ch}:STATE OFF')
        
        self.inst.scope_write('DISplay:WAVEView1:REF1:STATE ON')
        self.inst.scope_write('DISplay:WAVEView1:REF2:STATE ON')
        
        return True
    
    def _reload_reference_waveforms(self) -> bool:
        """Reload reference waveforms."""
        if not self.reference_config:
            self.log("ERROR: No reference config available")
            return False
        
        self.log("Reloading reference waveforms...")
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
    
    def _setup_measurements(self, config: Dict[str, Any]) -> bool:
        """Configure measurements on scope."""
        self.log("Setting up measurements...")
        
        meas_num = 1
        for tp in self.test_points:
            spec = tp.extra_data.get('spec')
            if not spec:
                continue
            
            source = spec.source
            
            # Configure measurement type
            self.inst.scope_write(f'MEASUrement:MEAS{meas_num}:TYPE {spec.meas_type}')
            self.inst.scope_write(f'MEASUrement:MEAS{meas_num}:SOUrce {source}')
            
            # For pattern length, set auto detection
            if spec.meas_type == 'PATTERNLENGTH':
                self.inst.scope_write(f'MEASUrement:MEAS{meas_num}:PATTERNDETECTION AUTO')
            
            self.inst.scope_write(f'MEASUrement:MEAS{meas_num}:STATE ON')
            
            self.log(f"  MEAS{meas_num}: {spec.meas_type} on {source}")
            
            tp.extra_data['meas_num'] = meas_num
            meas_num += 1
        
        self.inst.scope_opc(5)
        return True
    
    def run_single_test(self, test_point: TestPoint, config: Dict[str, Any]) -> TestPoint:
        """Run a single measurement."""
        spec = test_point.extra_data.get('spec')
        meas_num = test_point.extra_data.get('meas_num', 1)
        
        if not spec:
            test_point.status = TestStatus.ERROR
            return test_point
        
        try:
            # Use CURRentacq for single acquisition measurement
            raw_value = float(self.inst.scope_query(
                f'MEASUrement:MEAS{meas_num}:RESUlts:CURRentacq:MEAN?'
            ))
            
            # Check for invalid measurement
            if math.isnan(raw_value) or math.isinf(raw_value) or raw_value > 1e30:
                test_point.status = TestStatus.ERROR
                test_point.extra_data['error'] = "Invalid measurement"
                return test_point
            
            display_value = raw_value * spec.display_scale
            test_point.measured_value = display_value
            
            raw_lower = test_point.extra_data.get('raw_lower', 0)
            raw_upper = test_point.extra_data.get('raw_upper', float('inf'))
            
            if raw_lower <= raw_value <= raw_upper:
                test_point.status = TestStatus.PASS
            else:
                test_point.status = TestStatus.FAIL
            
            raw_nominal = test_point.extra_data.get('raw_nominal', raw_value)
            if raw_nominal != 0:
                test_point.error_pct = ((raw_value - raw_nominal) / raw_nominal) * 100
            
        except Exception as e:
            test_point.status = TestStatus.ERROR
            test_point.extra_data['error'] = str(e)
        
        return test_point
    
    def _format_value(self, value: float, unit: str) -> str:
        """Format measurement value for display."""
        if unit == "Mbps":
            return f"{value:.3f} {unit}"
        elif unit == "V":
            if value >= 1:
                return f"{value:.4f} V"
            else:
                return f"{value*1000:.2f} mV"
        elif unit == "bits":
            return f"{value:.0f} bits"
        else:
            return f"{value:.6g} {unit}"
    
    def _print_results_table(self):
        """Print results in table format matching Tek PTA standard."""
        self.log("")
        self.log("=" * 110)
        self.log(f"{'#':<4} {'Test Name':<20} {'Nominal':>14} {'Lower Limit':>14} {'Upper Limit':>14} {'Measured':>14} {'Status':>8}")
        self.log("-" * 110)
        
        for tp in self.test_points:
            nominal_str = self._format_value(tp.nominal_value, tp.unit)
            lower_str = self._format_value(tp.lower_limit, tp.unit)
            upper_str = self._format_value(tp.upper_limit, tp.unit)
            measured_str = self._format_value(tp.measured_value, tp.unit) if tp.measured_value else "---"
            status_str = tp.status.value
            
            self.log(f"{tp.test_id:<4} {tp.name:<20} {nominal_str:>14} {lower_str:>14} {upper_str:>14} {measured_str:>14} {status_str:>8}")
        
        self.log("=" * 110)
    
    def _capture_screenshot(self, label: str = "prbs7_dut") -> str:
        """Capture oscilloscope screenshot."""
        if not self.output_dir:
            return ""
        
        try:
            filename = f"{label}.png"
            filepath = Path(self.output_dir) / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            scope_filename = f"prbs7_{label}.png"
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
            
            try:
                self.inst.scope_write(f'FILESystem:DELEte "{used_path}"')
            except:
                pass
            
            self.log(f"Screenshot saved: {filename}")
            
            # Notify UI
            if self.on_screenshot:
                self.on_screenshot(str(filepath))
            
            return str(filepath)
            
        except Exception as e:
            self.log(f"Screenshot error: {e}")
            return ""
    
    def run(self, config: Dict[str, Any]):
        """Run the PRBS7 DUT test."""
        self.running = True
        
        if not self.setup_instruments(config):
            self.log("ERROR: Instrument setup failed")
            if self.on_complete:
                self.on_complete(0, len(self.test_points))
            return
        
        pass_count = 0
        fail_count = 0
        
        try:
            if not self.ref_mode:
                self.log("Enabling AWG output...")
                self._awg_write('OUTPut1:STATe ON')
                self._awg_write('AWGControl:RUN')
                self._awg_query('*OPC?')
                time.sleep(0.5)
                
                self.progress(10, "AWG running, acquiring waveform...")
                
                # Single acquisition for serial pattern measurement
                self.log("Starting single acquisition...")
                self.inst.scope_write('ACQuire:MODe SAMple')
                self.inst.scope_write('ACQuire:STOPAfter SEQuence')  # Single shot
                self.inst.scope_write('ACQuire:STATE RUN')
                
                # Wait for acquisition to complete
                self.log("  Waiting for trigger and acquisition...")
                timeout = 30  # seconds
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    if not self.running:
                        self.log("  Acquisition cancelled")
                        break
                    
                    try:
                        state = self.inst.scope_query('ACQuire:STATE?').strip()
                        if state == '0':
                            self.log("  Acquisition complete")
                            break
                    except:
                        pass
                    
                    time.sleep(0.2)
                else:
                    self.log("WARNING: Acquisition timeout - no trigger?")
                
                self.progress(50, "Acquisition complete, reading measurements...")
                
            else:
                self.log("Reference mode - reading measurements...")
                time.sleep(0.3)
            
            # Capture single screenshot for all tests (they share the same view)
            screenshot_path = ""
            if self.output_dir:
                screenshot_path = self._capture_screenshot("prbs7_capture")
            
            # Run measurements
            self.log("")
            self.log("=" * 60)
            self.log("RUNNING MEASUREMENTS")
            self.log("=" * 60)
            
            total = len(self.test_points)
            
            for i, tp in enumerate(self.test_points):
                if not self.running:
                    break
                
                if not tp.enabled:
                    tp.status = TestStatus.SKIPPED
                    continue
                
                tp.status = TestStatus.RUNNING
                if self.on_test_start:
                    self.on_test_start(tp)
                
                tp = self.run_single_test(tp, config)
                
                # Assign same screenshot to all tests (they share one view)
                if screenshot_path:
                    tp.screenshot_path = screenshot_path
                
                if tp.status == TestStatus.PASS:
                    pass_count += 1
                elif tp.status in (TestStatus.FAIL, TestStatus.ERROR):
                    fail_count += 1
                
                if self.on_test_complete:
                    self.on_test_complete(tp)
                
                self.progress(50 + (i + 1) / total * 50, f"Test {i + 1}/{total}")
            
            # Print results table
            self._print_results_table()
            
            self.log("")
            self.log(f"Test Summary: {pass_count} PASSED, {fail_count} FAILED")
            
        except Exception as e:
            self.log(f"FATAL ERROR: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            if not self.ref_mode and self.awg:
                self.log("Disabling AWG output...")
                try:
                    self._awg_write('AWGControl:STOP')
                    self._awg_write('OUTPut1:STATe OFF')
                except:
                    pass
            
            self.running = False
            self.progress(100, "Complete")
            
            if self.on_complete:
                self.on_complete(pass_count, fail_count)
    
    def cleanup(self):
        """Cleanup after test."""
        self.running = False
        
        if self.awg:
            try:
                self._awg_write('AWGControl:STOP')
                self._awg_write('OUTPut1:STATe OFF')
            except:
                pass
            
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
            name="PRBS7 DUT Test",
            description=(
                "Tests DUT with PRBS7 stimulus from AWG70000 series.\n\n"
                "Measurements per channel (CH1, CH2, MATH differential):\n"
                "  • Data Rate: 250 Mbps ±1%\n"
                "  • Amplitude: 500 mV ±25 mV (SE), 1V ±50 mV (diff)\n"
                "  • Pattern Length: 127 bits (PRBS7)\n\n"
                "Supports reference waveform mode when AWG is not available."
            ),
            test_type="prbs7_dut_test",
            config={
                'amplitude_v': 1.0,        # AWG differential amplitude
                'data_rate_mbps': 250,     # 250 Mbps
            },
            required_instruments=[
                "AWG70000 Series (optional with reference mode)",
                "MSO4/5/6 Series Oscilloscope"
            ],
            engine_class=PRBS7DUTTestEngine,
        ),
    ]


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("PRBS7 DUT Test Suite for Tek PTA")
    print("=" * 70)
    print()
    print("Measurements:")
    print("  CH1, CH2 (single-ended):")
    print("    - Data Rate: 250 Mbps ±1%")
    print("    - Amplitude: 500 mV ±25 mV")
    print("    - Pattern Length: 127 bits")
    print()
    print("  MATH1 (differential = CH1 - CH2):")
    print("    - Data Rate: 250 Mbps ±1%")
    print("    - Amplitude: 1.0 V ±50 mV")
    print("    - Pattern Length: 127 bits")
    print()
    print("PRBS7: 2^7 - 1 = 127 bits, polynomial x^7 + x^6 + 1")
    print()
    print("Setup Diagram Images Location:")
    print("  C:\\Users\\u610842\\TektronixMCP\\PTA\\test_suites\\images\\")
    print()
    print("Installation: Copy to test_suites/ folder next to tek_pta.py")
    print("-" * 70)
