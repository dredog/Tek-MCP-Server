#!/usr/bin/env python3
"""
Tek PTA Plugin API
==================

This module provides the base classes and data structures for creating
external test suite plugins for Tek PTA.

Usage in a plugin file:
    from tek_pta_plugin_api import TestSuitePlugin, TestEngineBase, TestPoint, TestStatus
    
    class MyCustomEngine(TestEngineBase):
        def generate_test_points(self, config=None):
            # REQUIRED: Called when test suite is selected to populate UI table
            self.test_points = []
            for i in range(5):
                self.test_points.append(TestPoint(
                    test_id=i+1,
                    name=f"Test {i+1}",
                    nominal_value=100.0,
                    unit="mV",
                    lower_limit=90.0,
                    upper_limit=110.0,
                ))
            return self.test_points
        
        def run(self, config):
            # Called when "Run" button is clicked
            # Test points already exist from generate_test_points()
            for tp in self.test_points:
                tp.status = TestStatus.RUNNING
                # ... perform measurement ...
                tp.measured_value = 99.5
                tp.status = TestStatus.PASS
            return self.test_points
    
    def register_suites():
        return [
            TestSuitePlugin(
                name="My Custom Test",
                description="Description of what this test does",
                test_type="my_custom",
                config={"param1": 10, "param2": "value"},
                required_instruments=["Oscilloscope"],
                engine_class=MyCustomEngine,
            ),
        ]

CRITICAL: The generate_test_points() method is called when the user SELECTS the test
suite in the UI, NOT when they click "Run". This is how Tek PTA populates the test
table before execution. If you don't implement generate_test_points(), the UI will
show an empty test table and nothing will happen when you click the suite button.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Type
from enum import Enum


class TestStatus(Enum):
    """Status of a test point"""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "Skipped"


@dataclass
class ReferenceConfig:
    """Configuration for using reference waveforms instead of live acquisition"""
    enabled: bool = False
    ref_files: Dict[str, str] = field(default_factory=dict)  # {"REF1": "path/to/file.wfm", ...}
    test_numbers: str = "all"  # "all" or comma-separated like "1-5,10,15-20"
    
    def applies_to_test(self, test_id: int) -> bool:
        """Check if this reference config applies to a specific test number"""
        if not self.enabled:
            return False
        if self.test_numbers.lower() == "all":
            return True
        
        # Parse test number specification like "1-5,10,15-20"
        try:
            for part in self.test_numbers.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = part.split('-')
                    if int(start) <= test_id <= int(end):
                        return True
                else:
                    if int(part) == test_id:
                        return True
        except ValueError:
            return False
        return False
    
    def get_ref_for_channel(self, channel: int) -> str:
        """Get the reference channel name for a given live channel"""
        return f"REF{channel}"


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
    """
    Definition of a test suite that can be loaded by Tek PTA.
    
    Attributes:
        name: Display name shown in the test suite selector
        description: Detailed description of what the test does
        test_type: Unique identifier for this test type (e.g., "afg_freq", "power_supply")
        config: Default configuration parameters for this test
        required_instruments: List of required equipment (shown in UI)
        engine_class: Optional custom TestEngineBase subclass for test execution
        config_panel_builder: Optional function to build custom config UI
        setup_diagram_generator: Optional function to generate setup diagram image
        results_columns: Optional custom columns for results tree [(name, width), ...]
    """
    name: str
    description: str
    test_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Optional[Type] = None
    config_panel_builder: Optional[Callable] = None
    setup_diagram_generator: Optional[Callable] = None
    results_columns: Optional[List[tuple]] = None
    
    def to_test_suite(self):
        """Convert to internal TestSuite format"""
        # Import here to avoid circular dependency
        from tek_pta import TestSuite
        return TestSuite(
            name=self.name,
            description=self.description,
            test_type=self.test_type,
            config=self.config,
            required_instruments=self.required_instruments,
        )


class TestEngineBase:
    """
    Base class for custom test engines.
    
    Subclass this to create your own test execution logic.
    The main application will instantiate your engine and call
    the appropriate methods during test execution.
    
    Callbacks (set by main app):
        on_log: Called with log message string
        on_progress: Called with (percentage, status_message)
        on_test_start: Called with TestPoint when test starts
        on_test_complete: Called with TestPoint when test completes
        on_screenshot: Called with screenshot path
        on_complete: Called with (pass_count, fail_count) when all tests done
    
    Reference Mode:
        reference_config: ReferenceConfig instance for using pre-recorded waveforms
        Use _is_ref_mode(test_id) to check if a test should use reference waveforms
        Use _get_source(ch, test_id) to get "CH<n>" or "REF<n>" depending on mode
    """
    
    def __init__(self, instrument_manager):
        """
        Initialize the engine with access to instruments.
        
        Args:
            instrument_manager: InstrumentManager instance with scope/smu access
        """
        self.inst = instrument_manager
        self.test_points: List[TestPoint] = []
        self.running = False
        self.output_dir = None
        self.reference_config: Optional[ReferenceConfig] = None  # Reference mode config
        
        # Callbacks - set by main application
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[float, str], None]] = None
        self.on_test_start: Optional[Callable[[TestPoint], None]] = None
        self.on_test_complete: Optional[Callable[[TestPoint], None]] = None
        self.on_screenshot: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[int, int], None]] = None
    
    def log(self, message: str):
        """Log a message to the application log"""
        if self.on_log:
            self.on_log(message)
    
    def progress(self, percentage: float, message: str):
        """Update progress indicator"""
        if self.on_progress:
            self.on_progress(percentage, message)

    def _is_ref_mode(self, test_id: int) -> bool:
        """Check if this test should use reference waveforms"""
        if self.reference_config and self.reference_config.enabled:
            return self.reference_config.applies_to_test(test_id)
        return False

    def _get_source(self, ch: int, test_id: int = 0) -> str:
        """Get the measurement source - either CH or REF depending on mode"""
        if self._is_ref_mode(test_id):
            return f"REF{ch}"
        return f"CH{ch}"
    
    def generate_test_points(self, config: Dict[str, Any]) -> List[TestPoint]:
        """
        Generate the list of test points from configuration.
        
        CRITICAL: This method is called when the user SELECTS the test suite in
        the UI (clicks the test suite button), NOT when they click "Run". This is
        how Tek PTA populates the test table before execution.
        
        You MUST:
        1. Create TestPoint objects with test_id, name, nominal_value, unit, limits
        2. Store them in self.test_points
        3. Return the list
        
        If this method is not implemented or returns empty, the UI will show an
        empty test table and nothing will happen when clicked.
        
        Args:
            config: Configuration dictionary from the test suite (may be None)
            
        Returns:
            List of TestPoint objects (also stored in self.test_points)
        """
        raise NotImplementedError("Subclass must implement generate_test_points()")
    
    def setup_instruments(self, config: Dict[str, Any]) -> bool:
        """
        Configure instruments before running tests.
        
        Override this to set up oscilloscope, SMU, etc.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if setup successful, False otherwise
        """
        raise NotImplementedError("Subclass must implement setup_instruments()")
    
    def run_single_test(self, test_point: TestPoint, config: Dict[str, Any]) -> TestPoint:
        """
        Execute a single test point.
        
        Override this to implement your measurement logic.
        
        Args:
            test_point: The test point to execute
            config: Configuration dictionary
            
        Returns:
            Updated TestPoint with results
        """
        raise NotImplementedError("Subclass must implement run_single_test()")
    
    def cleanup(self):
        """
        Cleanup after test run.
        
        Override to reset instruments, close connections, etc.
        """
        pass
    
    def run(self, config: Dict[str, Any]):
        """
        Main test execution loop.
        
        This default implementation handles the standard flow:
        1. Generate test points
        2. Setup instruments
        3. Run each test point
        4. Cleanup
        5. Report completion
        
        Override if you need different flow control.
        """
        self.running = True
        self.test_points = self.generate_test_points(config)
        
        if not self.setup_instruments(config):
            self.log("ERROR: Instrument setup failed")
            if self.on_complete:
                self.on_complete(0, len(self.test_points))
            return
        
        pass_count = 0
        fail_count = 0
        total = len([tp for tp in self.test_points if tp.enabled])
        
        for i, tp in enumerate(self.test_points):
            if not self.running:
                self.log("Test stopped by user")
                break
            
            if not tp.enabled:
                tp.status = TestStatus.SKIPPED
                continue
            
            tp.status = TestStatus.RUNNING
            if self.on_test_start:
                self.on_test_start(tp)
            
            self.progress((i / total) * 100, f"Testing: {tp.name}")
            
            try:
                tp = self.run_single_test(tp, config)
                
                if tp.status == TestStatus.PASS:
                    pass_count += 1
                else:
                    fail_count += 1
                    
            except Exception as e:
                tp.status = TestStatus.ERROR
                tp.extra_data['error'] = str(e)
                fail_count += 1
                self.log(f"ERROR: {tp.name} - {e}")
            
            if self.on_test_complete:
                self.on_test_complete(tp)
        
        self.cleanup()
        self.progress(100, "Complete")
        
        if self.on_complete:
            self.on_complete(pass_count, fail_count)
    
    def stop(self):
        """Signal the test to stop"""
        self.running = False


# Helper functions for plugin authors

def format_frequency(hz: float) -> str:
    """Format frequency value with appropriate unit"""
    if hz >= 1e9:
        return f"{hz/1e9:.3f} GHz"
    elif hz >= 1e6:
        return f"{hz/1e6:.3f} MHz"
    elif hz >= 1e3:
        return f"{hz/1e3:.3f} kHz"
    else:
        return f"{hz:.3f} Hz"


def format_voltage(v: float) -> str:
    """Format voltage value with appropriate unit"""
    if abs(v) >= 1:
        return f"{v:.3f} V"
    elif abs(v) >= 1e-3:
        return f"{v*1e3:.3f} mV"
    else:
        return f"{v*1e6:.3f} µV"


def format_current(a: float) -> str:
    """Format current value with appropriate unit"""
    if abs(a) >= 1:
        return f"{a:.3f} A"
    elif abs(a) >= 1e-3:
        return f"{a*1e3:.3f} mA"
    elif abs(a) >= 1e-6:
        return f"{a*1e6:.3f} µA"
    else:
        return f"{a*1e9:.3f} nA"


def format_time(s: float) -> str:
    """Format time value with appropriate unit"""
    if s >= 1:
        return f"{s:.3f} s"
    elif s >= 1e-3:
        return f"{s*1e3:.3f} ms"
    elif s >= 1e-6:
        return f"{s*1e6:.3f} µs"
    elif s >= 1e-9:
        return f"{s*1e9:.3f} ns"
    else:
        return f"{s*1e12:.3f} ps"


def calculate_limits(nominal: float, tolerance_pct: float) -> tuple:
    """Calculate lower and upper limits from nominal and tolerance"""
    margin = nominal * (tolerance_pct / 100)
    return (nominal - margin, nominal + margin)


def check_pass_fail(measured: float, nominal: float, tolerance_pct: float) -> tuple:
    """
    Check if measured value is within tolerance of nominal.
    
    Returns:
        (passed: bool, error_pct: float)
    """
    if nominal == 0:
        error_pct = 0 if measured == 0 else float('inf')
        passed = abs(measured) < tolerance_pct / 100
    else:
        error_pct = ((measured - nominal) / nominal) * 100
        passed = abs(error_pct) <= tolerance_pct
    
    return (passed, error_pct)
