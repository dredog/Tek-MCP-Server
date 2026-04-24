#!/usr/bin/env python3
"""
Tek PTA Example Test Suites
===========================

This file contains the working test suites extracted from tek_pta.py.
These demonstrate the plugin system and serve as templates for creating
your own test suites.

These tests use the built-in test engines in tek_pta.py:
- "afg_freq" -> AFGFrequencyTestEngine
- "led_current" -> LEDCurrentTestEngine  
- "spectrum_scan" -> SpectrumScannerEngine

To create your own test suites:
1. Copy this file as a starting point
2. Modify the TestSuitePlugin definitions
3. Place in test_suites/ folder or import via Browse button
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any

# =============================================================================
# TEST SUITE PLUGIN DEFINITION
# =============================================================================

@dataclass
class TestSuitePlugin:
    """
    Definition of a test suite that can be loaded by Tek PTA.
    
    Attributes:
        name: Display name shown in the test suite selector
        description: Detailed description of what the test does
        test_type: Identifier that maps to a test engine 
                   (use built-in types or create custom engines)
        config: Default configuration parameters for this test
        required_instruments: List of required equipment (shown in UI)
        engine_class: Optional custom engine class (None = use built-in)
    """
    name: str
    description: str
    test_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Any = None


# =============================================================================
# AFG FREQUENCY SWEEP TEST
# =============================================================================

afg_frequency_sweep = TestSuitePlugin(
    name="AFG Frequency Sweep (1kHz - 25MHz)",
    description=(
        "Standard frequency sweep test using internal AFG. Outputs square waves at 20 "
        "logarithmically-spaced frequencies from 1kHz to 25MHz and measures frequency on CH1. "
        "Pass/fail tolerance: ±0.2%. Connect AFG OUT to CH1 with 50Ω BNC cable."
    ),
    test_type="afg_freq",
    config={
        "freq_start": 1000,
        "freq_stop": 25000000,
        "num_points": 20,
        "tolerance": 0.2,
        "afg_amp": 1.0,
        "spacing": "logarithmic"
    },
    required_instruments=["MSO/MDO Oscilloscope with AFG"],
)


# =============================================================================
# LED CURRENT TEST
# =============================================================================

led_current_test = TestSuitePlugin(
    name="Current Shunt Test with SMU as source",
    description=(
        "Measures current using 2450 SMU and oscilloscope with shunt resistor. "
        "Circuit: SMU+ → 470Ω → LED → 10Ω shunt → SMU-. "
        "Scope reads voltage across shunt; SCALERATio converts to amps. "
        "Passive probe or differential probe or TICP across shunt."
    ),
    test_type="led_current",
    config={
        "voltages": [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        "channel": 3,
        "shunt_resistance": 10,   # Ohms — drives CH<x>:SCALERATio (1/R)
    },
    required_instruments=["MSO/MDO Oscilloscope", "Keithley 2450 SMU"],
)


# =============================================================================
# SPECTRUM SCANNER TEST
# =============================================================================

spectrum_scanner = TestSuitePlugin(
    name="Spectrum Scanner (FM Radio default)",
    description=(
        "RF spectrum analyzer using SpectrumView. Default scans FM band (83-113 MHz) but range is "
        "configurable in the UI. Max frequency depends on oscilloscope bandwidth (1-10 GHz). "
        "Works with MSO 4/5/6 Series. Connect an antenna to the selected channel. "
        "Returns top 10 signals by amplitude with frequency and band identification."
    ),
    test_type="spectrum_scan",
    config={
        "start_mhz": 83,
        "stop_mhz": 113,
        "channel": 2
    },
    required_instruments=["MSO 4/5/6 Series with SpectrumView", "Antenna"],
)


# =============================================================================
# REGISTRATION FUNCTION (Required)
# =============================================================================

def register_suites():
    """
    Return list of test suites to register with Tek PTA.
    
    This function is called by the plugin discovery system when
    tek_pta.py loads plugins from the test_suites/ folder.
    
    Returns:
        List of TestSuitePlugin objects
    """
    return [
        afg_frequency_sweep,
        led_current_test,
        spectrum_scanner,
    ]


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Tek PTA Example Test Suites")
    print("=" * 70)
    
    suites = register_suites()
    print(f"\nFound {len(suites)} test suite(s):\n")
    
    for suite in suites:
        print(f"  • {suite.name}")
        print(f"    Type: {suite.test_type}")
        print(f"    Requires: {', '.join(suite.required_instruments)}")
        print()
    
    print("-" * 70)
    print("To use these test suites:")
    print("  1. Place this file in the test_suites/ folder next to tek_pta.py")
    print("  2. Run tek_pta.py - suites are discovered automatically")
    print("  3. Or use 'Import...' button to load from any location")
    print("-" * 70)
