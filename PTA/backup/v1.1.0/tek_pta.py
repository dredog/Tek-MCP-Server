#!/usr/bin/env python3
"""
==============================================================================
Tek PTA - Production Test Assistant
Version 1.0.1
==============================================================================

Tek PTA is free AE-ware from Tektronix, developed by Tektronix Application 
Engineers with decades of knowledge of how to control Tektronix instruments.

Features:
- AFG Frequency Sweep Test with auto-scaling
- LED Current Test (SMU + Scope current comparison)
- Spectrum Scanner (RF signal detection)
- Reference Waveform loading (WFM/ISF/CSV to REF channels)
- Professional PDF reports with screenshots
- SCPI command logging
- Plugin system for custom test suites

Contact: Andre Asbury (andre.asbury@tektronix.com)

Requirements: pip install pyvisa pyvisa-py Pillow reportlab matplotlib
==============================================================================
"""

__version__ = "1.0.1"
__last_modified__ = "2026-02-03"
__author__ = "Tektronix Application Engineers"

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import threading
import queue
import time
import math
import datetime
import os
import json
from pathlib import Path
import importlib.util
import importlib.machinery
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any, Callable
from enum import Enum

try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for saving to file
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# =============================================================================
# CONSTANTS AND DATA CLASSES
# =============================================================================

class TekColors:
    TEK_BLUE = "#00629B"
    TEK_CYAN = "#00A3E0"
    TEK_DARK = "#003B5C"
    BG_DARK = "#1E2A38"
    BG_MEDIUM = "#2C3E50"
    BG_LIGHT = "#34495E"
    BG_CARD = "#2D4152"
    BG_PANEL = "#243342"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#BDC3C7"
    TEXT_DIM = "#7F8C8D"
    TEXT_ACCENT = "#00A3E0"
    STATUS_PASS = "#2ECC71"
    STATUS_FAIL = "#E74C3C"
    STATUS_RUNNING = "#F39C12"
    STATUS_ERROR = "#F1C40F"    # Yellow for errors
    STATUS_NOT_RUN = "#95A5A6"
    BORDER = "#4A6278"
    BUTTON_HOVER = "#00B4D8"
    # SCPI log colors
    SCPI_CMD = "#87CEEB"      # Light blue for commands
    SCPI_QUERY = "#98FB98"    # Light green for queries
    SCPI_RESPONSE = "#DDA0DD" # Plum for responses


class TekFonts:
    TITLE = ("Segoe UI", 18, "bold")
    HEADER = ("Segoe UI", 13, "bold")
    SUBHEADER = ("Segoe UI", 11, "bold")
    NORMAL = ("Segoe UI", 10)
    SMALL = ("Segoe UI", 9)
    MONO = ("Consolas", 10)
    BUTTON = ("Segoe UI", 10, "bold")
    STATUS = ("Segoe UI", 16, "bold")


# Available PLL Bandwidth Options for Clock Recovery (Eye Diagram Test)
PLL_OPTIONS = {
    # PLL Name: (nominal_rate_bps, bandwidth_hz, description)
    "DISPLAYPORT_RBR": (1.62e9, 1.0e6, "DisplayPort RBR (1.62 Gbps)"),
    "DISPLAYPORT_HBR": (2.7e9, 1.0e6, "DisplayPort HBR (2.7 Gbps)"),
    "DISPLAYPORT_HBR2": (5.4e9, 1.0e6, "DisplayPort HBR2 (5.4 Gbps)"),
    "SATA_GEN1": (1.5e9, 1.5e6, "SATA Gen1 (1.5 Gbps)"),
    "SATA_GEN2": (3.0e9, 1.5e6, "SATA Gen2 (3.0 Gbps)"),
    "SATA_GEN3": (6.0e9, 1.5e6, "SATA Gen3 (6.0 Gbps)"),
    "PCIE_GEN1": (2.5e9, 1.5e6, "PCIe Gen1 (2.5 Gbps)"),
    "PCIE_GEN2": (5.0e9, 1.5e6, "PCIe Gen2 (5.0 Gbps)"),
    "PCIE_GEN3": (8.0e9, 1.5e6, "PCIe Gen3 (8.0 Gbps)"),
    "USB2_HS": (480e6, 300e3, "USB 2.0 High Speed (480 Mbps)"),
    "USB3_GEN1": (5.0e9, 2.0e6, "USB 3.0 Gen1 (5.0 Gbps)"),
    "CUSTOM_1G": (1.0e9, 500e3, "Custom 1 Gbps"),
    "CUSTOM_2G": (2.0e9, 1.0e6, "Custom 2 Gbps"),
    "CUSTOM_5G": (5.0e9, 2.0e6, "Custom 5 Gbps"),
    "CUSTOM_10G": (10.0e9, 5.0e6, "Custom 10 Gbps"),
}


# =============================================================================
# TEST SETUP DIAGRAM GENERATORS
# =============================================================================

def generate_led_test_setup_diagram(output_path: Path) -> str:
    """
    Generate a block diagram for the LED Current Test setup.
    Returns path to saved image file.
    """
    if not MATPLOTLIB_AVAILABLE:
        return ""
    
    try:
        fig, ax = plt.subplots(1, 1, figsize=(10, 6), facecolor='#1E2A38')
        ax.set_facecolor('#1E2A38')
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 60)
        ax.axis('off')
        
        # Title
        ax.text(50, 57, "LED Current Test Setup", fontsize=16, fontweight='bold',
               ha='center', color='white')
        
        # SMU Block
        smu_rect = plt.Rectangle((5, 25), 18, 20, linewidth=2, edgecolor='#00A3E0',
                                  facecolor='#2C3E50', zorder=2)
        ax.add_patch(smu_rect)
        ax.text(14, 37, "Keithley", fontsize=10, ha='center', color='white', fontweight='bold')
        ax.text(14, 33, "2450 SMU", fontsize=10, ha='center', color='white', fontweight='bold')
        ax.text(14, 28, "HI/LO", fontsize=9, ha='center', color='#BDC3C7')
        
        # 470Ω Resistor
        ax.text(35, 44, "470Ω", fontsize=10, ha='center', color='#F39C12', fontweight='bold')
        # Draw resistor zigzag
        res_x = [28, 30, 31, 33, 35, 37, 39, 41, 42]
        res_y = [40, 40, 42, 38, 42, 38, 42, 40, 40]
        ax.plot(res_x, res_y, color='#F39C12', linewidth=2, zorder=3)
        
        # LED (triangle with bar)
        led_x = [50, 55, 50, 50]
        led_y = [38, 40, 42, 38]
        ax.fill(led_x, led_y, color='#E74C3C', zorder=3)
        ax.plot([55, 55], [37, 43], color='#E74C3C', linewidth=2, zorder=3)
        ax.text(52.5, 33, "LED", fontsize=10, ha='center', color='#E74C3C', fontweight='bold')
        
        # 10Ω Shunt Resistor
        ax.text(68, 44, "10Ω", fontsize=10, ha='center', color='#2ECC71', fontweight='bold')
        ax.text(68, 48, "(Shunt)", fontsize=9, ha='center', color='#2ECC71')
        # Draw resistor zigzag
        res2_x = [60, 62, 63, 65, 67, 69, 71, 73, 76]
        res2_y = [40, 40, 42, 38, 42, 38, 42, 40, 40]
        ax.plot(res2_x, res2_y, color='#2ECC71', linewidth=2, zorder=3)
        
        # Connection lines (circuit path)
        ax.plot([23, 28], [40, 40], color='white', linewidth=2, zorder=1)  # SMU HI to R1
        ax.plot([42, 50], [40, 40], color='white', linewidth=2, zorder=1)  # R1 to LED
        ax.plot([55, 60], [40, 40], color='white', linewidth=2, zorder=1)  # LED to shunt
        ax.plot([76, 85], [40, 40], color='white', linewidth=2, zorder=1)  # Shunt to return
        ax.plot([85, 85], [40, 20], color='white', linewidth=2, zorder=1)  # Down
        ax.plot([85, 23], [20, 20], color='white', linewidth=2, zorder=1)  # Back to SMU LO
        ax.plot([23, 23], [20, 25], color='white', linewidth=2, zorder=1)  # Up to SMU
        
        # Oscilloscope Block
        scope_rect = plt.Rectangle((58, 5), 22, 15, linewidth=2, edgecolor='#00A3E0',
                                    facecolor='#2C3E50', zorder=2)
        ax.add_patch(scope_rect)
        ax.text(69, 14, "MSO5/6", fontsize=10, ha='center', color='white', fontweight='bold')
        ax.text(69, 10, "Oscilloscope", fontsize=9, ha='center', color='white')
        ax.text(69, 6, "CH3", fontsize=9, ha='center', color='#00A3E0')
        
        # Probe connections (to shunt resistor)
        ax.plot([64, 64], [20, 38], color='#87CEEB', linewidth=1.5, linestyle='--', zorder=1)
        ax.plot([74, 74], [20, 42], color='#87CEEB', linewidth=1.5, linestyle='--', zorder=1)
        ax.text(69, 24, "Probe", fontsize=9, ha='center', color='#87CEEB')
        
        # Labels
        ax.text(23, 43, "HI", fontsize=9, ha='center', color='#BDC3C7')
        ax.text(23, 17, "LO", fontsize=9, ha='center', color='#BDC3C7')
        
        # Notes
        ax.text(5, 8, "V_out: 2V to 5V", fontsize=9, color='#BDC3C7')
        ax.text(5, 4, "Current Limit: 20mA", fontsize=9, color='#BDC3C7')
        ax.text(30, 8, "I = V_shunt / 10Ω", fontsize=9, color='#2ECC71')
        ax.text(30, 4, "Scope: CH3 w/ 10Ω ext attn", fontsize=9, color='#87CEEB')
        
        # Formula
        ax.text(50, 52, "Current Measurement: I_LED = V_scope / R_shunt (10Ω)",
               fontsize=10, ha='center', color='#BDC3C7', style='italic')
        
        plt.tight_layout()
        plt.savefig(output_path, facecolor='#1E2A38', dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return str(output_path)
    except Exception as e:
        print(f"Error generating LED diagram: {e}")
        return ""


def generate_spectrum_test_setup_diagram(output_path: Path) -> str:
    """
    Generate a block diagram for the Spectrum Scanner Test setup.
    Returns path to saved image file.
    """
    if not MATPLOTLIB_AVAILABLE:
        return ""
    
    try:
        fig, ax = plt.subplots(1, 1, figsize=(10, 5), facecolor='#1E2A38')
        ax.set_facecolor('#1E2A38')
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 50)
        ax.axis('off')
        
        # Title
        ax.text(50, 47, "Spectrum Scanner Test Setup", fontsize=16, fontweight='bold',
               ha='center', color='white')
        
        # Antenna
        ax.plot([20, 20], [35, 25], color='#F39C12', linewidth=3, zorder=3)
        ax.plot([15, 20, 25], [35, 42, 35], color='#F39C12', linewidth=3, zorder=3)
        ax.text(20, 20, "Antenna", fontsize=10, ha='center', color='#F39C12', fontweight='bold')
        
        # BNC Cable
        ax.plot([20, 50], [25, 25], color='white', linewidth=2, linestyle='-', zorder=1)
        ax.text(35, 28, "50Ω Coax Cable", fontsize=9, ha='center', color='#BDC3C7')
        
        # Oscilloscope Block
        scope_rect = plt.Rectangle((50, 15), 30, 20, linewidth=2, edgecolor='#00A3E0',
                                    facecolor='#2C3E50', zorder=2)
        ax.add_patch(scope_rect)
        ax.text(65, 28, "MSO5/6B", fontsize=11, ha='center', color='white', fontweight='bold')
        ax.text(65, 23, "SpectrumView", fontsize=10, ha='center', color='#00A3E0')
        ax.text(65, 18, "CH2 (50Ω)", fontsize=9, ha='center', color='#BDC3C7')
        
        # Notes
        ax.text(5, 10, "• 50Ω termination for antenna/coax", fontsize=9, color='#BDC3C7')
        ax.text(5, 6, "• SV Average: 256 acq", fontsize=9, color='#BDC3C7')
        ax.text(5, 2, "• 1 GHz capture bandwidth", fontsize=9, color='#BDC3C7')
        
        ax.text(50, 6, "Output: Top 10 peaks sorted by amplitude (dBm)", fontsize=10,
               ha='left', color='#2ECC71')
        
        plt.tight_layout()
        plt.savefig(output_path, facecolor='#1E2A38', dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return str(output_path)
    except Exception as e:
        print(f"Error generating spectrum diagram: {e}")
        return ""


def generate_awg_test_setup_diagram(output_path: Path) -> str:
    """
    Generate a block diagram for the AWG Pulse Timing Test setup.
    Returns path to saved image file.
    """
    if not MATPLOTLIB_AVAILABLE:
        return ""
    
    try:
        # Larger figure for better readability
        fig, ax = plt.subplots(1, 1, figsize=(14, 7), facecolor='#1E2A38')
        ax.set_facecolor('#1E2A38')
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 60)
        ax.axis('off')
        
        # Title - larger font
        ax.text(50, 57, "AWG70002B Pulse Timing Test Setup", fontsize=20, fontweight='bold',
               ha='center', color='white')
        
        # AWG Block - positioned left (x: 8-30, y: 25-47)
        awg_left, awg_bottom, awg_width, awg_height = 8, 25, 22, 22
        awg_rect = plt.Rectangle((awg_left, awg_bottom), awg_width, awg_height, 
                                  linewidth=2, edgecolor='#F39C12', facecolor='#2C3E50', zorder=2)
        ax.add_patch(awg_rect)
        ax.text(awg_left + awg_width/2, 42, "AWG70002B", fontsize=14, ha='center', color='white', fontweight='bold')
        ax.text(awg_left + awg_width/2, 37, "100 kHz Pulse", fontsize=12, ha='center', color='#F39C12')
        
        # Oscilloscope Block - positioned right (x: 62-90, y: 23-49)
        scope_left, scope_bottom, scope_width, scope_height = 62, 23, 28, 26
        scope_rect = plt.Rectangle((scope_left, scope_bottom), scope_width, scope_height,
                                    linewidth=2, edgecolor='#00A3E0', facecolor='#2C3E50', zorder=2)
        ax.add_patch(scope_rect)
        ax.text(scope_left + scope_width/2, 44, "MSO5/6B", fontsize=14, ha='center', color='white', fontweight='bold')
        ax.text(scope_left + scope_width/2, 27, "6.25 GS/s", fontsize=12, ha='center', color='#00A3E0')
        
        # Cable Y positions
        cable1_y = 40  # Upper cable
        cable2_y = 32  # Lower cable
        
        # AWG right edge, Scope left edge
        awg_right = awg_left + awg_width
        
        # Connection cables - lines go from AWG edge to Scope edge
        # Upper cable: AWG CH1 → Scope CH1
        ax.plot([awg_right, scope_left], [cable1_y, cable1_y], color='white', lw=2.5, zorder=1)
        ax.plot([scope_left-1, scope_left], [cable1_y, cable1_y], color='white', lw=2.5, zorder=1)  # Arrow tip
        ax.annotate('', xy=(scope_left, cable1_y), xytext=(scope_left-3, cable1_y),
                   arrowprops=dict(arrowstyle='->', color='white', lw=2.5))
        
        # Lower cable: AWG CH2 → Scope CH3  
        ax.plot([awg_right, scope_left], [cable2_y, cable2_y], color='white', lw=2.5, zorder=1)
        ax.annotate('', xy=(scope_left, cable2_y), xytext=(scope_left-3, cable2_y),
                   arrowprops=dict(arrowstyle='->', color='white', lw=2.5))
        
        # Channel labels ABOVE the cable lines (outside instruments)
        ax.text(awg_right + 2, cable1_y + 2.5, "CH1+", fontsize=13, ha='left', color='#F39C12', fontweight='bold')
        ax.text(awg_right + 2, cable2_y + 2.5, "CH2+", fontsize=13, ha='left', color='#F39C12', fontweight='bold')
        ax.text(scope_left - 2, cable1_y + 2.5, "CH1", fontsize=13, ha='right', color='#00A3E0', fontweight='bold')
        ax.text(scope_left - 2, cable2_y + 2.5, "CH3", fontsize=13, ha='right', color='#00A3E0', fontweight='bold')
        
        # Cable type labels centered above cables
        ax.text(50, cable1_y + 2.5, "50Ω Coax", fontsize=11, ha='center', color='#BDC3C7')
        ax.text(50, cable2_y - 3, "50Ω Coax", fontsize=11, ha='center', color='#BDC3C7')
        
        # 50Ω termination INSIDE the scope box (next to channel indicators)
        ax.text(scope_left + scope_width - 3, cable1_y, "50Ω", fontsize=11, ha='right', color='#BDC3C7')
        ax.text(scope_left + scope_width - 3, cable2_y, "50Ω", fontsize=11, ha='right', color='#BDC3C7')
        
        # Notes section - larger fonts
        ax.text(8, 16, "Connections:", fontsize=13, color='white', fontweight='bold')
        ax.text(8, 11, "• AWG CH1+ → Scope CH1 (single-ended, 50Ω)", fontsize=12, color='#BDC3C7')
        ax.text(8, 6, "• AWG CH2+ → Scope CH3 (single-ended, 50Ω)", fontsize=12, color='#BDC3C7')
        ax.text(8, 1, "• CH2 signal delayed 2 µs from CH1", fontsize=12, color='#BDC3C7')
        
        ax.text(62, 11, "Measurements:", fontsize=13, color='white', fontweight='bold')
        ax.text(62, 6, "Delay, Rise Time, Fall Time", fontsize=12, color='#2ECC71')
        ax.text(62, 1, "100 samples per measurement", fontsize=12, color='#2ECC71')
        
        plt.tight_layout()
        plt.savefig(output_path, facecolor='#1E2A38', dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return str(output_path)
    except Exception as e:
        print(f"Error generating AWG diagram: {e}")
        return ""


def generate_afg_test_setup_diagram(output_path: Path, channel: int = 1) -> str:
    """
    Generate a block diagram for the AFG Frequency Sweep Test setup.
    The MSO4/5/6 has a built-in AFG - cable goes from AFG output (back) to channel input (front).
    
    Args:
        output_path: Path to save the diagram image
        channel: The scope channel number to connect to (default 1)
    
    Returns path to saved image file.
    """
    if not MATPLOTLIB_AVAILABLE:
        return ""
    
    try:
        # Larger figure for better readability
        fig, ax = plt.subplots(1, 1, figsize=(12, 7), facecolor='#1E2A38')
        ax.set_facecolor('#1E2A38')
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 60)
        ax.axis('off')
        
        # Title - larger font
        ax.text(50, 57, "AFG Frequency Sweep Test Setup", fontsize=18, fontweight='bold',
               ha='center', color='white')
        ax.text(50, 53, "(MSO4/5/6 Built-in AFG)", fontsize=12, ha='center', color='#BDC3C7')
        
        # Single MSO Block - representing both front and back
        scope_rect = plt.Rectangle((25, 20), 50, 28, linewidth=3, edgecolor='#00A3E0',
                                    facecolor='#2C3E50', zorder=2)
        ax.add_patch(scope_rect)
        ax.text(50, 42, "MSO4/5/6 Series", fontsize=14, ha='center', color='white', fontweight='bold')
        
        # Dividing line between front and back
        ax.plot([25, 75], [34, 34], color='#4A5568', linewidth=1, linestyle='--', zorder=3)
        ax.text(50, 36, "FRONT", fontsize=10, ha='center', color='#BDC3C7')
        ax.text(50, 31, "BACK", fontsize=10, ha='center', color='#BDC3C7')
        
        # Front panel - Channel inputs
        ax.text(35, 38, f"CH{channel}", fontsize=12, ha='center', color='#00A3E0', fontweight='bold')
        ax.text(35, 24.5, "50Ω", fontsize=11, ha='center', color='#BDC3C7')
        
        # Back panel - AFG output  
        ax.text(65, 27, "AFG OUT", fontsize=12, ha='center', color='#F39C12', fontweight='bold')
        
        # Draw cable going AROUND the scope (from back to front)
        # Path: AFG OUT -> down -> around right -> up -> around left -> to CH input
        cable_color = 'white'
        cable_width = 2.5
        
        # Start from AFG OUT, go down
        ax.plot([65, 65], [20, 12], color=cable_color, linewidth=cable_width, zorder=1)
        # Go left under the scope
        ax.plot([65, 35], [12, 12], color=cable_color, linewidth=cable_width, zorder=1)
        # Go up to CH input level
        ax.plot([35, 35], [12, 20], color=cable_color, linewidth=cable_width, zorder=1)
        # Arrow pointing up to CH input
        ax.annotate('', xy=(35, 20), xytext=(35, 14),
                   arrowprops=dict(arrowstyle='->', color=cable_color, lw=cable_width))
        
        # Cable label
        ax.text(50, 9, "50Ω BNC Coax Cable", fontsize=12, ha='center', color='#BDC3C7', fontweight='bold')
        
        # Notes section - larger fonts
        ax.text(5, 5, "• AFG OUTPUT (rear) → CH input (front)", fontsize=11, color='#BDC3C7')
        ax.text(5, 1, "• Both AFG output and channel set to 50Ω", fontsize=11, color='#BDC3C7')
        
        ax.text(60, 5, "Measurement: FREQUENCY", fontsize=11, color='#2ECC71', fontweight='bold')
        ax.text(60, 1, "Sweep with configurable tolerance", fontsize=10, color='#2ECC71')
        
        plt.tight_layout()
        plt.savefig(output_path, facecolor='#1E2A38', dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return str(output_path)
    except Exception as e:
        print(f"Error generating AFG diagram: {e}")
        return ""


def generate_eye_diagram_setup_diagram(output_path: Path) -> str:
    """
    Generate a compact block diagram for the Eye Diagram Test setup.
    Returns path to saved image file.
    """
    if not MATPLOTLIB_AVAILABLE:
        return ""
    
    try:
        # Compact size to fit in dialog with buttons visible
        fig, ax = plt.subplots(1, 1, figsize=(7, 2.8), facecolor='#1E2A38')
        ax.set_facecolor('#1E2A38')
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 40)
        ax.axis('off')
        
        # Title
        ax.text(50, 37, "Eye Diagram Test Setup", fontsize=12, fontweight='bold',
               ha='center', color='white')
        
        # DUT Block
        dut_rect = plt.Rectangle((5, 15), 16, 16, linewidth=2, edgecolor='#00A3E0',
                                  facecolor='#2C3E50', zorder=2)
        ax.add_patch(dut_rect)
        ax.text(13, 25, "DUT", fontsize=9, ha='center', color='white', fontweight='bold')
        ax.text(13, 20, "Data Out", fontsize=7, ha='center', color='#BDC3C7')
        
        # SMA Cable arrow
        ax.annotate('', xy=(38, 23), xytext=(21, 23),
                   arrowprops=dict(arrowstyle='->', color='#F39C12', lw=2))
        ax.text(29, 27, "SMA", fontsize=7, ha='center', color='#F39C12', fontweight='bold')
        
        # SMA-BNC Adapter
        adapter_rect = plt.Rectangle((38, 18), 10, 10, linewidth=2, edgecolor='#9B59B6',
                                     facecolor='#2C3E50', zorder=2)
        ax.add_patch(adapter_rect)
        ax.text(43, 24, "SMA", fontsize=6, ha='center', color='white')
        ax.text(43, 20, "BNC", fontsize=6, ha='center', color='white')
        
        # Connection to scope
        ax.annotate('', xy=(62, 23), xytext=(48, 23),
                   arrowprops=dict(arrowstyle='->', color='#F39C12', lw=2))
        
        # Oscilloscope Block
        scope_rect = plt.Rectangle((62, 12), 33, 22, linewidth=2, edgecolor='#00A3E0',
                                   facecolor='#2C3E50', zorder=2)
        ax.add_patch(scope_rect)
        ax.text(78, 29, "MSO Oscilloscope", fontsize=9, ha='center', color='white', fontweight='bold')
        ax.text(78, 23, "CH1 • 50Ω", fontsize=8, ha='center', color='#2ECC71', fontweight='bold')
        ax.text(78, 17, "Eye: Height & Width", fontsize=7, ha='center', color='#BDC3C7')
        
        # Signal info at bottom
        ax.text(50, 5, "Signal: ~650 mVpp, ~350 mV offset  •  Output: Eye statistics (min/max/mean/σ)", 
               fontsize=7, ha='center', color='#BDC3C7')
        
        plt.tight_layout()
        diagram_path = output_path / "eye_diagram_setup.png"
        plt.savefig(diagram_path, dpi=100, facecolor='#1E2A38', 
                   edgecolor='none', bbox_inches='tight')
        plt.close(fig)
        return str(diagram_path)
        
    except Exception as e:
        print(f"Failed to generate eye diagram setup: {e}")
        return ""


def format_si(value, unit="", precision=3):
    """Format a numeric value with SI prefix for human-readable display.
    
    Examples:
        format_si(2e-6, "s")    -> "2.000 µs"
        format_si(1.61e-10, "s") -> "161.000 ps"
        format_si(24e6, "Hz")   -> "24.000 MHz"
        format_si(0.005, "V")   -> "5.000 mV"
        format_si(1500, "")     -> "1.500 k"
    """
    if value is None:
        return "---"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return str(value)
    
    # Handle invalid/infinity values  
    if math.isnan(v) or math.isinf(v) or abs(v) > 1e30:
        return "Invalid"
    
    if v == 0:
        return f"0 {unit}".strip()
    
    SI_PREFIXES = [
        (1e12,  "T"),
        (1e9,   "G"),
        (1e6,   "M"),
        (1e3,   "k"),
        (1,     ""),
        (1e-3,  "m"),
        (1e-6,  "µ"),
        (1e-9,  "n"),
        (1e-12, "p"),
        (1e-15, "f"),
    ]
    
    abs_v = abs(v)
    for scale, prefix in SI_PREFIXES:
        if abs_v >= scale * 0.999:  # 0.999 to handle floating point edge cases
            scaled = v / scale
            return f"{scaled:.{precision}f} {prefix}{unit}".strip()
    
    # Smaller than femto - use scientific notation
    return f"{v:.{precision}e} {unit}".strip()


class TestStatus(Enum):
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "Skipped"


@dataclass
class InstrumentInfo:
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    firmware_version: str = ""
    visa_address: str = ""
    instrument_type: str = "Unknown"
    is_connected: bool = False


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
class TestSuite:
    name: str
    description: str
    test_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)  # e.g., ["Oscilloscope", "SMU"]
    setup_diagram_path: str = ""  # Path to test setup diagram image
    reference_config: ReferenceConfig = field(default_factory=ReferenceConfig)  # Reference waveform config
    source_file: str = ""  # Path to the plugin file that defined this suite
    modified_time: str = ""  # Last modified timestamp (ISO format or display string)


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


# =============================================================================
# PLUGIN DISCOVERY SYSTEM
# =============================================================================

def get_plugin_directories():
    """
    Get list of directories to search for test suite plugins.
    
    Sources (in order of priority):
    1. TEK_PTA_PLUGIN_DIRS environment variable (semicolon-separated paths)
    2. tek_pta_config.json file in the same folder as tek_pta.py
    3. Default: test_suites/ folder next to tek_pta.py
    
    Returns:
        List of Path objects
    """
    script_dir = Path(__file__).parent
    plugin_dirs = []
    
    # 1. Check environment variable (semicolon-separated on Windows)
    env_dirs = os.environ.get('TEK_PTA_PLUGIN_DIRS', '')
    if env_dirs:
        for dir_path in env_dirs.split(';'):
            dir_path = dir_path.strip()
            if dir_path:
                plugin_dirs.append(Path(dir_path))
    
    # 2. Check config file
    config_file = script_dir / "tek_pta_config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config_dirs = config.get('plugin_directories', [])
                for dir_path in config_dirs:
                    # Support ~ for home directory
                    expanded = os.path.expanduser(dir_path)
                    expanded = os.path.expandvars(expanded)  # Support %USERPROFILE% etc.
                    plugin_dirs.append(Path(expanded))
        except Exception as e:
            print(f"Warning: Failed to read config file: {e}")
    
    # 3. Always include default locations
    plugin_dirs.append(script_dir / "test_suites")
    
    return plugin_dirs


def discover_test_suite_plugins(plugin_dirs=None):
    """
    Discover and load test suite plugins from directories.
    
    Args:
        plugin_dirs: List of Path objects to search. If None, uses get_plugin_directories()
    
    Returns:
        (discovered_suites, loaded_engines) - List of TestSuite and dict of engines
    """
    if plugin_dirs is None:
        plugin_dirs = get_plugin_directories()
    
    discovered_suites = []
    loaded_engines = {}  # test_type -> engine_class
    
    for plugin_dir in plugin_dirs:
        if not plugin_dir.exists():
            continue
        
        for py_file in plugin_dir.glob("*.py"):
            # Skip __init__.py and private files
            if py_file.name.startswith("_"):
                continue
            
            # Skip the API file itself
            if py_file.name == "tek_pta_plugin_api.py":
                continue
            
            try:
                # Load the module
                module_name = f"tek_pta_plugin_{py_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    continue
                    
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Check for register_suites function
                if hasattr(module, 'register_suites'):
                    plugin_suites = module.register_suites()
                    
                    # Get file modification time
                    try:
                        mod_time = datetime.datetime.fromtimestamp(py_file.stat().st_mtime)
                        mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M")
                    except:
                        mod_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    for plugin in plugin_suites:
                        # Convert plugin to TestSuite
                        suite = TestSuite(
                            name=plugin.name,
                            description=plugin.description,
                            test_type=plugin.test_type,
                            config=plugin.config if hasattr(plugin, 'config') else {},
                            required_instruments=plugin.required_instruments if hasattr(plugin, 'required_instruments') else [],
                            source_file=str(py_file),
                            modified_time=mod_time_str,
                        )
                        discovered_suites.append(suite)
                        
                        # Store custom engine if provided
                        if hasattr(plugin, 'engine_class') and plugin.engine_class is not None:
                            loaded_engines[plugin.test_type] = plugin.engine_class
                        
                        print(f"Loaded plugin: {plugin.name} ({py_file.name})")
                        
            except Exception as e:
                print(f"Warning: Failed to load plugin {py_file}: {e}")
    
    return discovered_suites, loaded_engines


def import_plugin_file(file_path: Path) -> tuple:
    """
    Import a single plugin file.
    
    Args:
        file_path: Path to the .py file to import
    
    Returns:
        (suites, engines) tuple or ([], {}) on failure
    """
    if not file_path.exists() or not file_path.suffix == '.py':
        return [], {}
    
    try:
        module_name = f"tek_pta_plugin_imported_{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return [], {}
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        suites = []
        engines = {}
        
        # Get file modification time
        try:
            mod_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M")
        except:
            mod_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if hasattr(module, 'register_suites'):
            for plugin in module.register_suites():
                suite = TestSuite(
                    name=plugin.name,
                    description=plugin.description,
                    test_type=plugin.test_type,
                    config=plugin.config if hasattr(plugin, 'config') else {},
                    required_instruments=plugin.required_instruments if hasattr(plugin, 'required_instruments') else [],
                    source_file=str(file_path),
                    modified_time=mod_time_str,
                )
                suites.append(suite)
                
                if hasattr(plugin, 'engine_class') and plugin.engine_class is not None:
                    engines[plugin.test_type] = plugin.engine_class
        
        return suites, engines
        
    except Exception as e:
        print(f"Failed to import plugin {file_path}: {e}")
        return [], {}


# =============================================================================
# INSTRUMENT MANAGER
# =============================================================================

class InstrumentManager:
    def __init__(self):
        self.rm = None
        self.instruments: Dict[str, InstrumentInfo] = {}
        self.scope = None
        self.scope_info: Optional[InstrumentInfo] = None
        self.smu = None
        self.smu_info: Optional[InstrumentInfo] = None
        self.awg = None
        self.awg_info: Optional[InstrumentInfo] = None
        self.on_scpi_log = None  # Callback for SCPI logging: (type, message)
        self._init_visa()

    def _log_scpi(self, scpi_type: str, message: str):
        """Log SCPI command/query/response"""
        if self.on_scpi_log:
            self.on_scpi_log(scpi_type, message)

    def _init_visa(self):
        if not PYVISA_AVAILABLE:
            return
        try:
            self.rm = pyvisa.ResourceManager('@py')
        except Exception:
            try:
                self.rm = pyvisa.ResourceManager()
            except Exception:
                pass

    def _make_visa_address(self, ip: str) -> str:
        ip = ip.strip()
        if ip.startswith("TCPIP"):
            return ip
        return f"TCPIP0::{ip}::inst0::INSTR"

    def discover_instruments(self) -> List[InstrumentInfo]:
        discovered = []
        seen = set()
        if not self.rm:
            return discovered
        
        # First try standard VISA discovery
        try:
            resources = self.rm.list_resources()
            print(f"VISA resources found: {resources}")  # Debug
            for addr in resources:
                if "127.0.0.1" in addr or "localhost" in addr.lower():
                    continue
                try:
                    inst = self.rm.open_resource(addr)
                    inst.timeout = 5000
                    idn = inst.query("*IDN?").strip()
                    parts = idn.split(",")
                    serial = parts[2].strip() if len(parts) > 2 else f"UNK_{addr[-8:]}"
                    if serial in seen:
                        inst.close()
                        continue
                    seen.add(serial)
                    
                    # Check if we already have this instrument (preserve connection state)
                    if addr in self.instruments:
                        info = self.instruments[addr]
                    else:
                        info = InstrumentInfo(
                            manufacturer=parts[0].strip() if parts else "Unknown",
                            model=parts[1].strip() if len(parts) > 1 else "Unknown",
                            serial_number=serial,
                            firmware_version=parts[3].strip() if len(parts) > 3 else "",
                            visa_address=addr
                        )
                        model_up = info.model.upper()
                        # Detect oscilloscopes - including TekscopeSW (PC software)
                        if any(x in model_up for x in ['MSO', 'MDO', 'TDS', 'DPO', 'TEKSCOPE']):
                            info.instrument_type = "Oscilloscope"
                        elif any(x in model_up for x in ['2400', '2450', '2460', '2461', '2470']):
                            info.instrument_type = "SMU"
                        elif any(x in model_up for x in ['AFG', 'AWG']):
                            info.instrument_type = "Function Generator"
                        else:
                            info.instrument_type = "Instrument"
                        self.instruments[addr] = info
                    
                    # Check if this instrument is currently connected
                    if info.instrument_type == "Oscilloscope" and self.scope is not None:
                        if self.scope_info and self.scope_info.visa_address == addr:
                            info.is_connected = True
                    elif info.instrument_type == "SMU" and self.smu is not None:
                        if self.smu_info and self.smu_info.visa_address == addr:
                            info.is_connected = True
                    elif info.instrument_type == "Function Generator" and self.awg is not None:
                        if self.awg_info and self.awg_info.visa_address == addr:
                            info.is_connected = True
                    
                    discovered.append(info)
                    inst.close()
                except Exception as e:
                    print(f"Failed to query {addr}: {e}")  # Debug
        except Exception as e:
            print(f"VISA list_resources failed: {e}")  # Debug
        
        # Always scan link-local subnet for additional instruments
        link_local_found = self._scan_link_local(seen)
        discovered.extend(link_local_found)
        
        return discovered

    def _scan_link_local(self, seen: set) -> List[InstrumentInfo]:
        """Scan known link-local subnets for instruments.
        
        Uses parallel scanning with threading for speed. Scans only known
        subnets where Tektronix instruments are commonly found, but checks
        all hosts (1-254) in those subnets.
        
        Subnets can be customized in tek_pta_config.json under "scan_subnets".
        """
        import concurrent.futures
        
        discovered = []
        found_lock = threading.Lock()
        
        # Priority instruments - check these first (known IPs from your setup)
        priority_ips = [
            "169.254.10.36",    # MSO68B Linux default
            "169.254.113.94",   # MSO68B Windows default  
            "169.254.165.92",   # AWG70002B
            "169.254.111.28",   # Keithley 2450 SMU
        ]
        
        # Known subnets where Tektronix instruments have been found
        # 169.254.x.x link-local subnets
        link_local_subnets = [10, 111, 113, 165, 1, 0, 100, 200]
        
        # Also scan common static IP subnets (192.168.x.x)
        static_subnets_192 = [1, 0, 2, 10, 100]  # 192.168.1.x, 192.168.0.x, etc.
        
        # Check config file for customization
        script_dir = Path(__file__).parent
        config_file = script_dir / "tek_pta_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Custom priority IPs
                    user_priority = config.get('priority_instruments', [])
                    for ip in user_priority:
                        if ip not in priority_ips:
                            priority_ips.insert(0, ip)
                    # Custom subnets to scan
                    if 'scan_subnets_169' in config:
                        link_local_subnets = config['scan_subnets_169']
                    if 'scan_subnets_192' in config:
                        static_subnets_192 = config['scan_subnets_192']
            except Exception:
                pass
        
        # Localhost for TekscopeSW
        common_ips = ["127.0.0.1", "localhost"]
        
        def try_connect(ip: str) -> Optional[InstrumentInfo]:
            """Try to connect to a single IP address."""
            if ip in seen:
                return None
            visa_addr = self._make_visa_address(ip)
            try:
                inst = self.rm.open_resource(visa_addr)
                inst.timeout = 500  # Fast timeout for scanning
                inst.read_termination = '\n'
                inst.write_termination = '\n'
                idn = inst.query("*IDN?").strip()
                parts = idn.split(",")
                serial = parts[2].strip() if len(parts) > 2 else f"UNK_{ip}"
                inst.close()
                
                with found_lock:
                    if serial in seen:
                        return None
                    seen.add(serial)
                
                # Check if we already have this instrument
                if visa_addr in self.instruments:
                    info = self.instruments[visa_addr]
                else:
                    info = InstrumentInfo(
                        manufacturer=parts[0].strip() if parts else "Unknown",
                        model=parts[1].strip() if len(parts) > 1 else "Unknown",
                        serial_number=serial,
                        firmware_version=parts[3].strip() if len(parts) > 3 else "",
                        visa_address=visa_addr
                    )
                    model_up = info.model.upper()
                    if any(x in model_up for x in ['MSO', 'MDO', 'TDS', 'DPO', 'TEKSCOPE']):
                        info.instrument_type = "Oscilloscope"
                    elif any(x in model_up for x in ['2400', '2450', '2460', '2461', '2470', '2600', '2651']):
                        info.instrument_type = "SMU"
                    elif any(x in model_up for x in ['AFG', 'AWG']):
                        info.instrument_type = "Function Generator"
                    else:
                        info.instrument_type = "Instrument"
                    self.instruments[visa_addr] = info
                
                # Check connection state
                if info.instrument_type == "Oscilloscope" and self.scope is not None:
                    if self.scope_info and self.scope_info.visa_address == visa_addr:
                        info.is_connected = True
                elif info.instrument_type == "SMU" and self.smu is not None:
                    if self.smu_info and self.smu_info.visa_address == visa_addr:
                        info.is_connected = True
                elif info.instrument_type == "Function Generator" and self.awg is not None:
                    if self.awg_info and self.awg_info.visa_address == visa_addr:
                        info.is_connected = True
                
                return info
            except Exception:
                return None
        
        # Phase 1: Check priority IPs first (fast, sequential)
        for ip in priority_ips + common_ips:
            result = try_connect(ip)
            if result:
                discovered.append(result)
                print(f"  Found (priority): {result.model} at {ip}")
        
        # Phase 2: Build list of IPs to scan from known subnets
        scan_ips = []
        
        # 169.254.x.x link-local subnets (full host range 1-254)
        for subnet in link_local_subnets:
            for host in range(1, 255):
                addr = f"169.254.{subnet}.{host}"
                if addr not in priority_ips and addr not in common_ips:
                    scan_ips.append(addr)
        
        # 192.168.x.x static subnets (full host range 1-254)
        for subnet in static_subnets_192:
            for host in range(1, 255):
                addr = f"192.168.{subnet}.{host}"
                if addr not in priority_ips:
                    scan_ips.append(addr)
        
        print(f"  Scanning {len(scan_ips)} addresses across {len(link_local_subnets)} link-local + {len(static_subnets_192)} static subnets...")
        
        # Use thread pool for parallel scanning (50 threads for speed)
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(try_connect, ip): ip for ip in scan_ips}
            try:
                for future in concurrent.futures.as_completed(futures, timeout=30):
                    try:
                        result = future.result()
                        if result:
                            discovered.append(result)
                            print(f"  Found: {result.model} at {futures[future]}")
                    except Exception:
                        pass
            except concurrent.futures.TimeoutError:
                print("  Scan timeout reached, continuing with found instruments")
        
        return discovered
    
    def check_connection_health(self) -> Dict[str, Tuple[bool, str]]:
        """Check if connected instruments are still reachable.
        
        Returns dict of {instrument_type: (is_healthy, message)}
        Also updates instrument connection status.
        """
        health = {}
        
        # Check scope
        if self.scope is not None and self.scope_info:
            try:
                self.scope.query("*IDN?")
                health['scope'] = (True, "Connected")
            except Exception as e:
                health['scope'] = (False, f"Connection lost: {e}")
                self._log(f"⚠️ Oscilloscope connection lost: {self.scope_info.visa_address}")
                if self.scope_info:
                    self.scope_info.is_connected = False
        
        # Check SMU
        if self.smu is not None and self.smu_info:
            try:
                self.smu.query("*IDN?")
                health['smu'] = (True, "Connected")
            except Exception as e:
                health['smu'] = (False, f"Connection lost: {e}")
                self._log(f"⚠️ SMU connection lost: {self.smu_info.visa_address}")
                if self.smu_info:
                    self.smu_info.is_connected = False
        
        # Check AWG
        if self.awg is not None and self.awg_info:
            try:
                self.awg.query("*IDN?")
                health['awg'] = (True, "Connected")
            except Exception as e:
                health['awg'] = (False, f"Connection lost: {e}")
                self._log(f"⚠️ AWG/AFG connection lost: {self.awg_info.visa_address}")
                if self.awg_info:
                    self.awg_info.is_connected = False
        
        return health
    
    def reconnect_by_serial(self, serial_number: str, instrument_type: str) -> Tuple[bool, str]:
        """Try to reconnect to an instrument that changed IP address.
        
        Scans the network for the instrument by serial number and reconnects.
        Returns (success, message)
        """
        self._log(f"🔍 Searching for {instrument_type} S/N: {serial_number}...")
        
        # Rescan network (will find new IP)
        discovered = self.discover_instruments()
        
        # Find the instrument by serial
        for info in discovered:
            if info.serial_number == serial_number:
                new_addr = info.visa_address
                self._log(f"Found at new address: {new_addr}")
                
                # Reconnect based on type
                if instrument_type == "Oscilloscope":
                    success, msg = self.connect_scope(new_addr)
                elif instrument_type == "SMU":
                    success, msg = self.connect_smu(new_addr)
                elif instrument_type == "Function Generator":
                    success, msg = self.connect_awg(new_addr)
                else:
                    return False, f"Unknown instrument type: {instrument_type}"
                
                if success:
                    self._log(f"✓ Reconnected {instrument_type} at {new_addr}")
                    return True, f"Reconnected at {new_addr}"
                else:
                    return False, f"Found but failed to connect: {msg}"
        
        return False, f"Could not find {instrument_type} S/N {serial_number} on network"

    def add_manual(self, input_addr: str) -> Tuple[bool, str, Optional[InstrumentInfo]]:
        if not self.rm:
            return False, "VISA not initialized", None
        addr = self._make_visa_address(input_addr)
        try:
            inst = self.rm.open_resource(addr)
            inst.timeout = 5000
            inst.read_termination = '\n'
            inst.write_termination = '\n'
            idn = inst.query("*IDN?").strip()
            parts = idn.split(",")
            info = InstrumentInfo(
                manufacturer=parts[0].strip() if parts else "Unknown",
                model=parts[1].strip() if len(parts) > 1 else "Unknown",
                serial_number=parts[2].strip() if len(parts) > 2 else "Unknown",
                firmware_version=parts[3].strip() if len(parts) > 3 else "",
                visa_address=addr
            )
            model_up = info.model.upper()
            # Detect oscilloscopes - including TekscopeSW (PC software)
            if any(x in model_up for x in ['MSO', 'MDO', 'TDS', 'DPO', 'TEKSCOPE']):
                info.instrument_type = "Oscilloscope"
            elif any(x in model_up for x in ['2400', '2450', '2460', '2461', '2470']):
                info.instrument_type = "SMU"
            elif any(x in model_up for x in ['AFG', 'AWG']):
                info.instrument_type = "Function Generator"
            else:
                info.instrument_type = "Instrument"
            self.instruments[addr] = info
            inst.close()
            return True, f"Found: {info.manufacturer} {info.model}", info
        except Exception as e:
            return False, f"Connection failed: {e}", None

    def connect_scope(self, addr: str) -> Tuple[bool, str]:
        if not self.rm:
            return False, "VISA not initialized"
        try:
            self.scope = self.rm.open_resource(addr)
            self.scope.timeout = 30000
            self.scope.read_termination = '\n'
            self.scope.write_termination = '\n'
            idn = self.scope.query("*IDN?").strip()
            parts = idn.split(",")
            self.scope_info = InstrumentInfo(
                manufacturer=parts[0].strip() if parts else "Unknown",
                model=parts[1].strip() if len(parts) > 1 else "Unknown",
                serial_number=parts[2].strip() if len(parts) > 2 else "Unknown",
                firmware_version=parts[3].strip() if len(parts) > 3 else "",
                visa_address=addr, instrument_type="Oscilloscope", is_connected=True
            )
            self.scope.write("*CLS")
            self.scope.write("HEADer OFF")   # Essential: returns "0" not ":ACQUIRE:STATE 0"
            self.scope.write("VERBose OFF")  # Short form responses
            return True, f"Connected: {self.scope_info.model} (S/N: {self.scope_info.serial_number})"
        except Exception as e:
            return False, f"Failed: {e}"

    def connect_smu(self, addr: str) -> Tuple[bool, str]:
        if not self.rm:
            return False, "VISA not initialized"
        try:
            self.smu = self.rm.open_resource(addr)
            self.smu.timeout = 10000
            self.smu.read_termination = '\n'
            self.smu.write_termination = '\n'
            idn = self.smu.query("*IDN?").strip()
            parts = idn.split(",")
            self.smu_info = InstrumentInfo(
                manufacturer=parts[0].strip() if parts else "Unknown",
                model=parts[1].strip() if len(parts) > 1 else "Unknown",
                serial_number=parts[2].strip() if len(parts) > 2 else "Unknown",
                visa_address=addr, instrument_type="SMU", is_connected=True
            )
            self.smu.write("*CLS")
            return True, f"Connected: {self.smu_info.model}"
        except Exception as e:
            return False, f"Failed: {e}"

    def connect_awg(self, addr: str) -> Tuple[bool, str]:
        """Connect to an AWG or AFG instrument"""
        if not self.rm:
            return False, "VISA not initialized"
        try:
            self.awg = self.rm.open_resource(addr)
            self.awg.timeout = 10000
            self.awg.read_termination = '\n'
            self.awg.write_termination = '\n'
            idn = self.awg.query("*IDN?").strip()
            parts = idn.split(",")
            self.awg_info = InstrumentInfo(
                manufacturer=parts[0].strip() if parts else "Unknown",
                model=parts[1].strip() if len(parts) > 1 else "Unknown",
                serial_number=parts[2].strip() if len(parts) > 2 else "Unknown",
                visa_address=addr, instrument_type="Function Generator", is_connected=True
            )
            self.awg.write("*CLS")
            return True, f"Connected: {self.awg_info.model}"
        except Exception as e:
            return False, f"Failed: {e}"

    def disconnect_scope(self) -> Tuple[bool, str]:
        """Disconnect from oscilloscope"""
        if self.scope is None:
            return False, "Oscilloscope not connected"
        try:
            model = self.scope_info.model if self.scope_info else "Oscilloscope"
            self.scope.close()
            self.scope = None
            if self.scope_info:
                self.scope_info.is_connected = False
            self.scope_info = None
            return True, f"Disconnected: {model}"
        except Exception as e:
            self.scope = None
            self.scope_info = None
            return False, f"Error during disconnect: {e}"

    def disconnect_smu(self) -> Tuple[bool, str]:
        """Disconnect from SMU"""
        if self.smu is None:
            return False, "SMU not connected"
        try:
            model = self.smu_info.model if self.smu_info else "SMU"
            self.smu.close()
            self.smu = None
            if self.smu_info:
                self.smu_info.is_connected = False
            self.smu_info = None
            return True, f"Disconnected: {model}"
        except Exception as e:
            self.smu = None
            self.smu_info = None
            return False, f"Error during disconnect: {e}"

    def disconnect_awg(self) -> Tuple[bool, str]:
        """Disconnect from AWG/AFG"""
        if self.awg is None:
            return False, "AWG/AFG not connected"
        try:
            model = self.awg_info.model if self.awg_info else "AWG/AFG"
            self.awg.close()
            self.awg = None
            if self.awg_info:
                self.awg_info.is_connected = False
            self.awg_info = None
            return True, f"Disconnected: {model}"
        except Exception as e:
            self.awg = None
            self.awg_info = None
            return False, f"Error during disconnect: {e}"

    def disconnect_all(self) -> List[str]:
        """Disconnect all connected instruments. Returns list of status messages."""
        messages = []
        if self.scope is not None:
            success, msg = self.disconnect_scope()
            messages.append(f"Scope: {msg}")
        if self.smu is not None:
            success, msg = self.disconnect_smu()
            messages.append(f"SMU: {msg}")
        if self.awg is not None:
            success, msg = self.disconnect_awg()
            messages.append(f"AWG: {msg}")
        return messages if messages else ["No instruments connected"]

    def check_probe(self, ch: int) -> Tuple[bool, str]:
        if not self.scope:
            return False, ""
        try:
            result = self.scope.query(f"CH{ch}:PRObe:ID:TYPe?").strip()
            if result and result not in ["", "0", "NONE", '""', "UNKNOWN"]:
                return True, result
            return False, ""
        except Exception:
            return False, ""
    
    def get_probe_info(self, ch: int) -> Dict[str, str]:
        """Get probe information for a channel including type and serial number"""
        info = {"type": "", "serial": "", "connected": False}
        if not self.scope:
            return info
        try:
            # Query probe type
            probe_type = self.scope.query(f"CH{ch}:PRObe:ID:TYPe?").strip().strip('"')
            if probe_type and probe_type not in ["", "0", "NONE", "UNKNOWN"]:
                info["type"] = probe_type
                info["connected"] = True
                # Try to get serial number
                try:
                    serial = self.scope.query(f"CH{ch}:PRObe:ID:SERnumber?").strip().strip('"')
                    if serial and serial not in ["", "0", "NONE", "UNKNOWN"]:
                        info["serial"] = serial
                except Exception:
                    pass
        except Exception:
            pass
        return info

    def scope_write(self, cmd: str):
        """Write command to scope with logging"""
        if self.scope:
            self._log_scpi("cmd", f"SCOPE << {cmd}")
            self.scope.write(cmd)

    def scope_query(self, cmd: str, timeout: int = None) -> str:
        """Query scope with logging"""
        if not self.scope:
            return ""
        self._log_scpi("query", f"SCOPE << {cmd}")
        if timeout:
            old = self.scope.timeout
            self.scope.timeout = timeout
            try:
                result = self.scope.query(cmd).strip()
                self._log_scpi("response", f"SCOPE >> {result}")
                return result
            finally:
                self.scope.timeout = old
        result = self.scope.query(cmd).strip()
        self._log_scpi("response", f"SCOPE >> {result}")
        return result

    def scope_opc(self, timeout: int = 30):
        """Wait for operation complete - use only after long operations"""
        if self.scope:
            self._log_scpi("query", f"SCOPE << *OPC? (timeout={timeout}s)")
            old = self.scope.timeout
            self.scope.timeout = timeout * 1000
            try:
                result = self.scope.query("*OPC?").strip()
                self._log_scpi("response", f"SCOPE >> {result}")
            except Exception as e:
                self._log_scpi("response", f"SCOPE >> TIMEOUT: {e}")
            finally:
                self.scope.timeout = old

    def scope_wait_acquisition(self, timeout: int = 10) -> bool:
        """Wait for single acquisition to complete by polling ACQuire:STATE"""
        if not self.scope:
            return False
        start = time.time()
        while time.time() - start < timeout:
            state = self.scope_query("ACQuire:STATE?")
            # Handle both with and without header: "0" or ":ACQ:STATE 0"
            if state.endswith("0"):
                return True
            time.sleep(0.1)
        return False

    def smu_write(self, cmd: str):
        """Write command to SMU with logging"""
        if self.smu:
            self._log_scpi("cmd", f"SMU << {cmd}")
            self.smu.write(cmd)

    def smu_query(self, cmd: str) -> str:
        """Query SMU with logging"""
        if self.smu:
            self._log_scpi("query", f"SMU << {cmd}")
            result = self.smu.query(cmd).strip()
            self._log_scpi("response", f"SMU >> {result}")
            return result
        return ""


# =============================================================================
# TEST ENGINES
# =============================================================================

class AFGFrequencyTestEngine:
    def __init__(self, inst: InstrumentManager):
        self.inst = inst
        self.test_points: List[TestPoint] = []
        self.is_running = False
        self.should_stop = False
        self.on_log = None
        self.on_test_start = None
        self.on_test_complete = None
        self.on_progress = None
        self.on_screenshot = None
        self.on_complete = None
        self.reference_config: Optional[ReferenceConfig] = None  # Reference mode config

    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)

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

    def generate_test_points(self, freq_start: float, freq_stop: float,
                            num_points: int, tolerance: float,
                            spacing: str = "logarithmic") -> List[TestPoint]:
        self.test_points = []
        for i in range(num_points):
            if spacing == "logarithmic":
                log_start = math.log10(freq_start)
                log_stop = math.log10(freq_stop)
                log_freq = log_start + (log_stop - log_start) * i / (num_points - 1)
                freq = 10 ** log_freq
            else:
                freq = freq_start + (freq_stop - freq_start) * i / (num_points - 1)
            if freq >= 1e6:
                name = f"Freq {i+1}: {freq/1e6:.3f} MHz"
            elif freq >= 1e3:
                name = f"Freq {i+1}: {freq/1e3:.3f} kHz"
            else:
                name = f"Freq {i+1}: {freq:.1f} Hz"
            tp = TestPoint(
                test_id=i+1, name=name, nominal_value=freq, unit="Hz",
                tolerance_pct=tolerance, has_limits=True,
                lower_limit=freq * (1 - tolerance/100),
                upper_limit=freq * (1 + tolerance/100)
            )
            self.test_points.append(tp)
        return self.test_points

    def configure_scope(self, ch: int, termination: str, afg_amp: float):
        self._log("Resetting oscilloscope (FACtory)...")
        self.inst.scope_write("FACtory")
        # FACtory is a long operation - use OPC
        self.inst.scope_opc(30)
        self.inst.scope_write("*CLS")
        # FACtory resets these - must set again
        self.inst.scope_write("HEADer OFF")
        self.inst.scope_write("VERBose OFF")
        
        self._log(f"Configuring CH{ch}...")
        self.inst.scope_write(f"DISplay:WAVEView1:CH{ch}:STATE ON")
        
        # For AFG output, always use 50 ohm termination
        self.inst.scope_write(f"CH{ch}:TERmination 50")
        self._log(f"CH{ch} termination: 50Ω (AFG output)")
        
        self.inst.scope_write(f"CH{ch}:COUPling DC")
        self.inst.scope_write(f"CH{ch}:BANdwidth FULL")
        
        # Scale calculation: want signal to use ~80% of screen (8 divisions)
        # For Vpp signal across 8 div at 80% usage: scale = Vpp / (8 * 0.8) = Vpp / 6.4
        target_scale = afg_amp / 6.4
        nice = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5]
        scale = min((s for s in nice if s >= target_scale), default=1)
        self._log(f"CH{ch} scale: {scale} V/div (for {afg_amp} Vpp)")
        self.inst.scope_write(f"CH{ch}:SCAle {scale}")
        self.inst.scope_write(f"CH{ch}:OFFSet 0")
        
        self.inst.scope_write("TRIGger:A:TYPE EDGE")
        self.inst.scope_write(f"TRIGger:A:EDGE:SOUrce CH{ch}")
        self.inst.scope_write("TRIGger:A:EDGE:SLOpe RISe")
        self.inst.scope_write(f"TRIGger:A:LEVel:CH{ch} 0")

    def setup_freq_measurement(self, ch: int, source: str = None):
        """Setup frequency measurement. source can be CH<n> or REF<n>"""
        if source is None:
            source = f"CH{ch}"
        self._log(f"Setting up frequency measurement on {source}...")
        self.inst.scope_write('MEASUrement:DELETEALL')
        self.inst.scope_write('MEASUrement:ADDNew "MEAS1"')
        self.inst.scope_write("MEASUrement:MEAS1:TYPe FREQUENCY")
        self.inst.scope_write(f"MEASUrement:MEAS1:SOUrce {source}")
        self.inst.scope_write("MEASUrement:MEAS1:STATE ON")

    def configure_afg(self, freq: float, amp: float):
        self.inst.scope_write("AFG:FUNCtion SQUare")
        self.inst.scope_write(f"AFG:AMPLitude {amp}")
        self.inst.scope_write("AFG:OFFSet 0")
        self.inst.scope_write(f"AFG:FREQuency {freq}")
        self.inst.scope_write("AFG:SQUare:DUty 50")
        self.inst.scope_write("AFG:OUTPut:LOAd:IMPEDance FIFTy")
        self.inst.scope_write("AFG:OUTPut:STATE ON")

    def set_timebase(self, freq: float):
        """Set horizontal scale to show approximately 2-2.5 cycles"""
        period = 1.0 / freq
        # Want 2.5 cycles across 10 divisions
        # So each division = 2.5 * period / 10 = period / 4
        target_scale = period / 4
        
        nice = [1e-9, 2e-9, 4e-9, 5e-9, 10e-9, 20e-9, 40e-9, 50e-9, 100e-9, 
                200e-9, 400e-9, 500e-9, 1e-6, 2e-6, 4e-6, 5e-6, 10e-6, 20e-6, 
                40e-6, 50e-6, 100e-6, 200e-6, 400e-6, 500e-6, 1e-3, 2e-3, 
                4e-3, 5e-3, 10e-3, 20e-3, 40e-3, 50e-3, 100e-3, 200e-3, 
                400e-3, 500e-3, 1, 2, 4, 5, 10]
        scale = min((s for s in nice if s >= target_scale), default=1e-3)
        
        self.inst.scope_write(f"HORizontal:SCAle {scale}")
        self._log(f"Timebase: {scale*1e6:.3g} µs/div ({2.5*period/scale:.1f} cycles)")

    def measure_frequency(self, ref_mode: bool = False) -> float:
        """Perform measurement and read frequency. In ref_mode, skip acquisition."""
        if not ref_mode:
            # Set to single sequence mode and acquire
            self.inst.scope_write("ACQuire:STOPAfter SEQuence")
            self.inst.scope_write("ACQuire:SEQuence:NUMSEQuence 1")
            
            # Start acquisition
            self.inst.scope_write("ACQuire:STATE RUN")
            
            # Wait for acquisition to complete (state goes to 0)
            if not self.inst.scope_wait_acquisition(timeout=10):
                self._log("Warning: Acquisition timeout")
                return 0.0
        else:
            # Reference mode - just wait a moment for measurement to settle
            time.sleep(0.3)
        
        # Read measurement result
        try:
            result = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
            if result:
                val = float(result)
                if val > 0 and not math.isnan(val) and not math.isinf(val):
                    return val
        except Exception as e:
            self._log(f"Measurement error: {e}")
        
        return 0.0

    def auto_scale_vertical(self, ch: int, source: str = None, ref_mode: bool = False):
        """Dynamically adjust vertical scale and offset based on actual signal.
        In ref_mode, use REF channel and skip acquisition."""
        if source is None:
            source = f"CH{ch}"
        
        if not ref_mode:
            # Do a quick acquisition to measure the signal
            self.inst.scope_write("ACQuire:STOPAfter SEQuence")
            self.inst.scope_write("ACQuire:STATE RUN")
            self.inst.scope_wait_acquisition(timeout=5)
        
        # Use immediate measurements for quick min/max
        try:
            self.inst.scope_write(f"MEASUrement:IMMed:SOUrce {source}")
            
            self.inst.scope_write("MEASUrement:IMMed:TYPe MAXimum")
            vmax_str = self.inst.scope_query("MEASUrement:IMMed:VALue?")
            vmax = float(vmax_str) if vmax_str else 0
            
            self.inst.scope_write("MEASUrement:IMMed:TYPe MINImum")
            vmin_str = self.inst.scope_query("MEASUrement:IMMed:VALue?")
            vmin = float(vmin_str) if vmin_str else 0
            
            if vmax > vmin and not math.isinf(vmax) and not math.isinf(vmin):
                vpp = vmax - vmin
                vcenter = (vmax + vmin) / 2
                
                # Target: signal uses 80% of 8 divisions = 6.4 divisions
                target_scale = vpp / 6.4
                
                # Round to nice 1-2-5 sequence values
                nice = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 
                        0.2, 0.5, 1, 2, 5, 10]
                scale = min((s for s in nice if s >= target_scale), default=1)
                
                # For REF channels, use REF:REF<n>:VERTical commands
                if source.startswith("REF"):
                    self.inst.scope_write(f"{source}:VERTical:SCAle {scale}")
                    self.inst.scope_write(f"{source}:VERTical:POSition {-vcenter}")
                else:
                    self.inst.scope_write(f"CH{ch}:SCAle {scale}")
                    self.inst.scope_write(f"CH{ch}:OFFSet {-vcenter}")
                self._log(f"Auto-scale {source}: Vpp={vpp*1000:.1f}mV, scale={scale*1000:.0f}mV/div")
        except Exception as e:
            self._log(f"Auto-scale warning: {e}")

    def capture_screenshot(self, test_id: int, output_dir: Path) -> str:
        """Save screenshot from scope and transfer to local PC"""
        try:
            filename = f"test_{test_id:03d}.png"
            local_path = output_dir / filename
            
            # Try multiple scope paths - C:/Temp preferred, C:/ as fallback
            scope_paths = [f"C:/Temp/test_{test_id}.png", f"C:/test_{test_id}.png"]
            data = None
            used_path = None
            
            for scope_path in scope_paths:
                try:
                    # Save image on scope
                    self.inst.scope_write(f'SAVe:IMAGe "{scope_path}"')
                    self.inst.scope_query("*OPC?")
                    
                    # Read file data from scope
                    self.inst.scope_write(f'FILESystem:READFile "{scope_path}"')
                    data = self.inst.scope.read_raw()
                    used_path = scope_path
                    break  # Success, exit loop
                except Exception:
                    continue  # Try next path
            
            if data is None:
                self._log("Screenshot error: all scope paths failed")
                return ""
            
            # Save to local file
            with open(local_path, 'wb') as f:
                f.write(data)
            
            # Delete temp file from scope
            try:
                self.inst.scope_write(f'FILESystem:DELEte "{used_path}"')
            except:
                pass  # Cleanup failure is not critical
            
            self._log(f"Screenshot saved: {filename}")
            return str(local_path)
        except Exception as e:
            self._log(f"Screenshot error: {e}")
            return ""

    def run_test(self, tp: TestPoint, ch: int, afg_amp: float, output_dir: Path):
        tp.status = TestStatus.RUNNING
        if self.on_test_start:
            self.on_test_start(tp)
        
        ref_mode = self._is_ref_mode(tp.test_id)
        source = self._get_source(ch, tp.test_id)
        
        try:
            if ref_mode:
                self._log(f"Reference mode: measuring from {source}")
                # Skip AFG configuration - use pre-recorded waveform
                # Still set timebase for proper display
                self.set_timebase(tp.nominal_value)
            else:
                self.configure_afg(tp.nominal_value, afg_amp)
                self.set_timebase(tp.nominal_value)
                # Auto-scale vertical based on actual signal
                self.auto_scale_vertical(ch, source, ref_mode)
            
            # Perform measurement (skip acquisition in ref_mode)
            tp.measured_value = self.measure_frequency(ref_mode)
            
            if tp.measured_value > 0:
                tp.error_pct = ((tp.measured_value - tp.nominal_value) / tp.nominal_value) * 100
                if tp.lower_limit <= tp.measured_value <= tp.upper_limit:
                    tp.status = TestStatus.PASS
                else:
                    tp.status = TestStatus.FAIL
            else:
                tp.status = TestStatus.ERROR
                
            if output_dir:
                tp.screenshot_path = self.capture_screenshot(tp.test_id, output_dir)
                if self.on_screenshot and tp.screenshot_path:
                    self.on_screenshot(tp.screenshot_path)
        except Exception as e:
            tp.status = TestStatus.ERROR
            self._log(f"Error: {e}")
        if self.on_test_complete:
            self.on_test_complete(tp)

    def run_sequence(self, ch: int, termination: str, afg_amp: float, output_dir: Path):
        self.is_running = True
        self.should_stop = False
        
        # Check if any tests use reference mode
        any_ref_mode = any(self._is_ref_mode(tp.test_id) for tp in self.test_points if tp.enabled)
        all_ref_mode = all(self._is_ref_mode(tp.test_id) for tp in self.test_points if tp.enabled)
        
        try:
            if all_ref_mode:
                self._log("Reference mode: All tests using pre-recorded waveforms")
                # Minimal scope setup - just measurement
                self.inst.scope_write("*CLS")
                self.inst.scope_write("HEADer OFF")
                self.inst.scope_write("VERBose OFF")
                source = f"REF{ch}"
                # Turn on REF display
                self.inst.scope_write(f'DISplay:WAVEView1:{source}:STATE ON')
            else:
                self.configure_scope(ch, termination, afg_amp)
            
            # Setup measurement with appropriate source
            source = self._get_source(ch, self.test_points[0].test_id if self.test_points else 0)
            self.setup_freq_measurement(ch, source)
            
            total = len(self.test_points)
            for i, tp in enumerate(self.test_points):
                if self.should_stop:
                    break
                if not tp.enabled:
                    tp.status = TestStatus.SKIPPED
                    continue
                    
                # Update measurement source if needed (switching between REF and CH)
                new_source = self._get_source(ch, tp.test_id)
                if new_source != source:
                    self.setup_freq_measurement(ch, new_source)
                    source = new_source
                    
                if self.on_progress:
                    self.on_progress((i+1)/total*100, f"Test {i+1}/{total}")
                self.run_test(tp, ch, afg_amp, output_dir)
            
            # Turn off AFG only if we used it
            if not all_ref_mode:
                self.inst.scope_write("AFG:OUTPut:STATE OFF")
        except Exception as e:
            self._log(f"Sequence error: {e}")
        finally:
            self.is_running = False
            if self.on_complete:
                p = sum(1 for t in self.test_points if t.status == TestStatus.PASS)
                f = sum(1 for t in self.test_points if t.status == TestStatus.FAIL)
                self.on_complete(p, f)

    def stop(self):
        self.should_stop = True


class LEDCurrentTestEngine:
    """
    LED Current Test Engine
    
    Tests an LED circuit with a shunt resistor using SMU 2450 and oscilloscope.
    Circuit: SMU+ -> 470Ω -> LED -> 10Ω shunt -> SMU-
    CH3 measures voltage across the 10Ω shunt resistor.
    Using Ohm's law: I = V/R = V/10
    
    Pass criteria: Scope current measurement within 3% of SMU current measurement.
    """
    
    SHUNT_RESISTANCE = 10.0  # 10 ohm shunt resistor
    TOLERANCE_UA = 300       # Absolute tolerance: ±300 µA (0.3 mA)
    
    def __init__(self, inst: InstrumentManager):
        self.inst = inst
        self.test_points: List[TestPoint] = []
        self.is_running = False
        self.should_stop = False
        self.on_log = None
        self.on_test_start = None
        self.on_test_complete = None
        self.on_progress = None
        self.on_screenshot = None
        self.on_complete = None
        self.reference_config: Optional[ReferenceConfig] = None  # Reference mode config

    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)

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

    def generate_test_points(self, voltages: List[float]) -> List[TestPoint]:
        """Generate test points for voltage sweep"""
        self.test_points = []
        for i, v in enumerate(voltages):
            tp = TestPoint(
                test_id=i+1, 
                name=f"SMU Voltage: {v:.1f}V",
                nominal_value=v, 
                unit="V", 
                tolerance_pct=0,  # Not using percentage
                has_limits=True  # Will compare scope vs SMU current
            )
            self.test_points.append(tp)
        return self.test_points

    def configure_scope(self, ch: int):
        """Configure oscilloscope for current measurement via shunt"""
        self._log("Resetting oscilloscope...")
        self.inst.scope_write("FACtory")
        self.inst.scope_opc(30)
        self.inst.scope_write("*CLS")
        self.inst.scope_write("HEADer OFF")
        self.inst.scope_write("VERBose OFF")
        
        self._log(f"Configuring CH{ch} for current measurement...")
        
        # Turn off all channels first, then enable only the one we need (support up to 8)
        for c in range(1, 9):
            if c != ch:
                try:
                    self.inst.scope_write(f"DISplay:WAVEView1:CH{c}:STATE OFF")
                except:
                    pass  # Channel may not exist on this scope
        
        self.inst.scope_write(f"DISplay:WAVEView1:CH{ch}:STATE ON")
        self.inst.scope_write(f"CH{ch}:COUPling DC")
        self.inst.scope_write(f"CH{ch}:TERmination 1E6")  # High-Z for passive probe
        
        # Limit bandwidth to reduce noise (20 MHz for slow DC signals)
        self.inst.scope_write(f"CH{ch}:BANdwidth 20E6")
        self._log(f"CH{ch} bandwidth limited to 20 MHz (noise reduction)")
        
        # Set up external attenuation for V to A conversion
        # With 10 ohm shunt: I = V/R, so attenuation factor = 1/R = 0.1
        # This makes the scope display in Amps directly
        atten_factor = 1.0 / self.SHUNT_RESISTANCE  # 0.1 for 10 ohm
        self._log(f"Setting ext attenuation to {atten_factor} (1/{self.SHUNT_RESISTANCE}Ω)")
        self.inst.scope_write(f"CH{ch}:PROBEFunc:EXTAtten {atten_factor}")
        # Enable alternate units - STATE ON is required to activate it
        self.inst.scope_write(f"CH{ch}:PROBEFunc:EXTUnits:STATE ON")
        self._log(f"CH{ch} alternate units enabled (displays as Amps)")
        
        # Initial scale - small for mA range measurements (1mA/div)
        self.inst.scope_write(f"CH{ch}:SCAle 0.001")  # 1mA/div initial
        self.inst.scope_write(f"CH{ch}:OFFSet 0")
        
        # Trigger setup - auto trigger for DC signals
        self.inst.scope_write("TRIGger:A:TYPE EDGE")
        self.inst.scope_write(f"TRIGger:A:EDGE:SOUrce CH{ch}")
        self.inst.scope_write("TRIGger:A:EDGE:SLOpe RISe")
        self.inst.scope_write("TRIGger:A:MODe AUTO")  # Auto trigger for DC
        
        # Set horizontal scale - 20ms/div (avoid roll mode which starts at 40ms+)
        self.inst.scope_write("HORizontal:SCAle 20e-3")  # 20ms/div
        self._log("Horizontal scale: 20 ms/div")

    def setup_current_measurement(self, ch: int, source: str = None):
        """Set up MEAN measurement for DC current. source can be CH<n> or REF<n>"""
        if source is None:
            source = f"CH{ch}"
        self._log(f"Setting up DC current measurement on {source}...")
        self.inst.scope_write('MEASUrement:DELETEALL')
        self.inst.scope_write('MEASUrement:ADDNew "MEAS1"')
        self.inst.scope_write("MEASUrement:MEAS1:TYPe MEAN")
        self.inst.scope_write(f"MEASUrement:MEAS1:SOUrce {source}")
        self.inst.scope_write("MEASUrement:MEAS1:STATE ON")

    def configure_smu(self, voltage: float, current_limit: float = 0.1):
        """Configure SMU 2450 for voltage source with current measurement using TSP commands"""
        self._log(f"Configuring SMU for {voltage}V (source V, measure I)...")
        
        # Reset SMU using TSP command
        self.inst.smu_write("reset()")
        time.sleep(0.5)  # Allow reset to complete
        
        # Set the source function to voltage mode (TSP syntax)
        self.inst.smu_write("smu.source.func = smu.FUNC_DC_VOLTAGE")
        self.inst.smu_write(f"smu.source.level = {voltage}")
        self.inst.smu_write(f"smu.source.ilimit.level = {current_limit}")
        self.inst.smu_write("smu.source.readback = smu.ON")
        
        # Set measurement function to current mode
        self.inst.smu_write("smu.measure.func = smu.FUNC_DC_CURRENT")
        self.inst.smu_write("smu.measure.autorange = smu.ON")
        
        # Set NPLC for better accuracy (1 = 60Hz line cycle)
        self.inst.smu_write("smu.measure.nplc = 1")
        
        # Enable the output
        self.inst.smu_write("smu.source.output = smu.ON")
        time.sleep(0.3)  # Allow output to stabilize
        self._log("SMU output enabled")

    def set_smu_voltage(self, voltage: float):
        """Change SMU voltage without full reconfiguration (TSP)"""
        self.inst.smu_write(f"smu.source.level = {voltage}")
        time.sleep(0.2)  # Allow settling

    def measure_currents(self, ch: int) -> Tuple[float, float]:
        """
        Measure current from both SMU and scope.
        Returns: (scope_current_mA, smu_current_mA)
        """
        # Let circuit settle
        time.sleep(0.3)
        
        # Measure from SMU using TSP - take a reading and get from buffer
        smu_current = 0.0
        try:
            # Take a measurement and store in buffer
            self.inst.smu_write("smu.measure.read()")
            time.sleep(0.1)
            # Get the reading from the buffer (current value in Amps)
            result = self.inst.smu_query("printbuffer(1, 1, defbuffer1.readings)")
            if result:
                smu_current = float(result.strip()) * 1000  # Convert A to mA
                self._log(f"SMU measured: {smu_current:.3f} mA")
        except Exception as e:
            self._log(f"SMU measurement error: {e}")
        
        # Measure from scope - returns current directly in Amps due to EXTUnits:STATE ON
        # The external attenuation (1/R_shunt) already converts V to A
        scope_current = 0.0
        try:
            # Single acquisition
            self.inst.scope_write("ACQuire:STOPAfter SEQuence")
            self.inst.scope_write("ACQuire:STATE RUN")
            self.inst.scope_wait_acquisition(timeout=5)
            
            # Read mean current (already in Amps due to EXTUnits)
            result = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
            if result:
                current_amps = float(result)
                scope_current = current_amps * 1000  # Convert A to mA
                self._log(f"Scope measured: {scope_current:.3f} mA")
        except Exception as e:
            self._log(f"Scope measurement error: {e}")
        
        return scope_current, smu_current
    
    def read_smu_current(self) -> float:
        """Read current measurement from SMU (in mA)"""
        try:
            self.inst.smu_write("smu.measure.read()")
            result = self.inst.smu_query("printbuffer(1, 1, defbuffer1.readings)")
            if result:
                current_A = float(result.strip())
                current_mA = current_A * 1000
                return current_mA
        except Exception as e:
            self._log(f"SMU read error: {e}")
        return 0.0
    
    def measure_scope_current(self, ch: int, expected_current_mA: float) -> float:
        """
        Take scope measurement and return current in mA.
        Uses expected current for trigger level. Runs 5 acquisitions then stops.
        
        Args:
            ch: Scope channel number  
            expected_current_mA: Expected current from SMU reading (for trigger level)
        """
        try:
            # Set trigger level to expected current (not 50%!)
            trigger_level_A = expected_current_mA / 1000
            self.inst.scope_write(f"TRIGger:A:LEVel:CH{ch} {trigger_level_A}")
            self._log(f"Trigger level: {trigger_level_A*1000:.3f} mA")
            
            # Run mode (not single seq) - let it acquire for a bit then stop
            self.inst.scope_write("ACQuire:STOPAfter RUNSTop")
            self.inst.scope_write("ACQuire:STATE RUN")
            
            # Wait for ~5 acquisitions (with 20ms/div = 200ms record, 5 acq ~ 1 second)
            time.sleep(1.0)
            
            # Stop acquisition
            self.inst.scope_write("ACQuire:STATE STOP")
            time.sleep(0.2)  # Brief settle
            
            # Check for clipping
            clipping = self.inst.scope_query(f"CH{ch}:CLIPping?")
            if clipping and clipping.strip() == "1":
                self._log(f"WARNING: CH{ch} is clipping! Measurement may be inaccurate.")
            
            # Read mean current (already in Amps due to EXTUnits)
            result = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
            if result:
                current_A = float(result)
                current_mA = current_A * 1000
                self._log(f"Scope measured: {current_mA:.3f} mA")
                return current_mA
        except Exception as e:
            self._log(f"Scope measurement error: {e}")
        return 0.0

    def setup_vertical_for_current(self, ch: int, expected_current_mA: float):
        """
        Set vertical scale, offset, and trigger based on expected current from SMU.
        Checks for clipping and adjusts scale if needed.
        
        Args:
            ch: Scope channel number
            expected_current_mA: Expected current in mA (from SMU)
        """
        current_A = expected_current_mA / 1000  # Convert to Amps for scope
        
        # Start with 500 µA/div scale for best resolution on mA signals
        scales = [0.0005, 0.001, 0.002, 0.005]  # 500µA, 1mA, 2mA, 5mA per div
        
        for scale in scales:
            self._log(f"Trying vertical: {scale*1e6:.0f} µA/div, offset: {current_A*1000:.3f} mA")
            
            # Set scale
            self.inst.scope_write(f"CH{ch}:SCAle {scale}")
            
            # Set offset directly to expected current value
            # This centers the expected signal on screen
            self.inst.scope_write(f"CH{ch}:OFFSet {current_A}")
            
            # Quick acquisition to check for clipping
            self.inst.scope_write("ACQuire:STOPAfter SEQuence")
            self.inst.scope_write("ACQuire:STATE RUN")
            time.sleep(0.3)  # Brief acquisition
            self.inst.scope_write("ACQuire:STATE STOP")
            
            # Check for clipping using CH<x>:CLIPping? query
            clipping = self.inst.scope_query(f"CH{ch}:CLIPping?")
            if clipping and clipping.strip() == "1":
                self._log(f"Clipping detected at {scale*1e6:.0f} µA/div, trying larger scale...")
                continue  # Try next larger scale
            else:
                self._log(f"Vertical setup complete: {scale*1e6:.0f} µA/div, no clipping")
                break
        
        # Set trigger source to measurement channel, edge type, at expected current level
        self.inst.scope_write(f"TRIGger:A:EDGE:SOUrce CH{ch}")
        self.inst.scope_write("TRIGger:A:TYPE EDGE")
        self.inst.scope_write(f"TRIGger:A:LEVel:CH{ch} {current_A}")
        self.inst.scope_write("TRIGger:A:MODe AUTO")  # AUTO for DC signals
        self._log(f"Trigger: CH{ch} edge at {current_A*1000:.3f} mA")

    def take_preliminary_measurement(self, ch: int) -> float:
        """Take a quick measurement to determine actual current level for scaling"""
        # Single acquisition
        self.inst.scope_write("ACQuire:STOPAfter SEQuence")
        self.inst.scope_write("ACQuire:STATE RUN")
        self.inst.scope_wait_acquisition(timeout=5)
        
        # Read mean current (already in Amps due to EXTUnits)
        result = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
        if result:
            current_A = float(result)
            current_mA = current_A * 1000
            self._log(f"Preliminary measurement: {current_mA:.3f} mA")
            return current_mA
        return 1.0  # Default if measurement fails

    def capture_screenshot(self, test_id: int, output_dir: Path) -> str:
        """Save screenshot from scope and transfer to local PC"""
        try:
            filename = f"led_current_{test_id:03d}.png"
            local_path = output_dir / filename
            
            # Try multiple scope paths - C:/Temp preferred, C:/ as fallback
            scope_paths = [f"C:/Temp/led_{test_id}.png", f"C:/led_{test_id}.png"]
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
                self._log("Screenshot error: all scope paths failed")
                return ""
            
            with open(local_path, 'wb') as f:
                f.write(data)
            
            # Delete temp file from scope
            try:
                self.inst.scope_write(f'FILESystem:DELEte "{used_path}"')
            except:
                pass
            
            self._log(f"Screenshot saved: {filename}")
            return str(local_path)
        except Exception as e:
            self._log(f"Screenshot error: {e}")
            return ""

    def run_test(self, tp: TestPoint, ch: int, output_dir: Path):
        tp.status = TestStatus.RUNNING
        if self.on_test_start:
            self.on_test_start(tp)
        
        ref_mode = self._is_ref_mode(tp.test_id)
        source = self._get_source(ch, tp.test_id)
        
        try:
            if ref_mode:
                # Reference mode - measure from pre-recorded waveform only
                self._log(f"Reference mode: measuring from {source}")
                
                # Just read the measurement (already set up on REF channel)
                time.sleep(0.3)  # Let measurement settle
                result = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
                scope_current = float(result) * 1000 if result else 0  # A to mA
                
                # Store results - no SMU comparison in ref mode
                tp.measured_value = scope_current
                tp.extra_data['scope_current_mA'] = scope_current
                tp.extra_data['voltage'] = tp.nominal_value
                tp.extra_data['reference_mode'] = True
                tp.error_pct = 0  # No error calculation in ref mode
                tp.extra_data['error_uA'] = 0
                
                # In reference mode, just record the value - no pass/fail
                tp.status = TestStatus.PASS  # Or could use a new status
                self._log(f"Reference measurement: {scope_current:.3f} mA")
                
            else:
                # Normal mode with SMU
                # Step 1: Set SMU voltage and get the actual current reading
                self.configure_smu(tp.nominal_value)
                
                # Step 2: Read current from SMU - this tells us what to expect
                smu_current = self.read_smu_current()
                self._log(f"SMU reports: {smu_current:.3f} mA")
                
                # Step 3: Set up scope - channel, scale, offset (trigger source set here)
                self.setup_vertical_for_current(ch, smu_current)
                
                # Step 4: Take the scope measurement with 50% trigger level, single sequence
                scope_current = self.measure_scope_current(ch, smu_current)
                
                # Step 5: Ensure acquisition is STOPPED before getting results/screenshot
                self.inst.scope_write("ACQuire:STATE STOP")
                time.sleep(0.2)  # Brief settle time
                
                # Store results
                tp.measured_value = scope_current  # Scope measurement
                tp.extra_data['smu_current_mA'] = smu_current
                tp.extra_data['scope_current_mA'] = scope_current
                tp.extra_data['voltage'] = tp.nominal_value
                
                # Calculate absolute error and check pass/fail (using ±300 µA tolerance)
                error_mA = scope_current - smu_current
                error_uA = error_mA * 1000
                tp.error_pct = error_uA
                tp.extra_data['error_uA'] = error_uA
                
                tolerance_mA = self.TOLERANCE_UA / 1000
                tp.lower_limit = smu_current - tolerance_mA
                tp.upper_limit = smu_current + tolerance_mA
                
                if abs(error_uA) <= self.TOLERANCE_UA:
                    tp.status = TestStatus.PASS
                    self._log(f"PASS: Error {error_uA:+.1f} µA (within ±{self.TOLERANCE_UA} µA)")
                else:
                    tp.status = TestStatus.FAIL
                    self._log(f"FAIL: Error {error_uA:+.1f} µA (exceeds ±{self.TOLERANCE_UA} µA)")
            
            # Capture screenshot
            if output_dir:
                tp.screenshot_path = self.capture_screenshot(tp.test_id, output_dir)
                if self.on_screenshot and tp.screenshot_path:
                    self.on_screenshot(tp.screenshot_path)
                    
        except Exception as e:
            tp.status = TestStatus.ERROR
            self._log(f"Error: {e}")
        
        if self.on_test_complete:
            self.on_test_complete(tp)

    def run_sequence(self, ch: int, output_dir: Path):
        self.is_running = True
        self.should_stop = False
        
        # Check if all tests use reference mode
        all_ref_mode = all(self._is_ref_mode(tp.test_id) for tp in self.test_points if tp.enabled)
        
        try:
            if all_ref_mode:
                self._log("Reference mode: All tests using pre-recorded waveforms")
                # Minimal scope setup - just measurement on REF channel
                self.inst.scope_write("*CLS")
                self.inst.scope_write("HEADer OFF")
                self.inst.scope_write("VERBose OFF")
                source = f"REF{ch}"
                self.inst.scope_write(f'DISplay:WAVEView1:{source}:STATE ON')
                self.setup_current_measurement(ch, source)
            else:
                self.configure_scope(ch)
                self.setup_current_measurement(ch)
            
            total = len(self.test_points)
            for i, tp in enumerate(self.test_points):
                if self.should_stop:
                    break
                if not tp.enabled:
                    tp.status = TestStatus.SKIPPED
                    continue
                if self.on_progress:
                    self.on_progress((i+1)/total*100, f"Test {i+1}/{total}")
                self.run_test(tp, ch, output_dir)
            
            # Turn off SMU only if we used it
            if not all_ref_mode:
                self.inst.smu_write("smu.source.output = smu.OFF")
                self._log("SMU output disabled")
            
        except Exception as e:
            self._log(f"Sequence error: {e}")
        finally:
            self.is_running = False
            if self.on_complete:
                p = sum(1 for t in self.test_points if t.status == TestStatus.PASS)
                f = sum(1 for t in self.test_points if t.status == TestStatus.FAIL)
                self.on_complete(p, f)

    def stop(self):
        self.should_stop = True
        try:
            self.inst.smu_write("smu.source.output = smu.OFF")
        except Exception:
            pass


# =============================================================================
# SPECTRUM SCANNER ENGINE
# =============================================================================

@dataclass
class PeakSignal:
    """Represents a detected RF signal peak"""
    frequency_hz: float
    amplitude_dbm: float
    band_name: str = ""
    
    @property
    def frequency_mhz(self) -> float:
        return self.frequency_hz / 1e6
    
    def format_frequency(self) -> str:
        if self.frequency_hz >= 1e9:
            return f"{self.frequency_hz/1e9:.4f} GHz"
        else:
            return f"{self.frequency_mhz:.3f} MHz"


class SpectrumScannerEngine:
    """Engine for scanning RF spectrum using SpectrumView"""
    
    # MSO4/5/6 has 1 GHz capture bandwidth - can use larger spans
    SPAN_PER_STEP = 500e6      # 500 MHz span per step (faster scanning)
    NUM_PEAKS = 11             # Max peaks per span
    PEAK_THRESHOLD = -80       # dBm threshold
    PEAK_EXCURSION = 6         # dB excursion between peaks
    SETTLE_TIME = 0.5          # Seconds to settle after frequency change
    
    def __init__(self, inst: InstrumentManager):
        self.inst = inst
        self.test_points: List[TestPoint] = []
        self.all_peaks: List[PeakSignal] = []
        self.is_running = False
        self.should_stop = False
        self.on_log = None
        self.on_test_start = None
        self.on_test_complete = None
        self.on_progress = None
        self.on_screenshot = None
        self.on_complete = None
        self.reference_config: Optional[ReferenceConfig] = None  # Reference mode config
        self.scope_bandwidth_mhz: Optional[int] = None  # Queried at runtime
    
    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)

    def _query_scope_bandwidth_mhz(self) -> Optional[int]:
        """Query installed bandwidth from LICense:ITEM? strings.
        
        MSO 4/5/6 Series encodes bandwidth in license strings like X-BW-YYYY
        where X = series number, YYYY = bandwidth in MHz.
        The model number does NOT contain bandwidth (second digit = channel count).
        Example: MSO68B = 8-channel scope, NOT 8 GHz. Bandwidth from license.
        """
        import re
        try:
            for i in range(50):
                try:
                    item = self.inst.scope_query(f"LICense:ITEM? {i}")
                    if item is None:
                        break
                    item = item.strip()
                    match = re.search(r'(\d)-BW-(\d+)', item)
                    if match:
                        bw_mhz = int(match.group(2))
                        self._log(f"Scope bandwidth: {bw_mhz} MHz ({bw_mhz/1000:.1f} GHz) from license {match.group(0)}")
                        return bw_mhz
                except Exception:
                    break
        except Exception as e:
            self._log(f"Could not query bandwidth: {e}")
        return None

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
    
    def _auto_scale_for_no_clipping(self, ch: int, max_attempts: int = 5):
        """
        Check for clipping and increase vertical scale until no clipping.
        This is critical for accurate measurements.
        """
        scales = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0]  # Volts/div progression
        
        for attempt in range(max_attempts):
            # Run a quick acquisition
            self.inst.scope_write("ACQuire:STOPAfter SEQuence")
            self.inst.scope_write("ACQuire:STATE RUN")
            time.sleep(0.3)
            
            # Check for clipping
            clipping = self.inst.scope_query(f"CH{ch}:CLIPping?")
            if clipping and clipping.strip() == "1":
                # Clipping detected - increase scale
                current_scale = float(self.inst.scope_query(f"CH{ch}:SCAle?"))
                # Find next larger scale
                new_scale = current_scale * 2
                for s in scales:
                    if s > current_scale:
                        new_scale = s
                        break
                self._log(f"Clipping detected, increasing scale to {new_scale} V/div")
                self.inst.scope_write(f"CH{ch}:SCAle {new_scale}")
            else:
                self._log(f"No clipping at current scale")
                break
        
        self.inst.scope_write("ACQuire:STATE STOP")
    
    def generate_test_points(self, start_mhz: float, stop_mhz: float) -> List[TestPoint]:
        """Generate test points (one for scan summary)"""
        self.test_points = [
            TestPoint(
                test_id=1,
                name=f"Spectrum Scan {start_mhz:.0f}-{stop_mhz:.0f} MHz",
                nominal_value=stop_mhz - start_mhz,
                unit="MHz",
                tolerance_pct=0,
                has_limits=False
            )
        ]
        return self.test_points
    
    def _identify_band(self, freq_hz: float) -> str:
        """Identify which RF band a frequency belongs to"""
        freq_mhz = freq_hz / 1e6
        if 88 <= freq_mhz <= 108:
            return "FM Radio"
        elif 470 <= freq_mhz <= 608:
            return "TV UHF"
        elif 614 <= freq_mhz <= 698:
            return "600 MHz LTE"
        elif 698 <= freq_mhz <= 806:
            return "700 MHz LTE"
        elif 824 <= freq_mhz <= 894:
            return "Cellular 850"
        elif 1850 <= freq_mhz <= 1990:
            return "PCS 1900"
        elif 2400 <= freq_mhz <= 2500:
            return "WiFi 2.4GHz"
        elif 5150 <= freq_mhz <= 5850:
            return "WiFi 5GHz"
        elif freq_mhz < 30:
            return "HF"
        elif freq_mhz < 300:
            return "VHF"
        elif freq_mhz < 3000:
            return "UHF"
        else:
            return "SHF"
    
    def configure_spectrum_view(self, ch: int):
        """Configure SpectrumView for scanning"""
        self._log(f"Configuring SpectrumView on CH{ch}...")
        
        # CRITICAL: Factory reset first to ensure clean state
        self._log("Resetting to factory defaults...")
        self.inst.scope_write("FACtory")
        self.inst.scope_opc(30)  # Wait for factory reset
        
        # CRITICAL: Re-send header commands after factory reset
        self.inst.scope_write("*CLS")
        self.inst.scope_write("HEADer OFF")
        self.inst.scope_write("VERBose OFF")
        self._log("Header OFF, Verbose OFF")
        
        # Turn off other channels (support up to 8)
        for c in range(1, 9):
            if c != ch:
                try:
                    self.inst.scope_write(f"DISplay:WAVEView1:CH{c}:STATE OFF")
                except:
                    pass  # Channel may not exist on this scope
        
        # Enable channel
        self.inst.scope_write(f"DISplay:WAVEView1:CH{ch}:STATE ON")
        
        # Set channel to 50 ohm termination (proper for antennas/coax) and FULL bandwidth
        # MSO4/5/6 has 1 GHz capture bandwidth - can scan full range in one step
        self.inst.scope_write(f"CH{ch}:TERmination 50")
        self.inst.scope_write(f"CH{ch}:BANdwidth FULL")
        self._log(f"CH{ch}: 50Ω termination, FULL bandwidth for SpectrumView")
        
        # Set initial vertical scale - will be auto-adjusted for clipping
        self.inst.scope_write(f"CH{ch}:SCAle 0.1")  # 100mV/div initial
        
        # Set trigger to measurement channel, edge, 0V
        self.inst.scope_write(f"TRIGger:A:EDGE:SOUrce CH{ch}")
        self.inst.scope_write("TRIGger:A:TYPE EDGE")
        self.inst.scope_write("TRIGger:A:EDGE:SLOpe RISe")
        self.inst.scope_write(f"TRIGger:A:LEVel:CH{ch} 0")
        self.inst.scope_write("TRIGger:A:MODe AUTO")
        self._log(f"Trigger: CH{ch} edge at 0V, AUTO mode")
        
        # Set timebase - 1ms/div for SpectrumView
        self.inst.scope_write("HORizontal:SCAle 1e-3")
        self._log("Horizontal: 1 ms/div")
        
        # Acquisition mode should be SAMple (not Average - that's for time domain)
        self.inst.scope_write("ACQuire:MODe SAMple")
        self._log("Acquisition: Sample mode")
        
        # Check for clipping and auto-adjust vertical scale
        self._auto_scale_for_no_clipping(ch)
        
        # Enable SpectrumView
        self.inst.scope_write(f"CH{ch}:SV:STATE ON")
        
        # Display Normal trace AND Average trace
        self.inst.scope_write(f"SV:CH{ch}:SELect:RF_NORMal ON")
        
        # Configure SpectrumView averaging (this is in the SV menu, not ACQuire)
        self.inst.scope_write(f"SV:CH{ch}:RF_AVErage:NUMAVg 256")
        self.inst.scope_write(f"SV:CH{ch}:SELect:RF_AVErage ON")
        self._log("SpectrumView Average: 256 acquisitions")
        
        # Set Span:RBW ratio to 10000:1 for better frequency resolution
        self.inst.scope_write("SV:RBWMode AUTO")
        self.inst.scope_write("SV:SPANRBWRatio 10000")
        self._log("Span:RBW ratio: 10000:1 (better resolution)")
        
        # Configure peak detection
        self.inst.scope_write("SV:MARKER:PEAK:STATE ON")
        self.inst.scope_write(f"SV:MARKER:PEAK:MAXimum {self.NUM_PEAKS}")
        self.inst.scope_write(f"SV:MARKER:PEAK:THReshold {self.PEAK_THRESHOLD}")
        self.inst.scope_write(f"SV:MARKER:PEAK:EXCURsion {self.PEAK_EXCURSION}")
        self.inst.scope_write("SV:MARKER:TYPe ABSolute")
        
        # Set units to dBm
        self.inst.scope_write(f"SV:CH{ch}:UNIts DBM")
        
        self._log("SpectrumView configured")
    
    def set_frequency_range(self, center_freq: float, span: float, ch: int):
        """Set center frequency and span"""
        self.inst.scope_write(f"CH{ch}:SV:CENTERFrequency {center_freq}")
        self.inst.scope_write(f"SV:SPAN {span}")
    
    def get_peaks(self) -> List[PeakSignal]:
        """Query current peak markers"""
        peaks = []
        try:
            freq_response = self.inst.scope_query("SV:MARKER:PEAKS:FREQuency?")
            amp_response = self.inst.scope_query("SV:MARKER:PEAKS:AMPLITUDE?")
            
            if freq_response and amp_response:
                # Strip quotes and whitespace from response (scope returns quoted strings)
                # Response format: "776.7526E+6,779.7473E+6,..." - need to remove all quotes
                freq_str = freq_response.strip().replace('"', '').replace("'", "")
                amp_str = amp_response.strip().replace('"', '').replace("'", "")
                
                # Parse comma-separated values
                freqs = []
                for f in freq_str.split(','):
                    f = f.strip()
                    if f:
                        try:
                            freqs.append(float(f))
                        except ValueError:
                            self._log(f"Could not parse frequency: {f}")
                
                amps = []
                for a in amp_str.split(','):
                    a = a.strip()
                    if a:
                        try:
                            amps.append(float(a))
                        except ValueError:
                            self._log(f"Could not parse amplitude: {a}")
                
                for freq, amp in zip(freqs, amps):
                    if freq > 0 and amp > -999:
                        peak = PeakSignal(
                            frequency_hz=freq,
                            amplitude_dbm=amp,
                            band_name=self._identify_band(freq)
                        )
                        peaks.append(peak)
                        self._log(f"  Peak: {peak.format_frequency()} @ {peak.amplitude_dbm:.1f} dBm ({peak.band_name})")
        except Exception as e:
            self._log(f"Error reading peaks: {e}")
        return peaks
    
    def _deduplicate_peaks(self, new_peaks: List[PeakSignal], window_hz: float = 100e3) -> None:
        """Add new peaks to all_peaks, deduplicating within frequency window.
        
        Args:
            new_peaks: List of new peaks to merge
            window_hz: Frequency window for deduplication (default 100 kHz to preserve 
                       close FM stations while removing true duplicates from overlapping scans)
        """
        for peak in new_peaks:
            is_dup = False
            for existing in self.all_peaks:
                if abs(existing.frequency_hz - peak.frequency_hz) < window_hz:
                    # Keep the stronger signal
                    if peak.amplitude_dbm > existing.amplitude_dbm:
                        self.all_peaks.remove(existing)
                    else:
                        is_dup = True
                    break
            if not is_dup:
                self.all_peaks.append(peak)
    
    def run_scan(self, ch: int, start_mhz: float, stop_mhz: float, output_dir: Path):
        """Run spectrum scan.
        
        In reference mode, analyzes the static reference waveform's spectrum
        without any acquisition or frequency stepping.
        """
        self.is_running = True
        self.should_stop = False
        self.all_peaks = []
        self.output_dir = output_dir  # Store for screenshot capture
        
        # Check for reference mode
        ref_mode = self._is_ref_mode(0)
        source = self._get_source(ch)  # REF{ch} or CH{ch}
        
        tp = self.test_points[0] if self.test_points else None
        if tp:
            tp.status = TestStatus.RUNNING
            if self.on_test_start:
                self.on_test_start(tp)
        
        try:
            if ref_mode:
                # REFERENCE MODE: Analyze static waveform - no acquisition!
                self._log("=" * 50)
                self._log(f"REFERENCE MODE: Analyzing spectrum of {source}")
                self._log("Skipping frequency sweep (static waveform)")
                self._log("=" * 50)
                
                # Minimal setup
                self.inst.scope_write("*CLS")
                self.inst.scope_write("HEADer OFF")
                self.inst.scope_write("VERBose OFF")
                
                # Enable REF display
                self.inst.scope_write(f'DISplay:GLObal:{source}:STATE ON')
                
                # Configure spectrum view on reference channel
                self._configure_ref_spectrum_view(ch, source)
                
                # No acquisition - just wait for spectrum to compute
                self._log("Computing spectrum from reference waveform...")
                time.sleep(1.0)
                
                # Get peaks from single spectrum
                peaks = self.get_peaks()
                self._deduplicate_peaks(peaks, window_hz=100e3)
                
                # Sort by amplitude
                self.all_peaks.sort(key=lambda p: p.amplitude_dbm, reverse=True)
                
                self._log(f"\n=== Analysis Complete: {len(self.all_peaks)} peaks found ===")
                self._log("Top 10 Signals:")
                for i, peak in enumerate(self.all_peaks[:10], 1):
                    self._log(f"  {i}. {peak.format_frequency():>15} @ {peak.amplitude_dbm:>7.1f} dBm [{peak.band_name}]")
                
                # Capture screenshot
                screenshot_path = self._capture_spectrum_screenshot(ch, output_dir)
                
                # Update test point
                if tp:
                    tp.measured_value = len(self.all_peaks)
                    tp.extra_data['peaks'] = self.all_peaks[:10]
                    tp.extra_data['reference_mode'] = True
                    tp.extra_data['source'] = source
                    tp.status = TestStatus.PASS
                    if screenshot_path:
                        tp.screenshot_path = screenshot_path
                    if self.on_test_complete:
                        self.on_test_complete(tp)
                        
            else:
                # LIVE MODE: Normal frequency sweep with acquisitions
                
                # Determine scope model and minimum bandwidth
                scope_model = ""
                min_bandwidth_mhz = 200  # Default to MSO4 minimum
                try:
                    idn = self.inst.scope_query("*IDN?")
                    if idn:
                        parts = idn.split(",")
                        if len(parts) >= 2:
                            scope_model = parts[1].strip().upper()
                            if "MSO6" in scope_model or "MSO68" in scope_model:
                                min_bandwidth_mhz = 1000  # 1 GHz
                            elif "MSO5" in scope_model or "MSO58" in scope_model:
                                min_bandwidth_mhz = 350
                            else:
                                min_bandwidth_mhz = 200  # MSO4 or other
                            self._log(f"Scope: {scope_model}, minimum bandwidth: {min_bandwidth_mhz} MHz")
                except:
                    pass
                
                # Only query bandwidth license if requested stop exceeds model minimum
                if stop_mhz > min_bandwidth_mhz:
                    self.scope_bandwidth_mhz = self._query_scope_bandwidth_mhz()
                    if self.scope_bandwidth_mhz:
                        if stop_mhz > self.scope_bandwidth_mhz:
                            self._log(f"⚠️ Requested stop ({stop_mhz:.0f} MHz) exceeds scope bandwidth ({self.scope_bandwidth_mhz} MHz)")
                            self._log(f"   Capping stop frequency to {self.scope_bandwidth_mhz} MHz")
                            stop_mhz = float(self.scope_bandwidth_mhz)
                    else:
                        self._log("Could not determine scope bandwidth from licenses - using requested range")
                else:
                    self._log(f"Scan range ({stop_mhz:.0f} MHz) within model minimum ({min_bandwidth_mhz} MHz) - no bandwidth check needed")
                
                self.configure_spectrum_view(ch)
                
                start_hz = start_mhz * 1e6
                stop_hz = stop_mhz * 1e6
                span = self.SPAN_PER_STEP
                overlap = span * 0.1
                
                # Calculate scan steps
                current_center = start_hz + span / 2
                scan_steps = []
                while current_center - span / 2 < stop_hz:
                    scan_steps.append(current_center)
                    current_center += span - overlap
                
                total_steps = len(scan_steps)
                self._log(f"Scan: {total_steps} steps, {span/1e6:.0f} MHz span each")
                
                for i, center_freq in enumerate(scan_steps):
                    if self.should_stop:
                        self._log("Scan stopped")
                        break
                    
                    progress = (i + 1) / total_steps * 100
                    start_f = max(0, center_freq - span/2)
                    stop_f = center_freq + span/2
                    
                    if self.on_progress:
                        self.on_progress(progress, f"Scanning {start_f/1e6:.0f}-{stop_f/1e6:.0f} MHz...")
                    
                    self._log(f"Step {i+1}/{total_steps}: {start_f/1e6:.0f}-{stop_f/1e6:.0f} MHz")
                    
                    self.set_frequency_range(center_freq, span, ch)
                    time.sleep(self.SETTLE_TIME)
                    
                    # Trigger acquisition
                    self.inst.scope_write("ACQuire:STOPAfter SEQuence")
                    self.inst.scope_write("ACQuire:STATE RUN")
                    self.inst.scope_wait_acquisition(timeout=5)
                    
                    # Get peaks and deduplicate (100 kHz window to preserve close FM stations)
                    peaks = self.get_peaks()
                    self._deduplicate_peaks(peaks, window_hz=100e3)
                
                # Sort by amplitude
                self.all_peaks.sort(key=lambda p: p.amplitude_dbm, reverse=True)
                
                self._log(f"\n=== Scan Complete: {len(self.all_peaks)} peaks found ===")
                self._log("Top 10 Signals:")
                for i, peak in enumerate(self.all_peaks[:10], 1):
                    self._log(f"  {i}. {peak.format_frequency():>15} @ {peak.amplitude_dbm:>7.1f} dBm [{peak.band_name}]")
                
                # Capture screenshot with markers and table visible
                screenshot_path = self._capture_spectrum_screenshot(ch, output_dir)
                
                # Update test point
                if tp:
                    tp.measured_value = len(self.all_peaks)
                    tp.extra_data['peaks'] = self.all_peaks[:10]
                    tp.status = TestStatus.PASS
                    if screenshot_path:
                        tp.screenshot_path = screenshot_path
                    if self.on_test_complete:
                        self.on_test_complete(tp)
        
        except Exception as e:
            self._log(f"Scan error: {e}")
            if tp:
                tp.status = TestStatus.ERROR
                if self.on_test_complete:
                    self.on_test_complete(tp)
        
        finally:
            self.is_running = False
            if self.on_complete:
                self.on_complete(1 if tp and tp.status == TestStatus.PASS else 0, 
                               0 if tp and tp.status == TestStatus.PASS else 1)
    
    def _configure_ref_spectrum_view(self, ch: int, source: str):
        """Configure spectrum view for reference waveform analysis.
        
        Args:
            ch: Channel number (used for SV settings)
            source: Reference source like 'REF1'
        """
        self._log(f"Configuring spectrum view on {source}...")
        
        # Enable Spectrum View on the reference channel
        # Note: SV works on CH, but we can view the REF waveform's spectrum
        self.inst.scope_write(f"CH{ch}:SV:STATE ON")
        
        # Configure spectrum view settings
        self.inst.scope_write(f"SV:CH{ch}:SELect:RF AVG")
        self.inst.scope_write(f"SV:CH{ch}:UNIts DBM")
        
        # Set a reasonable span for viewing
        self.inst.scope_write(f"SV:CH{ch}:SPAN 500e6")  # 500 MHz span
        
        self._log("Spectrum view configured for reference analysis")
    
    def _capture_spectrum_screenshot(self, ch: int, output_dir: Path) -> str:
        """Capture screenshot with peak markers and table visible.
        
        Args:
            ch: Channel number used for spectrum view
            output_dir: Directory to save screenshot
            
        Returns:
            Path to saved screenshot, or empty string on failure
        """
        try:
            self._log("Capturing spectrum screenshot with markers...")
            
            # Enable peak markers display on the spectrum trace
            self.inst.scope_write("SV:MARKER:PEAK:STATE ON")
            self.inst.scope_write(f"SV:MARKER:PEAK:MAXimum {self.NUM_PEAKS}")
            
            # Add a peaks table to show results on screen
            # The table name must be a string like "TABLE1"
            try:
                self.inst.scope_write('PEAKSTABle:ADDNew "TABLE1"')
                self._log("Added peaks table to display")
            except Exception as e:
                self._log(f"Could not add peaks table: {e}")
            
            # Brief pause to let display update
            time.sleep(0.3)
            
            # Capture screenshot
            filename = "spectrum_scan_results.png"
            filepath = output_dir / filename
            
            scope_paths = [f"C:/Temp/{filename}", f"C:/{filename}"]
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
                self._log("Could not capture screenshot - all paths failed")
                return ""
            
            # Save locally
            with open(filepath, 'wb') as f:
                f.write(data)
            
            # Cleanup temp file on scope
            try:
                self.inst.scope_write(f'FILESystem:DELEte "{used_path}"')
            except:
                pass
            
            self._log(f"Screenshot saved: {filename}")
            
            # Notify UI
            if self.on_screenshot:
                self.on_screenshot(str(filepath))
            
            return str(filepath)
            
        except Exception as e:
            self._log(f"Screenshot error: {e}")
            return ""
    
    def run_sequence(self, ch: int, output_dir: Path, start_mhz: float = 80, stop_mhz: float = 120):
        """Run the scan sequence"""
        self.run_scan(ch, start_mhz, stop_mhz, output_dir)
    
    def stop(self):
        self.should_stop = True


class EyeDiagramTestEngine:
    """
    Eye Diagram Test Engine for Tektronix MSO4/5/6/7 Series Oscilloscopes.
    
    Performs eye diagram measurements including:
    - Eye Height (voltage opening)
    - Eye Width (timing opening)
    - Statistical analysis over multiple acquisitions
    
    Uses global clock recovery settings and TIE measurement for eye diagram generation.
    """
    
    def __init__(self, inst: InstrumentManager):
        self.inst = inst
        self.test_points: List[TestPoint] = []
        self.is_running = False
        self.should_stop = False
        
        # Callbacks (same pattern as other engines)
        self.on_log = None
        self.on_test_start = None
        self.on_test_complete = None
        self.on_progress = None
        self.on_screenshot = None
        self.on_complete = None
        self.reference_config: Optional[ReferenceConfig] = None  # Reference mode config
        
        # Test parameters
        self.data_rate_bps = 1.62e9  # Default: DisplayPort RBR
        self.num_acquisitions = 1    # Default: single long acquisition (10 µs/div captures many bits)
        self.expected_vpp = 0.650  # 650 mV
        self.expected_offset = 0.350  # 350 mV
        self.selected_pll = ""
        
        # Pass/Fail limits (None = no limit)
        self.eye_height_min = None  # Volts (e.g., 0.200 = 200 mV)
        self.eye_height_max = None  # Volts
        self.eye_width_min = None   # Seconds (e.g., 100e-12 = 100 ps)
        self.eye_width_max = None   # Seconds
        self.pattern_length_expected = None  # Expected pattern length in bits (e.g., 127 for PRBS7)
        
        # Results storage
        self.eye_height_data = None
        self.eye_width_data = None
        self.pattern_length_data = None
        self.data_rate_data = None
        self.dj_data = None  # Deterministic Jitter
    
    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)

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
    
    def stop(self):
        self.should_stop = True
    
    def select_optimal_pll(self) -> str:
        """Select the PLL option closest to the target data rate."""
        target_rate = self.data_rate_bps
        best_pll = None
        best_diff = float('inf')
        
        for pll_name, (nominal_rate, _, _) in PLL_OPTIONS.items():
            diff = abs(nominal_rate - target_rate)
            if diff < best_diff:
                best_diff = diff
                best_pll = pll_name
        
        self.selected_pll = best_pll
        rate_gbps = PLL_OPTIONS[best_pll][0] / 1e9
        self._log(f"Selected PLL: {best_pll} (nominal rate: {rate_gbps:.3f} Gbps)")
        return best_pll
    
    def calculate_optimal_scale(self) -> float:
        """Calculate optimal vertical scale. Target: Signal fills 80-90% of dynamic range (8 divisions)."""
        # 10 divisions total, want signal to fill ~8 divisions (80%)
        target_divisions = 8
        optimal_scale = self.expected_vpp / target_divisions
        
        # Round to nearest standard scale value
        standard_scales = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 
                          0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
        
        for scale in standard_scales:
            if scale >= optimal_scale:
                return scale
        return standard_scales[-1]
    
    def generate_test_points(self) -> List[TestPoint]:
        """Generate single test point for eye diagram measurement."""
        self.test_points = []
        
        # Create a single test point for the eye diagram measurement
        tp = TestPoint(
            test_id=1,
            name=f"Eye Diagram @ {self.data_rate_bps/1e9:.3f} Gbps",
            nominal_value=self.data_rate_bps,
            unit="bps",
            tolerance_pct=0,
            has_limits=False,  # No pass/fail for now
            enabled=True
        )
        self.test_points.append(tp)
        return self.test_points
    
    def configure_channel(self, ch: int):
        """Configure the input channel for the expected signal."""
        self._log(f"Configuring Channel {ch} for eye diagram...")
        
        # Turn off other channels, enable measurement channel (support up to 8)
        for c in range(1, 9):
            if c != ch:
                try:
                    self.inst.scope_write(f"DISplay:WAVEView1:CH{c}:STATE OFF")
                except:
                    pass  # Channel may not exist on this scope
        self.inst.scope_write(f"DISplay:WAVEView1:CH{ch}:STATE ON")
        
        # Set termination (50 ohm for high-speed signals via SMA)
        self.inst.scope_write(f"CH{ch}:TERmination 50")
        self._log(f"CH{ch} termination: 50Ω")
        
        # Set DC coupling
        self.inst.scope_write(f"CH{ch}:COUPling DC")
        
        # Set bandwidth to full for high-speed signals
        self.inst.scope_write(f"CH{ch}:BANdwidth FULL")
        
        # Calculate and set optimal vertical scale
        optimal_scale = self.calculate_optimal_scale()
        self.inst.scope_write(f"CH{ch}:SCAle {optimal_scale}")
        self._log(f"CH{ch} scale: {optimal_scale*1000:.1f} mV/div")
        
        # Set offset to center the signal
        self.inst.scope_write(f"CH{ch}:OFFSet {self.expected_offset}")
        self._log(f"CH{ch} offset: {self.expected_offset*1000:.1f} mV")
        
        # Center the waveform vertically
        self.inst.scope_write(f"CH{ch}:POSition 0")
    
    def auto_adjust_vertical(self, ch: int):
        """Auto-adjust vertical scale based on actual signal.
        
        Target: Signal Vpp should be 80-90% of dynamic range.
        If clipping, adjust offset until centered, then issue *CLS to clear old data.
        """
        self._log("Auto-adjusting vertical settings...")
        
        # Do a quick autoset to get signal on screen
        self.inst.scope_write("AUTOSet EXECute")
        self.inst.scope_opc(10)
        
        # Measure actual amplitude and offset
        self.inst.scope_write('MEASUrement:DELETEALL')
        self.inst.scope_write('MEASUrement:ADDNew "MEAS1"')
        self.inst.scope_write("MEASUrement:MEAS1:TYPe PK2PK")
        self.inst.scope_write(f"MEASUrement:MEAS1:SOUrce CH{ch}")
        self.inst.scope_write("MEASUrement:MEAS1:STATE ON")
        
        self.inst.scope_write('MEASUrement:ADDNew "MEAS2"')
        self.inst.scope_write("MEASUrement:MEAS2:TYPe MEAN")
        self.inst.scope_write(f"MEASUrement:MEAS2:SOUrce CH{ch}")
        self.inst.scope_write("MEASUrement:MEAS2:STATE ON")
        
        # Single acquisition
        self.inst.scope_write("ACQuire:STOPAfter SEQuence")
        self.inst.scope_write("ACQuire:STATE RUN")
        self.inst.scope_wait_acquisition(timeout=5)
        
        # Query amplitude and mean (DC offset)
        actual_amplitude = None
        actual_mean = None
        try:
            result = self.inst.scope_query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
            if result:
                actual_amplitude = float(result)
                if actual_amplitude > 0 and not math.isnan(actual_amplitude) and not math.isinf(actual_amplitude):
                    self.expected_vpp = actual_amplitude
                    
            result2 = self.inst.scope_query("MEASUrement:MEAS2:RESUlts:CURRentacq:MEAN?")
            if result2:
                actual_mean = float(result2)
                if not math.isnan(actual_mean) and not math.isinf(actual_mean):
                    self.expected_offset = actual_mean
        except Exception as e:
            self._log(f"Auto-adjust warning: {e}")
        
        # Set optimal scale for 80% of dynamic range
        if actual_amplitude:
            optimal_scale = self.calculate_optimal_scale()
            self.inst.scope_write(f"CH{ch}:SCAle {optimal_scale}")
            self._log(f"Adjusted scale to {optimal_scale*1000:.1f} mV/div (measured Vpp: {actual_amplitude*1000:.1f} mV)")
        
        # Set offset to center signal
        if actual_mean is not None:
            self.inst.scope_write(f"CH{ch}:OFFSet {actual_mean}")
            self._log(f"Adjusted offset to {actual_mean*1000:.1f} mV")
        
        # Check for clipping and adjust
        max_attempts = 3
        for attempt in range(max_attempts):
            # Quick acquisition to check
            self.inst.scope_write("ACQuire:STOPAfter SEQuence")
            self.inst.scope_write("ACQuire:STATE RUN")
            time.sleep(0.3)
            self.inst.scope_write("ACQuire:STATE STOP")
            
            clipping = self.inst.scope_query(f"CH{ch}:CLIPping?")
            if clipping and clipping.strip() == "1":
                self._log(f"Clipping detected (attempt {attempt+1}), adjusting...")
                current_scale = float(self.inst.scope_query(f"CH{ch}:SCAle?"))
                self.inst.scope_write(f"CH{ch}:SCAle {current_scale * 1.25}")
            else:
                self._log("No clipping - vertical setup complete")
                break
        
        # Clear status/data after scale adjustments (important for jitter measurements!)
        self.inst.scope_write("*CLS")
        
        # Delete temporary measurements
        self.inst.scope_write('MEASUrement:DELete "MEAS1"')
        self.inst.scope_write('MEASUrement:DELete "MEAS2"')
    
    def set_trigger_50_percent(self, ch: int):
        """Set trigger level to 50% of the signal amplitude."""
        self._log("Setting trigger to 50% level...")
        
        # Calculate 50% level (mid-point of signal)
        trigger_level = self.expected_offset
        
        # Set edge trigger on channel
        self.inst.scope_write("TRIGger:A:TYPe EDGE")
        self.inst.scope_write(f"TRIGger:A:EDGE:SOUrce CH{ch}")
        self.inst.scope_write("TRIGger:A:EDGE:SLOpe RISE")
        self.inst.scope_write(f"TRIGger:A:LEVel:CH{ch} {trigger_level}")
        self.inst.scope_write("TRIGger:A:MODe AUTO")
        
        self._log(f"Trigger level: {trigger_level*1000:.1f} mV")
    
    def setup_horizontal(self):
        """Configure horizontal timebase for eye diagram/jitter measurements.
        
        For jitter measurements, we need MANY unit intervals captured.
        For low GHz signals (1-5 Gbps), use 10-15 µs/div to capture thousands of UIs.
        """
        self._log("Configuring horizontal timebase for jitter...")
        
        # Calculate UI (unit interval) in seconds
        ui_seconds = 1.0 / self.data_rate_bps
        
        # For jitter/eye diagram, we need many UIs - use 10-15 µs/div for low GHz signals
        # At 1.62 Gbps: UI = 617 ps, 10 µs capture = ~16,000 UIs
        if self.data_rate_bps <= 5e9:
            time_per_div = 10e-6  # 10 µs/div for low GHz signals
        else:
            time_per_div = 5e-6   # 5 µs/div for higher rates
        
        num_uis = (time_per_div * 10) / ui_seconds  # UIs across full screen
        
        self.inst.scope_write(f"HORizontal:SCAle {time_per_div}")
        self._log(f"Horizontal scale: {time_per_div*1e6:.1f} µs/div ({num_uis:.0f} UIs captured)")
        
        # Maximize sample rate (scope may reduce it at longer time scales)
        self.inst.scope_write("HORizontal:SAMPLERate:ANALYZemode:MAXimum ON")
        
        # Set record length for sufficient data
        self.inst.scope_write("HORizontal:RECOrdlength 10000000")
    
    def setup_global_clock_recovery(self):
        """Configure global clock recovery settings for all measurements."""
        self._log("Configuring global clock recovery...")
        
        # Select optimal PLL bandwidth based on data rate
        pll_name = self.select_optimal_pll()
        pll_rate, pll_bw, _ = PLL_OPTIONS[pll_name]
        
        # Set global clock recovery method to PLL
        self.inst.scope_write("MEASUrement:CLOCKRecovery:METHod PLL")
        
        # Set data rate for nominal data rate recovery
        self.inst.scope_write(f"MEASUrement:CLOCKRecovery:DATARate {self.data_rate_bps}")
        
        # Set loop bandwidth
        self.inst.scope_write(f"MEASUrement:CLOCKRecovery:LOOPBandwidth {pll_bw}")
        
        # Use Type 2 PLL model (common for serial data)
        self.inst.scope_write("MEASUrement:CLOCKRecovery:MODel TYPE2")
        
        self._log(f"Global clock recovery: PLL, Rate={self.data_rate_bps/1e9:.3f} Gbps, BW={pll_bw/1e6:.1f} MHz")
    
    def setup_tie_measurement(self, ch: int, source: str = None):
        """Set up TIE (Time Interval Error) measurement - required for eye diagram.
        
        Args:
            ch: Channel number (used if source not specified)
            source: Explicit source like 'REF1' or 'CH1' (optional)
        """
        if source is None:
            source = self._get_source(ch)
        
        self._log(f"Setting up TIE measurement on {source}...")
        
        # Clear any existing measurements
        self.inst.scope_write('MEASUrement:DELETEALL')
        
        # Add TIE measurement (this is the base for eye diagram)
        self.inst.scope_write('MEASUrement:ADDNew "MEAS1"')
        self.inst.scope_write("MEASUrement:MEAS1:TYPe TIE")
        self.inst.scope_write(f"MEASUrement:MEAS1:SOUrce {source}")
        
        # Use global clock recovery settings
        self.inst.scope_write("MEASUrement:MEAS1:CLOCKRecovery:GLOBal 1")
        
        # Enable the measurement
        self.inst.scope_write("MEASUrement:MEAS1:STATE ON")
        
        self._log("TIE measurement configured (MEAS1)")
    
    def setup_eye_diagram_plot(self):
        """Create and configure the eye diagram plot."""
        self._log("Setting up eye diagram plot...")
        
        # Add eye diagram plot linked to TIE measurement
        self.inst.scope_write("PLOT:ADDNew \"PLOT1\"")
        self.inst.scope_write("PLOT:PLOT1:TYPe EYEDIAGRAM")
        self.inst.scope_write("PLOT:PLOT1:SOUrce1 MEAS1")
        
        # Show all bits
        self.inst.scope_write("PLOT:PLOT1:BITType ALLBits")
        
        self._log("Eye diagram plot configured (PLOT1)")
    
    def setup_eye_measurements(self, ch: int, source: str = None):
        """Configure eye diagram measurements: Height, Width, Pattern Length, Data Rate, DJ.
        
        Args:
            ch: Channel number (used if source not specified)
            source: Explicit source like 'REF1' or 'CH1' (optional)
        """
        if source is None:
            source = self._get_source(ch)
            
        self._log(f"Setting up eye measurements on {source}...")
        
        # Add Eye Height measurement (MEAS2)
        self.inst.scope_write('MEASUrement:ADDNew "MEAS2"')
        self.inst.scope_write("MEASUrement:MEAS2:TYPe HEIGHT")
        self.inst.scope_write(f"MEASUrement:MEAS2:SOUrce {source}")
        self.inst.scope_write("MEASUrement:MEAS2:CLOCKRecovery:GLOBal 1")
        self.inst.scope_write("MEASUrement:MEAS2:DISPlaystat:ENABle ON")
        self.inst.scope_write("MEASUrement:MEAS2:STATE ON")
        self._log("Eye Height measurement added (MEAS2)")
        
        # Add Eye Width measurement (MEAS3)
        self.inst.scope_write('MEASUrement:ADDNew "MEAS3"')
        self.inst.scope_write("MEASUrement:MEAS3:TYPe WIDTH")
        self.inst.scope_write(f"MEASUrement:MEAS3:SOUrce {source}")
        self.inst.scope_write("MEASUrement:MEAS3:CLOCKRecovery:GLOBal 1")
        self.inst.scope_write("MEASUrement:MEAS3:DISPlaystat:ENABle ON")
        self.inst.scope_write("MEASUrement:MEAS3:STATE ON")
        self._log("Eye Width measurement added (MEAS3)")
        
        # Add Pattern Length measurement (MEAS4)
        self.inst.scope_write('MEASUrement:ADDNew "MEAS4"')
        self.inst.scope_write("MEASUrement:MEAS4:TYPe PATTERNLENGTH")
        self.inst.scope_write(f"MEASUrement:MEAS4:SOUrce {source}")
        self.inst.scope_write("MEASUrement:MEAS4:CLOCKRecovery:GLOBal 1")
        self.inst.scope_write("MEASUrement:MEAS4:DISPlaystat:ENABle ON")
        self.inst.scope_write("MEASUrement:MEAS4:STATE ON")
        self._log("Pattern Length measurement added (MEAS4)")
        
        # Add Data Rate measurement (MEAS5)
        self.inst.scope_write('MEASUrement:ADDNew "MEAS5"')
        self.inst.scope_write("MEASUrement:MEAS5:TYPe DATARATE")
        self.inst.scope_write(f"MEASUrement:MEAS5:SOUrce {source}")
        self.inst.scope_write("MEASUrement:MEAS5:CLOCKRecovery:GLOBal 1")
        self.inst.scope_write("MEASUrement:MEAS5:DISPlaystat:ENABle ON")
        self.inst.scope_write("MEASUrement:MEAS5:STATE ON")
        self._log("Data Rate measurement added (MEAS5)")
        
        # Add Deterministic Jitter (DJ) measurement (MEAS6)
        self.inst.scope_write('MEASUrement:ADDNew "MEAS6"')
        self.inst.scope_write("MEASUrement:MEAS6:TYPe DJ")
        self.inst.scope_write(f"MEASUrement:MEAS6:SOUrce {source}")
        self.inst.scope_write("MEASUrement:MEAS6:CLOCKRecovery:GLOBal 1")
        self.inst.scope_write("MEASUrement:MEAS6:DISPlaystat:ENABle ON")
        self.inst.scope_write("MEASUrement:MEAS6:STATE ON")
        self._log("Deterministic Jitter (DJ) measurement added (MEAS6)")
        
        # Enable statistics collection
        self.inst.scope_write("MEASUrement:STATistics:STATE ON")
        
        # If using multiple acquisitions, set up population limiting
        # This ensures statistics are calculated correctly across acquisitions
        if self.num_acquisitions > 1:
            self._log(f"Configuring population limit to {self.num_acquisitions}")
            for meas_num in [2, 3, 4, 5, 6]:
                self.inst.scope_write(f"MEASUrement:MEAS{meas_num}:POPUlation:LIMIT:STATE ON")
                self.inst.scope_write(f"MEASUrement:MEAS{meas_num}:POPUlation:LIMIT:VALue {self.num_acquisitions}")
        
        self._log("Measurement statistics enabled")
    
    def run_acquisitions(self):
        """Run multiple acquisitions and collect statistics."""
        self._log(f"Starting {self.num_acquisitions} acquisitions...")
        
        # For eye diagram, use RUNSTop mode and let it run
        self.inst.scope_write("ACQuire:STOPAfter RUNSTop")
        
        # Clear previous data and start acquisition
        self.inst.scope_write("ACQuire:STATE STOP")
        time.sleep(0.3)
        self.inst.scope_write("ACQuire:STATE RUN")
        
        # Monitor progress by checking acquisition count
        start_time = time.time()
        timeout_seconds = 300  # 5 minute timeout
        last_acq_count = 0
        
        while not self.should_stop:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                self._log(f"WARNING: Acquisition timeout after {elapsed:.1f} seconds")
                break
            
            try:
                acq_count = int(self.inst.scope_query("ACQuire:NUMACq?"))
            except:
                acq_count = last_acq_count
            
            # Report progress
            if acq_count > 0:
                progress = min((acq_count / self.num_acquisitions) * 100, 100)
                if self.on_progress:
                    self.on_progress(progress, f"Acquiring: {acq_count}/{self.num_acquisitions}")
                
                if acq_count != last_acq_count and acq_count % 20 == 0:
                    self._log(f"Acquisition progress: {acq_count}")
                
                last_acq_count = acq_count
            
            # Stop when we have enough acquisitions
            if acq_count >= self.num_acquisitions:
                break
            
            time.sleep(0.2)
        
        # Stop acquisition
        self.inst.scope_write("ACQuire:STATE STOP")
        time.sleep(0.3)
        
        total_time = time.time() - start_time
        self._log(f"Acquisitions completed in {total_time:.1f} seconds ({last_acq_count} acquisitions)")
    
    def query_measurement_statistics(self):
        """Query all eye diagram measurement statistics from scope."""
        self._log("Collecting measurement statistics...")
        
        # Query Eye Height statistics (MEAS2)
        try:
            eh_mean = self.inst.scope_query("MEASUrement:MEAS2:RESUlts:ALLAcqs:MEAN?")
            eh_min = self.inst.scope_query("MEASUrement:MEAS2:RESUlts:ALLAcqs:MINimum?")
            eh_max = self.inst.scope_query("MEASUrement:MEAS2:RESUlts:ALLAcqs:MAXimum?")
            eh_stddev = self.inst.scope_query("MEASUrement:MEAS2:RESUlts:ALLAcqs:STDDev?")
            
            if eh_mean and eh_min and eh_max:
                self.eye_height_data = {
                    'current': float(eh_mean),
                    'mean': float(eh_mean),
                    'min': float(eh_min),
                    'max': float(eh_max),
                    'std_dev': float(eh_stddev) if eh_stddev else 0
                }
                self._log(f"Eye Height - Mean: {float(eh_mean)*1000:.2f} mV, "
                         f"Min: {float(eh_min)*1000:.2f} mV, Max: {float(eh_max)*1000:.2f} mV")
        except Exception as e:
            self._log(f"Failed to get eye height results: {e}")
            self.eye_height_data = None
        
        # Query Eye Width statistics (MEAS3)
        try:
            ew_mean = self.inst.scope_query("MEASUrement:MEAS3:RESUlts:ALLAcqs:MEAN?")
            ew_min = self.inst.scope_query("MEASUrement:MEAS3:RESUlts:ALLAcqs:MINimum?")
            ew_max = self.inst.scope_query("MEASUrement:MEAS3:RESUlts:ALLAcqs:MAXimum?")
            ew_stddev = self.inst.scope_query("MEASUrement:MEAS3:RESUlts:ALLAcqs:STDDev?")
            
            if ew_mean and ew_min and ew_max:
                self.eye_width_data = {
                    'current': float(ew_mean),
                    'mean': float(ew_mean),
                    'min': float(ew_min),
                    'max': float(ew_max),
                    'std_dev': float(ew_stddev) if ew_stddev else 0
                }
                # Calculate %UI
                ui_seconds = 1.0 / self.data_rate_bps
                eye_width_ui = (float(ew_mean) / ui_seconds) * 100
                self._log(f"Eye Width - Mean: {float(ew_mean)*1e12:.2f} ps ({eye_width_ui:.1f}% UI), "
                         f"Min: {float(ew_min)*1e12:.2f} ps, Max: {float(ew_max)*1e12:.2f} ps")
        except Exception as e:
            self._log(f"Failed to get eye width results: {e}")
            self.eye_width_data = None
        
        # Query Pattern Length (MEAS4)
        try:
            pl_mean = self.inst.scope_query("MEASUrement:MEAS4:RESUlts:ALLAcqs:MEAN?")
            
            if pl_mean:
                pl_value = float(pl_mean)
                # Pattern length should be a whole number (e.g., 127 for PRBS7)
                if pl_value > 0 and not math.isnan(pl_value) and not math.isinf(pl_value):
                    self.pattern_length_data = {
                        'mean': pl_value,
                        'value': int(round(pl_value))  # Round to nearest integer
                    }
                    self._log(f"Pattern Length: {int(round(pl_value))} bits")
                else:
                    self.pattern_length_data = None
        except Exception as e:
            self._log(f"Failed to get pattern length: {e}")
            self.pattern_length_data = None
        
        # Query Data Rate (MEAS5) - returns bits per second
        try:
            dr_mean = self.inst.scope_query("MEASUrement:MEAS5:RESUlts:ALLAcqs:MEAN?")
            dr_min = self.inst.scope_query("MEASUrement:MEAS5:RESUlts:ALLAcqs:MINimum?")
            dr_max = self.inst.scope_query("MEASUrement:MEAS5:RESUlts:ALLAcqs:MAXimum?")
            dr_stddev = self.inst.scope_query("MEASUrement:MEAS5:RESUlts:ALLAcqs:STDDev?")
            
            if dr_mean:
                dr_value = float(dr_mean)
                if dr_value > 0 and not math.isnan(dr_value) and not math.isinf(dr_value):
                    self.data_rate_data = {
                        'mean': dr_value,
                        'min': float(dr_min) if dr_min else dr_value,
                        'max': float(dr_max) if dr_max else dr_value,
                        'std_dev': float(dr_stddev) if dr_stddev else 0
                    }
                    self._log(f"Data Rate - Mean: {dr_value/1e9:.6f} Gbps")
                else:
                    self.data_rate_data = None
        except Exception as e:
            self._log(f"Failed to get data rate results: {e}")
            self.data_rate_data = None
        
        # Query Deterministic Jitter DJ (MEAS6) - returns seconds
        try:
            dj_mean = self.inst.scope_query("MEASUrement:MEAS6:RESUlts:ALLAcqs:MEAN?")
            dj_min = self.inst.scope_query("MEASUrement:MEAS6:RESUlts:ALLAcqs:MINimum?")
            dj_max = self.inst.scope_query("MEASUrement:MEAS6:RESUlts:ALLAcqs:MAXimum?")
            dj_stddev = self.inst.scope_query("MEASUrement:MEAS6:RESUlts:ALLAcqs:STDDev?")
            
            if dj_mean:
                dj_value = float(dj_mean)
                if dj_value >= 0 and not math.isnan(dj_value) and not math.isinf(dj_value) and abs(dj_value) < 1e30:
                    self.dj_data = {
                        'mean': dj_value,
                        'min': float(dj_min) if dj_min else dj_value,
                        'max': float(dj_max) if dj_max else dj_value,
                        'std_dev': float(dj_stddev) if dj_stddev else 0
                    }
                    self._log(f"Deterministic Jitter (DJ) - Mean: {dj_value*1e12:.2f} ps")
                else:
                    self.dj_data = None
        except Exception as e:
            self._log(f"Failed to get DJ results: {e}")
            self.dj_data = None
    
    def capture_screenshot(self, test_id: int, output_dir: Path) -> str:
        """Capture eye diagram screenshot."""
        try:
            filename = f"eye_diagram_{test_id:03d}.png"
            local_path = output_dir / filename
            
            # Try multiple scope paths - C:/Temp preferred, C:/ as fallback
            scope_paths = [f"C:/Temp/eye_{test_id}.png", f"C:/eye_{test_id}.png"]
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
                self._log("Screenshot error: all scope paths failed")
                return ""
            
            with open(local_path, 'wb') as f:
                f.write(data)
            
            # Delete temp file from scope
            try:
                self.inst.scope_write(f'FILESystem:DELEte "{used_path}"')
            except:
                pass
            
            self._log(f"Screenshot saved: {filename}")
            return str(local_path)
            
        except Exception as e:
            self._log(f"Screenshot error: {e}")
            return ""
    
    def run_sequence(self, ch: int, screenshot_dir: Path):
        """
        Execute the complete eye diagram test sequence.
        
        Args:
            ch: Oscilloscope channel number
            screenshot_dir: Path for saving screenshots
        """
        self.is_running = True
        self.should_stop = False
        passed = 0
        failed = 0
        
        # Check if using reference mode (static pre-captured waveform)
        ref_mode = self._is_ref_mode(0)
        source = self._get_source(ch)  # Returns REF{ch} or CH{ch}
        
        try:
            tp = self.test_points[0]
            tp.status = TestStatus.RUNNING
            if self.on_test_start:
                self.on_test_start(tp)
            
            if ref_mode:
                # REFERENCE MODE: Waveform is already captured - NO acquisition!
                self._log(f"Reference mode: Using pre-captured waveform on {source}")
                self._log("Skipping all acquisition steps (static waveform)")
                
                # Minimal scope setup - just clear and configure headers
                self.inst.scope_write("*CLS")
                self.inst.scope_write("HEADer OFF")
                self.inst.scope_write("VERBose OFF")
                
                # Make sure REF waveform is visible
                self.inst.scope_write(f'DISplay:GLObal:{source}:STATE ON')
                
                # Setup global clock recovery (still needed for measurements)
                self.setup_global_clock_recovery()
                
                # Setup measurements on the reference waveform
                self.setup_tie_measurement(ch, source)
                self.setup_eye_diagram_plot()
                self.setup_eye_measurements(ch, source)
                
                # NO acquisitions for reference waveforms - data is static!
                # Just wait briefly for measurements to process the existing waveform
                self._log("Processing reference waveform (no acquisition)...")
                time.sleep(1.0)
                
            else:
                # LIVE CHANNEL MODE: Normal acquisition sequence
                self._log(f"Live mode: Acquiring from {source}")
                
                # Reset scope to known state
                self._log("Resetting oscilloscope...")
                self.inst.scope_write("FACtory")
                self.inst.scope_opc(30)
                self.inst.scope_write("*CLS")
                self.inst.scope_write("HEADer OFF")
                self.inst.scope_write("VERBose OFF")
                
                # Configure channel
                self.configure_channel(ch)
                
                # Auto-adjust vertical
                self.auto_adjust_vertical(ch)
                
                # Set trigger
                self.set_trigger_50_percent(ch)
                
                # Configure horizontal
                self.setup_horizontal()
                
                # Setup global clock recovery (used by all jitter measurements)
                self.setup_global_clock_recovery()
                
                # Setup TIE measurement (required for eye diagram)
                self.setup_tie_measurement(ch, source)
                
                # Setup eye diagram plot
                self.setup_eye_diagram_plot()
                
                # Setup eye height and width measurements
                self.setup_eye_measurements(ch, source)
                
                # Run acquisitions (only for live channels!)
                self.run_acquisitions()
            
            if self.should_stop:
                tp.status = TestStatus.SKIPPED
            else:
                # Get statistics
                self.query_measurement_statistics()
                
                # Store results in test point
                tp.extra_data['eye_height'] = self.eye_height_data
                tp.extra_data['eye_width'] = self.eye_width_data
                tp.extra_data['pattern_length'] = self.pattern_length_data
                tp.extra_data['data_rate_measured'] = self.data_rate_data  # Measured data rate
                tp.extra_data['dj'] = self.dj_data  # Deterministic jitter
                tp.extra_data['data_rate_bps'] = self.data_rate_bps  # Expected data rate
                tp.extra_data['num_acquisitions'] = self.num_acquisitions if not ref_mode else 1
                tp.extra_data['selected_pll'] = self.selected_pll
                tp.extra_data['reference_mode'] = ref_mode
                tp.extra_data['source'] = source
                
                # Store limits for display
                tp.extra_data['eye_height_limits'] = {
                    'min': self.eye_height_min,
                    'max': self.eye_height_max
                }
                tp.extra_data['eye_width_limits'] = {
                    'min': self.eye_width_min,
                    'max': self.eye_width_max
                }
                tp.extra_data['pattern_length_expected'] = self.pattern_length_expected
                
                # Calculate %UI for eye width
                if self.eye_width_data:
                    ui_seconds = 1.0 / self.data_rate_bps
                    tp.extra_data['eye_width_ui_pct'] = (self.eye_width_data['mean'] / ui_seconds) * 100
                
                # Determine pass/fail based on limits
                all_pass = True
                has_any_limits = False
                
                # Check eye height limits
                if self.eye_height_data and self.eye_height_data.get('mean'):
                    eh_mean = self.eye_height_data['mean']
                    if not (math.isnan(eh_mean) or math.isinf(eh_mean) or abs(eh_mean) > 1e30):
                        if self.eye_height_min is not None:
                            has_any_limits = True
                            if eh_mean < self.eye_height_min:
                                all_pass = False
                                self._log(f"FAIL: Eye Height {eh_mean*1000:.2f} mV < min {self.eye_height_min*1000:.1f} mV")
                        if self.eye_height_max is not None:
                            has_any_limits = True
                            if eh_mean > self.eye_height_max:
                                all_pass = False
                                self._log(f"FAIL: Eye Height {eh_mean*1000:.2f} mV > max {self.eye_height_max*1000:.1f} mV")
                
                # Check eye width limits
                if self.eye_width_data and self.eye_width_data.get('mean'):
                    ew_mean = self.eye_width_data['mean']
                    if not (math.isnan(ew_mean) or math.isinf(ew_mean) or abs(ew_mean) > 1e30):
                        if self.eye_width_min is not None:
                            has_any_limits = True
                            if ew_mean < self.eye_width_min:
                                all_pass = False
                                self._log(f"FAIL: Eye Width {ew_mean*1e12:.2f} ps < min {self.eye_width_min*1e12:.1f} ps")
                        if self.eye_width_max is not None:
                            has_any_limits = True
                            if ew_mean > self.eye_width_max:
                                all_pass = False
                                self._log(f"FAIL: Eye Width {ew_mean*1e12:.2f} ps > max {self.eye_width_max*1e12:.1f} ps")
                
                # Check pattern length (exact match required if specified)
                if self.pattern_length_expected is not None:
                    has_any_limits = True
                    if self.pattern_length_data and self.pattern_length_data.get('value'):
                        measured_pl = self.pattern_length_data['value']
                        if measured_pl != self.pattern_length_expected:
                            all_pass = False
                            self._log(f"FAIL: Pattern Length {measured_pl} != expected {self.pattern_length_expected}")
                        else:
                            self._log(f"PASS: Pattern Length {measured_pl} matches expected")
                    else:
                        all_pass = False
                        self._log("FAIL: Could not measure pattern length")
                
                # Set status
                if has_any_limits:
                    tp.status = TestStatus.PASS if all_pass else TestStatus.FAIL
                    passed = 1 if all_pass else 0
                    failed = 0 if all_pass else 1
                else:
                    tp.status = TestStatus.PASS  # No limits = always pass
                    passed = 1
                    failed = 0
                
                tp.measured_value = 1  # Indicates test completed
                
                # Capture screenshot
                tp.screenshot_path = self.capture_screenshot(tp.test_id, screenshot_dir)
                if self.on_screenshot and tp.screenshot_path:
                    self.on_screenshot(tp.screenshot_path)
            
            if self.on_test_complete:
                self.on_test_complete(tp)
                
        except Exception as e:
            self._log(f"Test error: {e}")
            if self.test_points:
                self.test_points[0].status = TestStatus.ERROR
                failed = 1
                if self.on_test_complete:
                    self.on_test_complete(self.test_points[0])
        
        finally:
            self.is_running = False
            if self.on_complete:
                self.on_complete(passed, failed)


# =============================================================================
# AGC SAMPLE TEST ENGINE
# =============================================================================

class AGCSampleTestEngine:
    """
    AGC Sample Test Engine for measuring delay, rise time, and fall time 
    between two channels using a two-view approach.
    
    View 1 - Timing View (wide horizontal):
      Shows 2+ signal cycles for delay, period, frequency, duty cycle measurements.
      H scale: ~5× expected delay / 10 divisions.
      Trigger: configured channel/edge (default: CH1 falling at 50%).
      
    View 2 - Edge View (zoomed per measurement):
      Zoomed in to see edge transitions clearly for rise/fall time.
      H scale: 0.5 × nominal rise/fall time (e.g., 100ns rise → 50ns/div).
      Trigger: 50% on the measured channel, matching edge direction.
        - Rise time: trigger on rising edge of that channel
        - Fall time: trigger on falling edge of that channel
      Each edge measurement gets its own acquisition and screenshot.
    
    Measurements:
    1. Delay from CH_from edge to CH_to edge (with pass/fail) [timing view]
    2. Rise Time CH_from (informational) [edge view]
    3. Rise Time CH_to (informational) [edge view]
    4. Fall Time CH_from (informational) [edge view]
    5. Fall Time CH_to (informational) [edge view]
    """
    
    # 1-2-5 horizontal scale sequence for nice scope values
    NICE_H_SCALES = [
        1e-12, 2e-12, 5e-12,
        10e-12, 20e-12, 50e-12, 100e-12, 200e-12, 500e-12,
        1e-9, 2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9, 500e-9,
        1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6, 200e-6, 500e-6,
        1e-3, 2e-3, 5e-3, 10e-3
    ]
    
    def __init__(self, inst: InstrumentManager):
        self.inst = inst
        self.test_points: List[TestPoint] = []
        self.is_running = False
        self.should_stop = False
        
        # Callbacks
        self.on_log = None
        self.on_test_start = None
        self.on_test_complete = None
        self.on_progress = None
        self.on_screenshot = None
        self.on_complete = None
        self.reference_config: Optional[ReferenceConfig] = None
        
        # Test configuration (defaults from specification)
        self.channel_from = 1       # CH1 - trigger/source channel
        self.channel_to = 3         # CH3 - measurement channel
        self.termination = 50       # 50 ohm for BNC/SMA
        self.signal_high = 2.5      # High level voltage (V)
        self.signal_low = 0.0       # Low level voltage (V)
        self.expected_rise_time = 100e-9   # 100 ns default
        self.expected_fall_time = 100e-9   # 100 ns default (often same as rise)
        self.expected_delay = 10e-6        # 10 µs
        self.delay_tolerance_pct = 5.0     # ±5% tolerance
        self.trigger_level = 1.25          # Trigger at 50% of signal (1.25V)
        self.trigger_slope = "FALL"        # Trigger on falling edge (timing view)
        self.horizontal_position = 10      # 10% position (timing view)
    
    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)

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
    
    def _nice_h_scale(self, target: float) -> float:
        """Round a horizontal scale to a nice 1-2-5 oscilloscope value."""
        return min((s for s in self.NICE_H_SCALES if s >= target), default=target)
    
    def stop(self):
        self.should_stop = True
    
    def generate_test_points(self) -> List[TestPoint]:
        """Generate test points for the AGC sample test.
        
        Creates timing-view measurements (delay) and edge-view measurements
        (rise time, fall time) for both channels.
        """
        self.test_points = []
        
        # Calculate limits for delay measurement
        lower_limit = self.expected_delay * (1 - self.delay_tolerance_pct / 100)
        upper_limit = self.expected_delay * (1 + self.delay_tolerance_pct / 100)
        
        # Test Point 1: Delay measurement (with pass/fail) [TIMING VIEW]
        tp_delay = TestPoint(
            test_id=1,
            name=f"Delay CH{self.channel_from}↓ to CH{self.channel_to}↑",
            nominal_value=self.expected_delay,
            unit="s",
            tolerance_pct=self.delay_tolerance_pct,
            has_limits=True,
            lower_limit=lower_limit,
            upper_limit=upper_limit,
            enabled=True,
            extra_data={'view': 'timing', 'meas_type': 'DELAY',
                       'source_ch': self.channel_from, 'edge': 'FALL'}
        )
        self.test_points.append(tp_delay)
        
        # Test Point 2: Rise Time CH_from (informational) [EDGE VIEW]
        tp_rise_ch1 = TestPoint(
            test_id=2,
            name=f"Rise Time CH{self.channel_from}",
            nominal_value=self.expected_rise_time,
            unit="s",
            tolerance_pct=0,
            has_limits=False,
            enabled=True,
            extra_data={'view': 'edge', 'meas_type': 'RISETIME',
                       'source_ch': self.channel_from, 'edge': 'RISE'}
        )
        self.test_points.append(tp_rise_ch1)
        
        # Test Point 3: Rise Time CH_to (informational) [EDGE VIEW]
        tp_rise_ch3 = TestPoint(
            test_id=3,
            name=f"Rise Time CH{self.channel_to}",
            nominal_value=self.expected_rise_time,
            unit="s",
            tolerance_pct=0,
            has_limits=False,
            enabled=True,
            extra_data={'view': 'edge', 'meas_type': 'RISETIME',
                       'source_ch': self.channel_to, 'edge': 'RISE'}
        )
        self.test_points.append(tp_rise_ch3)
        
        # Test Point 4: Fall Time CH_from (informational) [EDGE VIEW]
        tp_fall_ch1 = TestPoint(
            test_id=4,
            name=f"Fall Time CH{self.channel_from}",
            nominal_value=self.expected_fall_time,
            unit="s",
            tolerance_pct=0,
            has_limits=False,
            enabled=True,
            extra_data={'view': 'edge', 'meas_type': 'FALLTIME',
                       'source_ch': self.channel_from, 'edge': 'FALL'}
        )
        self.test_points.append(tp_fall_ch1)
        
        # Test Point 5: Fall Time CH_to (informational) [EDGE VIEW]
        tp_fall_ch3 = TestPoint(
            test_id=5,
            name=f"Fall Time CH{self.channel_to}",
            nominal_value=self.expected_fall_time,
            unit="s",
            tolerance_pct=0,
            has_limits=False,
            enabled=True,
            extra_data={'view': 'edge', 'meas_type': 'FALLTIME',
                       'source_ch': self.channel_to, 'edge': 'FALL'}
        )
        self.test_points.append(tp_fall_ch3)
        
        return self.test_points
    
    def configure_scope(self):
        """Configure oscilloscope channels (shared between both views)."""
        self._log("Resetting oscilloscope (FACtory)...")
        self.inst.scope_write("FACtory")
        self.inst.scope_opc(30)
        self.inst.scope_write("*CLS")
        self.inst.scope_write("HEADer OFF")
        self.inst.scope_write("VERBose OFF")
        
        self._configure_channels()
    
    def _configure_channels(self):
        """Configure CH1 and CH3 for the measurement."""
        ch1 = self.channel_from
        ch3 = self.channel_to
        
        # Turn off all channels first (support up to 8)
        for ch in range(1, 9):
            try:
                self.inst.scope_write(f"DISplay:WAVEView1:CH{ch}:STATE OFF")
            except:
                pass  # Channel may not exist on this scope
        
        # Enable CH1 and CH3
        self._log(f"Configuring CH{ch1} and CH{ch3}...")
        self.inst.scope_write(f"DISplay:WAVEView1:CH{ch1}:STATE ON")
        self.inst.scope_write(f"DISplay:WAVEView1:CH{ch3}:STATE ON")
        
        # Configure both channels identically
        for ch in [ch1, ch3]:
            self.inst.scope_write(f"CH{ch}:TERmination {self.termination}")
            self._log(f"CH{ch} termination: {self.termination}Ω")
            self.inst.scope_write(f"CH{ch}:COUPling DC")
            self.inst.scope_write(f"CH{ch}:BANdwidth FULL")
            
            # Calculate vertical scale (signal uses ~80% of screen)
            vpp = self.signal_high - self.signal_low
            target_scale = vpp / 6.4
            nice_scales = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 
                          0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
            scale = min((s for s in nice_scales if s >= target_scale), default=1.0)
            
            self.inst.scope_write(f"CH{ch}:SCAle {scale}")
            self._log(f"CH{ch} scale: {scale*1000:.0f} mV/div")
            
            # Set offset to center the signal
            v_center = (self.signal_high + self.signal_low) / 2
            self.inst.scope_write(f"CH{ch}:OFFSet {-v_center}")
            self.inst.scope_write(f"CH{ch}:POSition 0")
    
    def _configure_timing_view(self):
        """Configure scope for timing/delay view (wide horizontal scale).
        
        Shows 2+ signal cycles for delay, period, frequency, duty cycle.
        Trigger on configured channel/edge.
        """
        self._log("--- Configuring TIMING VIEW ---")
        
        # Trigger settings for timing view
        ch = self.channel_from
        self.inst.scope_write("TRIGger:A:TYPe EDGE")
        self.inst.scope_write(f"TRIGger:A:EDGE:SOUrce CH{ch}")
        self.inst.scope_write(f"TRIGger:A:EDGE:SLOpe {self.trigger_slope}")
        self.inst.scope_write(f"TRIGger:A:LEVel:CH{ch} {self.trigger_level}")
        self.inst.scope_write("TRIGger:A:MODe NORMal")
        self._log(f"Trigger: CH{ch} {self.trigger_slope} edge at {self.trigger_level}V")
        
        # Horizontal: capture about 5× the expected delay on screen
        target_scale = self.expected_delay * 5 / 10
        scale = self._nice_h_scale(target_scale)
        
        self.inst.scope_write(f"HORizontal:SCAle {scale}")
        self.inst.scope_write(f"HORizontal:POSition {self.horizontal_position}")
        self._log(f"Horizontal: {format_si(scale, 's')}/div (timing view)")
    
    def _configure_edge_view(self, tp: TestPoint):
        """Configure scope for rise/fall time measurement (zoomed edge view).
        
        Rule of thumb: H scale = 0.5 × nominal rise/fall time
        Trigger at 50% on the measured channel, matching edge direction:
          - Rise time → trigger on rising edge
          - Fall time → trigger on falling edge
        """
        source_ch = tp.extra_data.get('source_ch', self.channel_from)
        meas_type = tp.extra_data.get('meas_type', 'RISETIME')
        trigger_edge = tp.extra_data.get('edge', 'RISE')
        
        self._log(f"--- Configuring EDGE VIEW for {tp.name} ---")
        
        # Trigger: 50% amplitude on the measured channel, matching edge
        trigger_level = (self.signal_high + self.signal_low) / 2
        self.inst.scope_write(f"TRIGger:A:EDGE:SOUrce CH{source_ch}")
        self.inst.scope_write(f"TRIGger:A:EDGE:SLOpe {trigger_edge}")
        self.inst.scope_write(f"TRIGger:A:LEVel:CH{source_ch} {trigger_level}")
        self._log(f"Trigger: CH{source_ch} {trigger_edge} edge at {trigger_level}V")
        
        # H scale = 0.5 × nominal rise/fall time, rounded to nice 1-2-5 value
        target_h_scale = tp.nominal_value * 0.5
        h_scale = self._nice_h_scale(target_h_scale)
        
        self.inst.scope_write(f"HORizontal:SCAle {h_scale}")
        self.inst.scope_write("HORizontal:POSition 50")  # Center the edge
        self._log(f"Horizontal: {format_si(h_scale, 's')}/div (0.5 × {format_si(tp.nominal_value, 's')} nominal)")
    
    def _acquire(self, timeout: int = 10) -> bool:
        """Perform single acquisition and wait for completion."""
        self.inst.scope_write("ACQuire:STOPAfter SEQuence")
        self.inst.scope_write("ACQuire:STATE RUN")
        
        if not self.inst.scope_wait_acquisition(timeout=timeout):
            self._log("Warning: Acquisition timeout - forcing trigger")
            self.inst.scope_write("TRIGger FORCe")
            time.sleep(0.5)
            return False
        
        time.sleep(0.3)
        return True
    
    def _read_measurement(self, meas_name: str) -> Optional[float]:
        """Read a measurement result from the scope. Returns None on error."""
        try:
            result_str = self.inst.scope_query(f"MEASUrement:{meas_name}:RESUlts:CURRentacq:MEAN?")
            if result_str:
                val = float(result_str)
                if not math.isnan(val) and not math.isinf(val) and abs(val) < 1e30:
                    return val
        except Exception as e:
            self._log(f"Error reading {meas_name}: {e}")
        return None
    
    def _evaluate_test_point(self, tp: TestPoint, measured: Optional[float]) -> TestPoint:
        """Evaluate a test point given a measured value."""
        if measured is None:
            tp.status = TestStatus.ERROR
            return tp
        
        tp.measured_value = measured
        if tp.nominal_value > 0:
            tp.error_pct = ((measured - tp.nominal_value) / tp.nominal_value) * 100
        
        if tp.has_limits:
            if tp.lower_limit <= measured <= tp.upper_limit:
                tp.status = TestStatus.PASS
            else:
                tp.status = TestStatus.FAIL
        else:
            tp.status = TestStatus.PASS  # Informational - always pass
        
        self._log(f"  {tp.name}: {format_si(measured, 's')} "
                  f"(nominal: {format_si(tp.nominal_value, 's')}) [{tp.status.value}]")
        return tp
    
    def capture_screenshot(self, label: str, output_dir: Path) -> str:
        """Save screenshot from scope and transfer to local PC."""
        try:
            safe_label = label.replace(" ", "_").replace("↓", "fall").replace("↑", "rise")
            filename = f"agc_{safe_label}.png"
            local_path = output_dir / filename
            
            scope_paths = [f"C:/Temp/{filename}", f"C:/{filename}"]
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
                self._log("Screenshot error: all scope paths failed")
                return ""
            
            with open(local_path, 'wb') as f:
                f.write(data)
            
            try:
                self.inst.scope_write(f'FILESystem:DELEte "{used_path}"')
            except:
                pass
            
            self._log(f"Screenshot saved: {filename}")
            return str(local_path)
        except Exception as e:
            self._log(f"Screenshot error: {e}")
            return ""
    
    def run_sequence(self, output_dir: Path):
        """Run the complete AGC test with two-view approach.
        
        Pass 1 - Timing View:
          Wide H scale showing 2+ signal cycles.
          Measures: delay (period, frequency, duty cycle if configured).
          One acquisition, one screenshot.
          
        Pass 2 - Edge View:
          Zoomed H scale = 0.5 × nominal rise/fall time.
          Trigger: 50% on measured channel, matching edge direction.
          Separate acquisition + screenshot for each edge measurement.
          
        Reference Mode:
          When using reference waveforms, skip all acquisition and trigger
          configuration. Just set up measurements on REF channels and read.
        """
        self.is_running = True
        self.should_stop = False
        passed = 0
        failed = 0
        
        # Check if using reference mode (static pre-captured waveforms)
        all_ref_mode = all(self._is_ref_mode(tp.test_id) for tp in self.test_points if tp.enabled)
        
        try:
            if all_ref_mode:
                # REFERENCE MODE: Waveform is already captured - NO acquisition!
                self._log("=" * 50)
                self._log("REFERENCE MODE: Using pre-captured waveforms")
                self._log("Skipping all acquisition/trigger configuration")
                self._log("=" * 50)
                
                # Minimal scope setup - just headers
                self.inst.scope_write("*CLS")
                self.inst.scope_write("HEADer OFF")
                self.inst.scope_write("VERBose OFF")
                
                # Get REF sources
                src1 = self._get_source(self.channel_from, 0)  # REF1
                src2 = self._get_source(self.channel_to, 0)    # REF3
                
                # Turn on REF displays
                self.inst.scope_write(f'DISplay:GLObal:{src1}:STATE ON')
                self.inst.scope_write(f'DISplay:GLObal:{src2}:STATE ON')
                self._log(f"Enabled {src1} and {src2} displays")
                
                # Run all measurements without separate views - data is static
                self._run_reference_mode_tests(output_dir, src1, src2, passed, failed)
                
            else:
                # LIVE MODE: Normal two-view acquisition sequence
                # Configure channels (shared between views)
                self.configure_scope()
                if self.should_stop:
                    return
                
                # Separate test points by view type
                timing_tests = [tp for tp in self.test_points 
                               if tp.enabled and tp.extra_data.get('view') == 'timing']
                edge_tests = [tp for tp in self.test_points 
                             if tp.enabled and tp.extra_data.get('view') == 'edge']
                total = len(timing_tests) + len(edge_tests)
                done = 0
                
                # ==============================================================
                # PASS 1: TIMING VIEW - wide horizontal for delay measurements
                # ==============================================================
                if timing_tests:
                    self._log("=" * 50)
                    self._log("PASS 1: Timing View (wide horizontal)")
                    self._log("=" * 50)
                    
                    self._configure_timing_view()
                    
                    # Set up timing measurements
                    self.inst.scope_write("MEASUrement:DELETEALL")
                    for tp in timing_tests:
                        meas_name = f"MEAS{tp.test_id}"
                        src1 = f"CH{self.channel_from}"
                        src2 = f"CH{self.channel_to}"
                        
                        self.inst.scope_write(f'MEASUrement:ADDNew "{meas_name}"')
                        self.inst.scope_write(f"MEASUrement:{meas_name}:TYPe DELAY")
                        self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce1 {src1}")
                        self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce2 {src2}")
                        self.inst.scope_write(f"MEASUrement:{meas_name}:DELay:EDGE1 FALL")
                        self.inst.scope_write(f"MEASUrement:{meas_name}:DELay:EDGE2 RISE")
                        self.inst.scope_write(f"MEASUrement:{meas_name}:STATE ON")
                        self._log(f"  {meas_name}: DELAY {src1} FALL → {src2} RISE")
                    
                    if self.on_progress:
                        self.on_progress(15, "Acquiring (timing view)...")
                    
                    self._acquire(timeout=10)
                    
                    if self.should_stop:
                        return
                    
                    # Capture timing view screenshot
                    if output_dir:
                        screenshot_path = self.capture_screenshot("timing_view", output_dir)
                        if screenshot_path and self.on_screenshot:
                            self.on_screenshot(screenshot_path)
                    
                    # Read and evaluate timing measurements
                    for tp in timing_tests:
                        if self.should_stop:
                            break
                        
                        tp.status = TestStatus.RUNNING
                        if self.on_test_start:
                            self.on_test_start(tp)
                        
                        measured = self._read_measurement(f"MEAS{tp.test_id}")
                        self._evaluate_test_point(tp, measured)
                        
                        if tp.status == TestStatus.PASS:
                            passed += 1
                        elif tp.status in (TestStatus.FAIL, TestStatus.ERROR):
                            failed += 1
                        
                        if tp.screenshot_path == "" and output_dir:
                            tp.screenshot_path = str(output_dir / "agc_timing_view.png")
                        
                        if self.on_test_complete:
                            self.on_test_complete(tp)
                        
                        done += 1
                        if self.on_progress:
                            self.on_progress(15 + done / total * 70, f"Test {done}/{total}")
                
                # ==============================================================
                # PASS 2: EDGE VIEW - zoomed for each rise/fall time measurement
                # ==============================================================
                if edge_tests and not self.should_stop:
                    self._log("")
                    self._log("=" * 50)
                    self._log("PASS 2: Edge View (zoomed per measurement)")
                    self._log("=" * 50)
                    
                    for tp in edge_tests:
                        if self.should_stop:
                            break
                        
                        tp.status = TestStatus.RUNNING
                        if self.on_test_start:
                            self.on_test_start(tp)
                        
                        meas_type = tp.extra_data.get('meas_type', 'RISETIME')
                        source_ch = tp.extra_data.get('source_ch', self.channel_from)
                        
                        # Reconfigure scope for this edge measurement
                        self._configure_edge_view(tp)
                        
                        # Set up edge measurement
                        self.inst.scope_write("MEASUrement:DELETEALL")
                        meas_name = f"MEAS{tp.test_id}"
                        src = f"CH{source_ch}"
                        
                        self.inst.scope_write(f'MEASUrement:ADDNew "{meas_name}"')
                        self.inst.scope_write(f"MEASUrement:{meas_name}:TYPe {meas_type}")
                        self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce {src}")
                        self.inst.scope_write(f"MEASUrement:{meas_name}:STATE ON")
                        self._log(f"  {meas_name}: {meas_type} on {src}")
                        
                        if self.on_progress:
                            self.on_progress(15 + done / total * 70, f"Acquiring {tp.name}...")
                        
                        self._acquire(timeout=10)
                        
                        if self.should_stop:
                            break
                        
                        # Capture edge view screenshot
                        if output_dir:
                            edge_name = tp.name.replace(" ", "_").lower()
                            screenshot_path = self.capture_screenshot(f"edge_{edge_name}", output_dir)
                            if screenshot_path:
                                tp.screenshot_path = screenshot_path
                                if self.on_screenshot:
                                    self.on_screenshot(screenshot_path)
                        
                        # Read and evaluate
                        measured = self._read_measurement(meas_name)
                        self._evaluate_test_point(tp, measured)
                        
                        if tp.status == TestStatus.PASS:
                            passed += 1
                        elif tp.status in (TestStatus.FAIL, TestStatus.ERROR):
                            failed += 1
                        
                        if self.on_test_complete:
                            self.on_test_complete(tp)
                        
                        done += 1
                        if self.on_progress:
                            self.on_progress(15 + done / total * 70, f"Test {done}/{total}")
            
        except Exception as e:
            self._log(f"Sequence error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            if self.on_complete:
                self.on_complete(passed, failed)
    
    def _run_reference_mode_tests(self, output_dir: Path, src1: str, src2: str, 
                                   passed: int, failed: int):
        """Run all tests in reference mode - no acquisitions, just measurements on static data."""
        
        # Set up ALL measurements at once on REF channels
        self.inst.scope_write("MEASUrement:DELETEALL")
        
        for tp in self.test_points:
            if not tp.enabled:
                tp.status = TestStatus.SKIPPED
                continue
                
            meas_name = f"MEAS{tp.test_id}"
            meas_type = tp.extra_data.get('meas_type', 'DELAY')
            source_ch = tp.extra_data.get('source_ch', self.channel_from)
            source = self._get_source(source_ch, tp.test_id)
            
            self.inst.scope_write(f'MEASUrement:ADDNew "{meas_name}"')
            
            if meas_type == 'DELAY':
                # Delay measurement uses two sources
                self.inst.scope_write(f"MEASUrement:{meas_name}:TYPe DELAY")
                self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce1 {src1}")
                self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce2 {src2}")
                self.inst.scope_write(f"MEASUrement:{meas_name}:DELay:EDGE1 FALL")
                self.inst.scope_write(f"MEASUrement:{meas_name}:DELay:EDGE2 RISE")
                self._log(f"  {meas_name}: DELAY {src1} FALL → {src2} RISE")
            else:
                # Rise/fall time - single source
                self.inst.scope_write(f"MEASUrement:{meas_name}:TYPe {meas_type}")
                self.inst.scope_write(f"MEASUrement:{meas_name}:SOUrce {source}")
                self._log(f"  {meas_name}: {meas_type} on {source}")
            
            self.inst.scope_write(f"MEASUrement:{meas_name}:STATE ON")
        
        # No acquisition needed - reference waveform is static
        # Just wait briefly for measurements to process
        self._log("Processing reference waveforms (no acquisition)...")
        time.sleep(0.5)
        
        # Capture single screenshot
        if output_dir:
            screenshot_path = self.capture_screenshot("ref_mode", output_dir)
            if screenshot_path and self.on_screenshot:
                self.on_screenshot(screenshot_path)
        
        # Read and evaluate all measurements
        total = len([tp for tp in self.test_points if tp.enabled])
        done = 0
        
        for tp in self.test_points:
            if not tp.enabled:
                continue
            if self.should_stop:
                break
            
            tp.status = TestStatus.RUNNING
            if self.on_test_start:
                self.on_test_start(tp)
            
            tp.extra_data['reference_mode'] = True
            
            measured = self._read_measurement(f"MEAS{tp.test_id}")
            self._evaluate_test_point(tp, measured)
            
            if tp.status == TestStatus.PASS:
                passed += 1
            elif tp.status in (TestStatus.FAIL, TestStatus.ERROR):
                failed += 1
            
            if output_dir and not tp.screenshot_path:
                tp.screenshot_path = str(output_dir / "agc_ref_mode.png")
            
            if self.on_test_complete:
                self.on_test_complete(tp)
            
            done += 1
            if self.on_progress:
                self.on_progress(done / total * 100, f"Test {done}/{total}")


# =============================================================================
# WIDGETS
# =============================================================================

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, style="primary",
                 width=120, height=36, radius=8, **kwargs):
        super().__init__(parent, width=width, height=height,
                        highlightthickness=0, bg=parent.cget('bg'), **kwargs)
        self.command = command
        self.text = text
        self.width = width
        self.height = height
        self.radius = radius
        styles = {
            "primary": (TekColors.TEK_BLUE, TekColors.BUTTON_HOVER, TekColors.TEXT_PRIMARY),
            "success": (TekColors.STATUS_PASS, "#58D68D", TekColors.TEXT_PRIMARY),
            "danger": (TekColors.STATUS_FAIL, "#EC7063", TekColors.TEXT_PRIMARY),
            "secondary": (TekColors.BG_LIGHT, TekColors.BG_MEDIUM, TekColors.TEXT_PRIMARY),
        }
        self.bg_color, self.hover_color, self.fg_color = styles.get(style, styles["primary"])
        self.current_bg = self.bg_color
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self):
        self.delete("all")
        x0, y0 = 2, 2
        x1, y1 = self.width - 2, self.height - 2
        r = self.radius
        self.create_arc(x0, y0, x0+2*r, y0+2*r, start=90, extent=90,
                       fill=self.current_bg, outline=self.current_bg)
        self.create_arc(x1-2*r, y0, x1, y0+2*r, start=0, extent=90,
                       fill=self.current_bg, outline=self.current_bg)
        self.create_arc(x0, y1-2*r, x0+2*r, y1, start=180, extent=90,
                       fill=self.current_bg, outline=self.current_bg)
        self.create_arc(x1-2*r, y1-2*r, x1, y1, start=270, extent=90,
                       fill=self.current_bg, outline=self.current_bg)
        self.create_rectangle(x0+r, y0, x1-r, y1, fill=self.current_bg, outline=self.current_bg)
        self.create_rectangle(x0, y0+r, x1, y1-r, fill=self.current_bg, outline=self.current_bg)
        self.create_text(self.width/2, self.height/2, text=self.text,
                        fill=self.fg_color, font=TekFonts.BUTTON)

    def _on_enter(self, e):
        self.current_bg = self.hover_color
        self._draw()
        self.config(cursor="hand2")

    def _on_leave(self, e):
        self.current_bg = self.bg_color
        self._draw()

    def _on_click(self, e):
        if self.command:
            self.command()

    def configure(self, **kwargs):
        if 'state' in kwargs:
            if kwargs['state'] == tk.DISABLED:
                self.current_bg = TekColors.BG_MEDIUM
                self.unbind("<Button-1>")
            else:
                self.current_bg = self.bg_color
                self.bind("<Button-1>", self._on_click)
            self._draw()
        if 'text' in kwargs:
            self.text = kwargs['text']
            self._draw()


# =============================================================================
# STYLED DIALOG CLASSES
# =============================================================================

class TekStyledDialog(tk.Toplevel):
    """
    A styled modal dialog that matches the Tek PTA UI theme.
    
    Replaces default Windows messageboxes with consistent dark theme dialogs.
    Supports OK/Cancel, Yes/No, and custom button configurations.
    """
    
    def __init__(self, parent, title: str, message: str, 
                 dialog_type: str = "okcancel",  # okcancel, yesno, ok, info, warning, error
                 width: int = 550, height: int = None,  # Increased default width by 10%
                 icon: str = None):  # info, warning, error, question
        super().__init__(parent)
        self.result = None
        
        self.title(title)
        self.configure(bg=TekColors.BG_DARK)
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)
        
        # Determine icon and header color
        icon_map = {
            'info': ('ℹ️', TekColors.TEK_CYAN),
            'warning': ('⚠️', TekColors.STATUS_RUNNING),
            'error': ('❌', TekColors.STATUS_FAIL),
            'question': ('❓', TekColors.TEK_CYAN),
            'success': ('✅', TekColors.STATUS_PASS),
        }
        
        # Auto-detect icon from dialog type if not specified
        if icon is None:
            if dialog_type in ('warning',):
                icon = 'warning'
            elif dialog_type in ('error',):
                icon = 'error'
            else:
                icon = 'info'
        
        icon_char, header_color = icon_map.get(icon, ('ℹ️', TekColors.TEK_CYAN))
        
        # Calculate height based on message length if not specified (increased by ~10%)
        if height is None:
            lines = message.count('\n') + 1
            char_per_line = max(1, width // 8)
            wrapped_lines = sum(1 + len(line) // char_per_line for line in message.split('\n'))
            height = min(660, max(220, 135 + wrapped_lines * 22))  # Increased minimums by 10%
        
        self.geometry(f"{width}x{height}")
        
        # Header bar with icon
        header = tk.Frame(self, bg=header_color, height=45)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        header_text = f"{icon_char}  {title}"
        tk.Label(header, text=header_text, font=TekFonts.HEADER,
                bg=header_color, fg="white").pack(pady=10, padx=15, anchor='w')
        
        # Content frame
        content = tk.Frame(self, bg=TekColors.BG_DARK, padx=25, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Message with word wrap - use Message widget for auto-wrap
        msg_widget = tk.Message(content, text=message, font=TekFonts.NORMAL,
                               bg=TekColors.BG_DARK, fg=TekColors.TEXT_PRIMARY,
                               width=width - 60, justify='left')
        msg_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Button frame
        btn_frame = tk.Frame(content, bg=TekColors.BG_DARK)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Create buttons based on dialog type
        if dialog_type == "okcancel":
            RoundedButton(btn_frame, "OK", command=lambda: self._respond(True),
                         style="success", width=100, height=34).pack(side=tk.RIGHT, padx=(10, 0))
            RoundedButton(btn_frame, "Cancel", command=lambda: self._respond(False),
                         style="secondary", width=100, height=34).pack(side=tk.RIGHT)
        elif dialog_type == "yesno":
            RoundedButton(btn_frame, "Yes", command=lambda: self._respond(True),
                         style="success", width=100, height=34).pack(side=tk.RIGHT, padx=(10, 0))
            RoundedButton(btn_frame, "No", command=lambda: self._respond(False),
                         style="secondary", width=100, height=34).pack(side=tk.RIGHT)
        elif dialog_type in ("ok", "info", "warning", "error"):
            RoundedButton(btn_frame, "OK", command=lambda: self._respond(True),
                         style="primary", width=100, height=34).pack(side=tk.RIGHT)
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", lambda: self._respond(False))
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        
        # Focus on dialog
        self.focus_set()
        
        # Bind Enter and Escape keys
        self.bind('<Return>', lambda e: self._respond(True))
        self.bind('<Escape>', lambda e: self._respond(False))
    
    def _respond(self, value: bool):
        self.result = value
        self.destroy()
    
    @staticmethod
    def askokcancel(parent, title: str, message: str, icon: str = 'info') -> bool:
        """Show OK/Cancel dialog, returns True if OK clicked."""
        dialog = TekStyledDialog(parent, title, message, "okcancel", icon=icon)
        parent.wait_window(dialog)
        return dialog.result is True
    
    @staticmethod
    def askyesno(parent, title: str, message: str, icon: str = 'question') -> bool:
        """Show Yes/No dialog, returns True if Yes clicked."""
        dialog = TekStyledDialog(parent, title, message, "yesno", icon=icon)
        parent.wait_window(dialog)
        return dialog.result is True
    
    @staticmethod
    def showinfo(parent, title: str, message: str):
        """Show info dialog."""
        dialog = TekStyledDialog(parent, title, message, "info", icon='info')
        parent.wait_window(dialog)
    
    @staticmethod
    def showwarning(parent, title: str, message: str):
        """Show warning dialog."""
        dialog = TekStyledDialog(parent, title, message, "warning", icon='warning')
        parent.wait_window(dialog)
    
    @staticmethod
    def showerror(parent, title: str, message: str):
        """Show error dialog."""
        dialog = TekStyledDialog(parent, title, message, "error", icon='error')
        parent.wait_window(dialog)


# =============================================================================
# TEST FAILURE DIALOG
# =============================================================================

class TestFailureDialog(tk.Toplevel):
    """Non-modal dialog shown when a test fails.
    
    Allows user to continue or abort while still being able to browse
    the main application (SCPI log, results, etc.).
    """
    
    # Class variable to track "continue all" state across instances
    continue_all_failures = False
    
    def __init__(self, parent, test_point: TestPoint, on_response: Callable[[str, bool], None]):
        """
        Args:
            parent: Parent window
            test_point: The failed test point
            on_response: Callback with (action, save_waveforms) where action is 'continue' or 'abort'
        """
        super().__init__(parent)
        self.on_response = on_response
        self.result = None
        self.save_waveforms = tk.BooleanVar(value=False)
        self.continue_all = tk.BooleanVar(value=False)
        
        self.title("⚠️ Test Failed")
        self.configure(bg=TekColors.BG_DARK)
        self.geometry("500x400")
        self.resizable(True, True)
        
        # Stay on top but NOT modal (grab_set causes crashes when test thread is running)
        self.transient(parent)
        self.attributes('-topmost', True)
        
        # Prevent closing without response
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._create_ui(test_point)
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self, tp: TestPoint):
        # Header with warning icon
        header = tk.Frame(self, bg=TekColors.STATUS_FAIL, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="⚠️  TEST FAILED", font=TekFonts.HEADER,
                bg=TekColors.STATUS_FAIL, fg="white").pack(pady=10)
        
        # Content frame
        content = tk.Frame(self, bg=TekColors.BG_DARK, padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Test info
        info_frame = tk.Frame(content, bg=TekColors.BG_CARD, padx=15, pady=10)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(info_frame, text=f"Test #{tp.test_id}: {tp.name}",
                font=TekFonts.SUBHEADER, bg=TekColors.BG_CARD, 
                fg=TekColors.TEXT_PRIMARY).pack(anchor='w')
        
        # Show measured vs expected
        if tp.has_limits:
            measured_str = f"{tp.measured_value:.6g} {tp.unit}"
            expected_str = f"{tp.nominal_value:.6g} {tp.unit}"
            limits_str = f"Limits: {tp.lower_limit:.6g} to {tp.upper_limit:.6g} {tp.unit}"
            
            tk.Label(info_frame, text=f"Measured: {measured_str}",
                    font=TekFonts.NORMAL, bg=TekColors.BG_CARD,
                    fg=TekColors.STATUS_FAIL).pack(anchor='w', pady=(5, 0))
            tk.Label(info_frame, text=f"Expected: {expected_str}",
                    font=TekFonts.NORMAL, bg=TekColors.BG_CARD,
                    fg=TekColors.TEXT_SECONDARY).pack(anchor='w')
            tk.Label(info_frame, text=limits_str,
                    font=TekFonts.SMALL, bg=TekColors.BG_CARD,
                    fg=TekColors.TEXT_SECONDARY).pack(anchor='w')
        
        # Checkboxes frame
        check_frame = tk.Frame(content, bg=TekColors.BG_DARK)
        check_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(check_frame, text="Save waveforms before continuing/aborting",
                       variable=self.save_waveforms).pack(anchor='w')
        
        ttk.Checkbutton(check_frame, text="Continue through all remaining failures (don't ask again)",
                       variable=self.continue_all).pack(anchor='w', pady=(5, 0))
        
        # Info text
        tk.Label(content, text="You can browse the SCPI log and results\nwhile this dialog is open.",
                font=TekFonts.SMALL, bg=TekColors.BG_DARK,
                fg=TekColors.TEXT_SECONDARY, justify='center').pack(pady=(0, 10))
        
        # Buttons
        btn_frame = tk.Frame(content, bg=TekColors.BG_DARK)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        RoundedButton(btn_frame, "Continue Testing", 
                     command=self._on_continue,
                     style="success", width=140, height=36).pack(side=tk.LEFT, padx=(0, 10))
        
        RoundedButton(btn_frame, "Abort Test Sequence",
                     command=self._on_abort,
                     style="danger", width=160, height=36).pack(side=tk.LEFT)
    
    def _on_continue(self):
        self.result = 'continue'
        # Store "continue all" preference as class variable
        if self.continue_all.get():
            TestFailureDialog.continue_all_failures = True
        self.on_response('continue', self.save_waveforms.get())
        self.destroy()
    
    def _on_abort(self):
        self.result = 'abort'
        # Reset "continue all" on abort
        TestFailureDialog.continue_all_failures = False
        self.on_response('abort', self.save_waveforms.get())
        self.destroy()
    
    def _on_close(self):
        # Prevent closing without making a choice - treat as abort
        self._on_abort()
    
    @classmethod
    def reset_continue_all(cls):
        """Reset the continue-all flag. Call at start of new test run."""
        cls.continue_all_failures = False


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class TektronixProductionTestApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Tek PTA - Production Test Assistant v{__version__}")
        self.root.geometry("1600x1000")
        self.root.configure(bg=TekColors.BG_DARK)
        self.inst = InstrumentManager()
        self.inst.on_scpi_log = self._log_scpi  # Connect SCPI logging
        self.afg_engine = AFGFrequencyTestEngine(self.inst)
        self.led_engine = LEDCurrentTestEngine(self.inst)
        self.spectrum_engine = SpectrumScannerEngine(self.inst)
        self.eye_engine = EyeDiagramTestEngine(self.inst)
        self.agc_engine = AGCSampleTestEngine(self.inst)
        self.current_engine = None
        self.current_suite = None
        self.output_dir = None
        self.msg_queue = queue.Queue()
        self.screenshot_cache = {}
        self.screenshot_paths = []
        self.screenshot_idx = 0
        # Persistent SCPI log - not cleared when user presses Clear button
        self.persistent_scpi_log: List[str] = []
        # Plugin engines storage (populated by _create_suites)
        self.plugin_engines: Dict[str, Any] = {}
        # Test failure dialog state
        self.failure_dialog: Optional[TestFailureDialog] = None
        self.failure_response: Optional[str] = None  # 'continue' or 'abort'
        self.failure_save_waveforms: bool = False
        self.test_paused_for_failure: bool = False
        # Threading event to pause engine on failure - cleared = paused, set = running
        self.failure_pause_event = threading.Event()
        self.failure_pause_event.set()  # Start in "running" state
        self._load_logos()
        self._configure_styles()
        self._create_ui()
        self._setup_callbacks()
        self._process_messages()
        self.test_suites = self._create_suites()

    def _load_logos(self):
        self.logo_modern = None
        self.logo_classic = None
        if not PIL_AVAILABLE:
            return
        script_dir = Path(__file__).parent
        modern_paths = [Path("Tek_Logo_2016.png"), script_dir / "Tek_Logo_2016.png"]
        classic_paths = [Path("Tek_Logo_1947.png"), script_dir / "Tek_Logo_1947.png"]
        for path in modern_paths:
            if path.exists():
                try:
                    img = Image.open(path)
                    img = img.resize((140, 35), Image.Resampling.LANCZOS)
                    self.logo_modern = ImageTk.PhotoImage(img)
                    break
                except Exception:
                    pass
        for path in classic_paths:
            if path.exists():
                try:
                    img = Image.open(path)
                    img = img.resize((55, 55), Image.Resampling.LANCZOS)
                    self.logo_classic = ImageTk.PhotoImage(img)
                    break
                except Exception:
                    pass

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=TekColors.BG_DARK, foreground=TekColors.TEXT_PRIMARY)
        style.configure('TFrame', background=TekColors.BG_DARK)
        style.configure('TLabel', background=TekColors.BG_DARK, foreground=TekColors.TEXT_PRIMARY)
        style.configure('TLabelframe', background=TekColors.BG_DARK)
        style.configure('TLabelframe.Label', background=TekColors.BG_DARK,
                       foreground=TekColors.TEXT_ACCENT, font=TekFonts.SUBHEADER)
        style.configure('TNotebook', background=TekColors.BG_DARK)
        style.configure('TNotebook.Tab', background=TekColors.BG_MEDIUM,
                       foreground=TekColors.TEXT_PRIMARY, padding=[15, 8])
        style.map('TNotebook.Tab', background=[('selected', TekColors.TEK_BLUE)])
        style.configure('TEntry', fieldbackground=TekColors.BG_LIGHT, foreground=TekColors.TEXT_PRIMARY)
        style.configure('TCombobox', fieldbackground=TekColors.BG_LIGHT, foreground=TekColors.TEXT_PRIMARY)
        style.configure('TCheckbutton', background=TekColors.BG_DARK, foreground=TekColors.TEXT_PRIMARY)
        style.configure('Treeview', background=TekColors.BG_MEDIUM, foreground=TekColors.TEXT_PRIMARY,
                       fieldbackground=TekColors.BG_MEDIUM, rowheight=25)
        style.configure('Treeview.Heading', background=TekColors.BG_LIGHT, foreground=TekColors.TEXT_PRIMARY)

    def _create_ui(self):
        self._create_header()
        
        # Main horizontal paned window: content | log
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side: content (lab bench, test list, notebook)
        content_frame = tk.Frame(self.main_paned, bg=TekColors.BG_DARK)
        self.main_paned.add(content_frame, weight=3)
        
        content_paned = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left-left: lab bench + test list
        left_frame = tk.Frame(content_paned, bg=TekColors.BG_DARK)
        content_paned.add(left_frame, weight=1)
        
        left_paned = ttk.PanedWindow(left_frame, orient=tk.VERTICAL)
        left_paned.pack(fill=tk.BOTH, expand=True)
        bench_frame = tk.Frame(left_paned, bg=TekColors.BG_CARD)
        left_paned.add(bench_frame, weight=1)
        self._create_lab_bench(bench_frame)
        list_frame = tk.Frame(left_paned, bg=TekColors.BG_CARD)
        left_paned.add(list_frame, weight=2)
        self._create_test_list(list_frame)
        
        # Left-right: notebook (wider default for better text display)
        notebook_frame = tk.Frame(content_paned, bg=TekColors.BG_DARK)
        content_paned.add(notebook_frame, weight=3)  # Increased from 2 to 3
        self._create_notebook(notebook_frame)
        
        # Right side: log panel (adjustable width)
        log_frame = tk.Frame(self.main_paned, bg=TekColors.BG_PANEL)
        self.main_paned.add(log_frame, weight=1)
        self._create_log_panel(log_frame)

    def _create_header(self):
        header = tk.Frame(self.root, bg=TekColors.BG_PANEL, height=75)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        logo_frame = tk.Frame(header, bg=TekColors.BG_PANEL)
        logo_frame.pack(side=tk.LEFT, padx=15, pady=10)
        if self.logo_modern:
            tk.Label(logo_frame, image=self.logo_modern, bg=TekColors.BG_PANEL).pack(side=tk.LEFT)
        else:
            tk.Label(logo_frame, text="Tektronix", font=TekFonts.TITLE,
                    bg=TekColors.BG_PANEL, fg=TekColors.TEK_CYAN).pack(side=tk.LEFT)
        if self.logo_classic:
            tk.Label(logo_frame, image=self.logo_classic, bg=TekColors.BG_PANEL).pack(side=tk.LEFT, padx=15)
        center = tk.Frame(header, bg=TekColors.BG_PANEL)
        center.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)
        tk.Label(center, text="Tek PTA - Production Test Assistant", font=TekFonts.TITLE,
                bg=TekColors.BG_PANEL, fg=TekColors.TEXT_PRIMARY).pack(anchor=tk.W)
        self.suite_label = tk.Label(center, text="No test suite selected", font=TekFonts.NORMAL,
                                   bg=TekColors.BG_PANEL, fg=TekColors.TEXT_SECONDARY,
                                   wraplength=500, justify=tk.LEFT)
        self.suite_label.pack(anchor=tk.W)
        btn_frame = tk.Frame(header, bg=TekColors.BG_PANEL)
        btn_frame.pack(side=tk.RIGHT, padx=15, pady=15)
        # About button - centered, easy to find
        self.about_btn = RoundedButton(btn_frame, "ℹ️ About",
                                       command=self._show_about_dialog, style="secondary")
        self.about_btn.pack(side=tk.LEFT, padx=5)
        self.suite_btn = RoundedButton(btn_frame, "📋 Select Suite",
                                       command=self._show_suite_selector, style="secondary")
        self.suite_btn.pack(side=tk.LEFT, padx=5)
        self.browse_btn = RoundedButton(btn_frame, "📁 Import...",
                                        command=self._browse_plugin_file, style="secondary")
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        self.run_btn = RoundedButton(btn_frame, "▶ Run Tests",
                                    command=self._run_tests, style="success")
        self.run_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = RoundedButton(btn_frame, "⬛ Stop",
                                     command=self._stop_tests, style="danger")
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn.configure(state=tk.DISABLED)

    def _create_lab_bench(self, parent):
        title_frame = tk.Frame(parent, bg=TekColors.BG_CARD)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(title_frame, text="🔬 Virtual Lab Bench", font=TekFonts.SUBHEADER,
                bg=TekColors.BG_CARD, fg=TekColors.TEXT_ACCENT).pack(side=tk.LEFT)
        btn_frame = tk.Frame(parent, bg=TekColors.BG_CARD)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        RoundedButton(btn_frame, "🔄 Refresh", command=self._refresh_instruments,
                     style="secondary", width=90, height=30).pack(side=tk.LEFT, padx=2)
        RoundedButton(btn_frame, "➕ Add", command=self._add_instrument,
                     style="secondary", width=70, height=30).pack(side=tk.LEFT, padx=2)
        self.instruments_frame = tk.Frame(parent, bg=TekColors.BG_CARD)
        self.instruments_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(self.instruments_frame, text="Click Refresh to discover instruments",
                font=TekFonts.SMALL, bg=TekColors.BG_CARD,
                fg=TekColors.TEXT_SECONDARY).pack(pady=20)

    def _create_instrument_card(self, parent, inst: InstrumentInfo):
        # Highlight card background if connected
        bg_color = TekColors.BG_LIGHT if not inst.is_connected else "#1a3d1a"  # Dark green tint
        card = tk.Frame(parent, bg=bg_color)
        card.pack(fill=tk.X, pady=3)
        inner = tk.Frame(card, bg=bg_color)
        inner.pack(fill=tk.X, padx=8, pady=6)
        icons = {"Oscilloscope": "📊", "SMU": "⚡", "Function Generator": "〰️"}
        icon = icons.get(inst.instrument_type, "📟")
        tk.Label(inner, text=icon, font=("Segoe UI", 16),
                bg=bg_color, fg=TekColors.TEXT_PRIMARY).pack(side=tk.LEFT, padx=(0, 8))
        info = tk.Frame(inner, bg=bg_color)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(info, text=f"{inst.manufacturer} {inst.model}", font=TekFonts.SMALL,
                bg=bg_color, fg=TekColors.TEXT_PRIMARY).pack(anchor=tk.W)
        
        # Show CONNECTED status or serial number
        if inst.is_connected:
            status_frame = tk.Frame(info, bg=bg_color)
            status_frame.pack(anchor=tk.W)
            tk.Label(status_frame, text="✓ CONNECTED", font=("Segoe UI", 8, "bold"),
                    bg=bg_color, fg=TekColors.STATUS_PASS).pack(side=tk.LEFT)
            tk.Label(status_frame, text=f" • S/N: {inst.serial_number}", font=("Segoe UI", 8),
                    bg=bg_color, fg=TekColors.TEXT_SECONDARY).pack(side=tk.LEFT)
        else:
            tk.Label(info, text=f"S/N: {inst.serial_number}", font=("Segoe UI", 8),
                    bg=bg_color, fg=TekColors.TEXT_SECONDARY).pack(anchor=tk.W)
        
        if inst.instrument_type == "Oscilloscope":
            if inst.is_connected:
                btn = RoundedButton(inner, "✓ Active", style="success", width=70, height=26)
                btn.configure(state=tk.DISABLED)
            else:
                btn = RoundedButton(inner, "Connect",
                                   command=lambda i=inst: self._connect_scope(i), width=70, height=26)
            btn.pack(side=tk.RIGHT)
        elif inst.instrument_type == "SMU":
            if inst.is_connected:
                btn = RoundedButton(inner, "✓ Active", style="success", width=70, height=26)
                btn.configure(state=tk.DISABLED)
            else:
                btn = RoundedButton(inner, "Connect",
                                   command=lambda i=inst: self._connect_smu(i), width=70, height=26)
            btn.pack(side=tk.RIGHT)
        elif inst.instrument_type == "Function Generator":
            if inst.is_connected:
                btn = RoundedButton(inner, "✓ Active", style="success", width=70, height=26)
                btn.configure(state=tk.DISABLED)
            else:
                btn = RoundedButton(inner, "Connect",
                                   command=lambda i=inst: self._connect_awg(i), width=70, height=26)
            btn.pack(side=tk.RIGHT)

    def _create_test_list(self, parent):
        title = tk.Frame(parent, bg=TekColors.BG_CARD)
        title.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(title, text="📋 Test Sequence", font=TekFonts.SUBHEADER,
                bg=TekColors.BG_CARD, fg=TekColors.TEXT_ACCENT).pack(side=tk.LEFT)
        btn_frame = tk.Frame(parent, bg=TekColors.BG_CARD)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        RoundedButton(btn_frame, "All", command=self._select_all,
                     style="secondary", width=50, height=26).pack(side=tk.LEFT, padx=2)
        RoundedButton(btn_frame, "None", command=self._select_none,
                     style="secondary", width=55, height=26).pack(side=tk.LEFT, padx=2)
        container = tk.Frame(parent, bg=TekColors.BG_CARD)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        canvas = tk.Canvas(container, bg=TekColors.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.test_list_frame = tk.Frame(canvas, bg=TekColors.BG_CARD)
        self.test_list_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.test_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.test_checkboxes = {}
        self.test_status_labels = {}

    def _create_notebook(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="⚙️ Configure")
        self._create_config_panel(config_frame)
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="📊 Results")
        self._create_results_panel(results_frame)
        screenshot_frame = ttk.Frame(notebook)
        notebook.add(screenshot_frame, text="📷 Screenshots")
        self._create_screenshot_panel(screenshot_frame)
        self.notebook = notebook

    def _show_about_dialog(self):
        """Show About dialog window - compact, no scrolling needed"""
        about = tk.Toplevel(self.root)
        about.title("About Tek PTA")
        about.geometry("480x520")
        about.configure(bg=TekColors.BG_DARK)
        about.transient(self.root)
        about.grab_set()
        about.resizable(False, False)
        
        # Center on parent
        about.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 480) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 520) // 2
        about.geometry(f"+{x}+{y}")
        
        frame = tk.Frame(about, bg=TekColors.BG_DARK)
        frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=15)
        
        # Title
        tk.Label(frame, text="Tek PTA", font=("Segoe UI", 24, "bold"),
                bg=TekColors.BG_DARK, fg=TekColors.TEK_CYAN).pack(pady=(0, 2))
        tk.Label(frame, text="Production Test Assistant", font=("Segoe UI", 12),
                bg=TekColors.BG_DARK, fg=TekColors.TEXT_PRIMARY).pack(pady=(0, 10))
        
        # Version info - single line
        tk.Label(frame, text=f"v{__version__} • {__last_modified__}", font=TekFonts.SMALL,
                bg=TekColors.BG_DARK, fg=TekColors.TEXT_SECONDARY).pack()
        
        # AE-ware notice
        tk.Label(frame, text="FREE AE-WARE FROM TEKTRONIX", font=("Segoe UI", 10, "bold"),
                bg=TekColors.BG_DARK, fg=TekColors.TEK_CYAN).pack(pady=(12, 5))
        
        about_text = """Developed by Tektronix Application Engineers with decades
of instrument programming expertise.

PURPOSE: Rapid development of automated test programs
with proper SCPI usage and measurement techniques.

CUSTOMIZATION: Customizable via Claude AI. Not fully
vetted through software deployment approval chains.

DISCLAIMER: Provided "as-is" without warranty.
For educational and demonstration purposes."""
        
        tk.Label(frame, text=about_text, font=TekFonts.SMALL,
                bg=TekColors.BG_DARK, fg=TekColors.TEXT_SECONDARY,
                justify=tk.CENTER).pack(pady=8)
        
        # Contact info
        contact_frame = tk.Frame(frame, bg=TekColors.BG_PANEL)
        contact_frame.pack(fill=tk.X, pady=10)
        tk.Label(contact_frame, text="Questions or Bug Reports?", 
                font=TekFonts.SMALL, bg=TekColors.BG_PANEL, 
                fg=TekColors.TEXT_PRIMARY).pack(pady=(8, 2))
        tk.Label(contact_frame, text="Andre Asbury - andre.asbury@tektronix.com", 
                font=TekFonts.SMALL, bg=TekColors.BG_PANEL, 
                fg=TekColors.TEXT_ACCENT).pack(pady=(0, 8))
        
        # Close button
        RoundedButton(frame, "Close", command=about.destroy, 
                     style="primary", width=100, height=32).pack(pady=10)

    def _create_config_panel(self, parent):
        config_nb = ttk.Notebook(parent)
        config_nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sequence tab
        seq = ttk.Frame(config_nb)
        config_nb.add(seq, text="Sequence")
        
        # Description (always visible) - use Message widget for proper word wrap
        desc_frame = ttk.LabelFrame(seq, text="Test Suite Description")
        desc_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # Use Message widget which automatically wraps text
        self.suite_desc_label = tk.Message(desc_frame, text="Select a test suite to see its description.",
                                          font=TekFonts.NORMAL, bg=TekColors.BG_DARK,
                                          fg=TekColors.TEXT_SECONDARY, justify=tk.LEFT,
                                          anchor=tk.W, aspect=500)  # aspect controls width/height ratio
        self.suite_desc_label.pack(padx=10, pady=10, fill=tk.X, expand=True)
        
        # Container for dynamic config frames
        self.config_container = tk.Frame(seq, bg=TekColors.BG_DARK)
        self.config_container.pack(fill=tk.BOTH, expand=True)
        
        # Create frequency sweep config frame (for AFG tests)
        self.freq_config_frame = ttk.LabelFrame(self.config_container, text="Frequency Sweep Configuration")
        self._create_freq_config(self.freq_config_frame)
        
        # Create voltage sweep config frame (for LED current tests)
        self.voltage_config_frame = ttk.LabelFrame(self.config_container, text="Voltage Sweep Configuration")
        self._create_voltage_config(self.voltage_config_frame)
        
        # Create spectrum scan config frame
        self.spectrum_config_frame = ttk.LabelFrame(self.config_container, text="Spectrum Scan Configuration")
        self._create_spectrum_config(self.spectrum_config_frame)
        
        # Create eye diagram config frame
        self.eye_diagram_config_frame = ttk.LabelFrame(self.config_container, text="Eye Diagram Configuration")
        self._create_eye_diagram_config(self.eye_diagram_config_frame)
        
        # Channels tab
        ch_tab = ttk.Frame(config_nb)
        config_nb.add(ch_tab, text="Channels")
        self._create_channel_config(ch_tab)
        
        # Info tab (renamed from Session)
        info_tab = ttk.Frame(config_nb)
        config_nb.add(info_tab, text="Info")
        info_frame = ttk.LabelFrame(info_tab, text="Test Information")
        info_frame.pack(fill=tk.X, padx=15, pady=10)
        self.operator = tk.StringVar()
        self.dut_serial = tk.StringVar()
        self.description = tk.StringVar()
        for lbl, var in [("Operator:", self.operator), ("DUT Serial:", self.dut_serial), ("Description:", self.description)]:
            row = ttk.Frame(info_frame)
            row.pack(fill=tk.X, padx=10, pady=5)
            ttk.Label(row, text=lbl, width=12).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, width=40).pack(side=tk.LEFT, padx=10)
        
        # References tab - for loading reference waveforms
        ref_tab = ttk.Frame(config_nb)
        config_nb.add(ref_tab, text="References")
        self._create_reference_config(ref_tab)

    def _create_freq_config(self, parent):
        """Create frequency sweep configuration widgets"""
        row1 = ttk.Frame(parent)
        row1.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row1, text="Start (Hz):").pack(side=tk.LEFT)
        self.freq_start = tk.StringVar(value="1000")
        ttk.Entry(row1, textvariable=self.freq_start, width=12).pack(side=tk.LEFT, padx=10)
        ttk.Label(row1, text="Stop (Hz):").pack(side=tk.LEFT, padx=(15, 0))
        self.freq_stop = tk.StringVar(value="25000000")
        ttk.Entry(row1, textvariable=self.freq_stop, width=12).pack(side=tk.LEFT, padx=10)
        
        row2 = ttk.Frame(parent)
        row2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row2, text="Points:").pack(side=tk.LEFT)
        self.num_points = tk.StringVar(value="20")
        ttk.Spinbox(row2, textvariable=self.num_points, from_=5, to=50, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row2, text="Tolerance (%):").pack(side=tk.LEFT, padx=(15, 0))
        self.tolerance = tk.StringVar(value="0.2")
        ttk.Entry(row2, textvariable=self.tolerance, width=8).pack(side=tk.LEFT, padx=10)
        
        row3 = ttk.Frame(parent)
        row3.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row3, text="Spacing:").pack(side=tk.LEFT)
        self.spacing = tk.StringVar(value="logarithmic")
        ttk.Radiobutton(row3, text="Logarithmic", variable=self.spacing, value="logarithmic").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(row3, text="Linear", variable=self.spacing, value="linear").pack(side=tk.LEFT, padx=10)
        
        afg_frame = ttk.LabelFrame(parent, text="AFG Settings")
        afg_frame.pack(fill=tk.X, padx=5, pady=10)
        row4 = ttk.Frame(afg_frame)
        row4.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row4, text="Amplitude (Vpp):").pack(side=tk.LEFT)
        self.afg_amp = tk.StringVar(value="1.0")
        ttk.Entry(row4, textvariable=self.afg_amp, width=8).pack(side=tk.LEFT, padx=10)
        
        # Generate Tests button inside this config frame
        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_row, text="🔄 Generate Tests", command=self._generate_tests).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="↩ Restore Defaults", command=self._restore_defaults).pack(side=tk.LEFT, padx=5)

    def _create_voltage_config(self, parent):
        """Create voltage sweep configuration widgets for LED current test"""
        row1 = ttk.Frame(parent)
        row1.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row1, text="Start (V):").pack(side=tk.LEFT)
        self.volt_start = tk.StringVar(value="2.0")
        ttk.Entry(row1, textvariable=self.volt_start, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row1, text="Stop (V):").pack(side=tk.LEFT, padx=(15, 0))
        self.volt_stop = tk.StringVar(value="5.0")
        ttk.Entry(row1, textvariable=self.volt_stop, width=8).pack(side=tk.LEFT, padx=10)
        
        row2 = ttk.Frame(parent)
        row2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row2, text="Points:").pack(side=tk.LEFT)
        self.volt_points = tk.StringVar(value="7")
        ttk.Spinbox(row2, textvariable=self.volt_points, from_=3, to=20, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row2, text="Tolerance (µA):").pack(side=tk.LEFT, padx=(15, 0))
        self.led_tolerance = tk.StringVar(value="300")
        ttk.Entry(row2, textvariable=self.led_tolerance, width=8).pack(side=tk.LEFT, padx=10)
        
        row3 = ttk.Frame(parent)
        row3.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row3, text="Spacing:").pack(side=tk.LEFT)
        self.volt_spacing = tk.StringVar(value="linear")
        ttk.Radiobutton(row3, text="Linear", variable=self.volt_spacing, value="linear").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(row3, text="Logarithmic", variable=self.volt_spacing, value="logarithmic").pack(side=tk.LEFT, padx=10)
        
        # Specific values option
        row4 = ttk.Frame(parent)
        row4.pack(fill=tk.X, padx=10, pady=5)
        self.use_specific_values = tk.BooleanVar(value=False)
        ttk.Checkbutton(row4, text="Use specific values:", variable=self.use_specific_values,
                       command=self._toggle_specific_values).pack(side=tk.LEFT)
        self.specific_values = tk.StringVar(value="2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0")
        self.specific_entry = ttk.Entry(row4, textvariable=self.specific_values, width=35)
        self.specific_entry.pack(side=tk.LEFT, padx=10)
        
        # Shunt resistor setting
        shunt_frame = ttk.LabelFrame(parent, text="Shunt Resistor")
        shunt_frame.pack(fill=tk.X, padx=5, pady=10)
        row5 = ttk.Frame(shunt_frame)
        row5.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row5, text="Resistance (Ω):").pack(side=tk.LEFT)
        self.shunt_resistance = tk.StringVar(value="10")
        ttk.Entry(row5, textvariable=self.shunt_resistance, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row5, text="(For I = V/R conversion)").pack(side=tk.LEFT, padx=10)
        
        # Generate Tests button inside this config frame
        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_row, text="🔄 Generate Tests", command=self._generate_tests).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="↩ Restore Defaults", command=self._restore_defaults).pack(side=tk.LEFT, padx=5)

    def _create_spectrum_config(self, parent):
        """Create spectrum scan configuration widgets"""
        row1 = ttk.Frame(parent)
        row1.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row1, text="Start (MHz):").pack(side=tk.LEFT)
        self.spectrum_start_mhz = tk.StringVar(value="83")
        ttk.Entry(row1, textvariable=self.spectrum_start_mhz, width=10).pack(side=tk.LEFT, padx=10)
        ttk.Label(row1, text="Stop (MHz):").pack(side=tk.LEFT, padx=(15, 0))
        self.spectrum_stop_mhz = tk.StringVar(value="113")
        ttk.Entry(row1, textvariable=self.spectrum_stop_mhz, width=10).pack(side=tk.LEFT, padx=10)
        
        row2 = ttk.Frame(parent)
        row2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row2, text="Quick Presets:").pack(side=tk.LEFT)
        ttk.Button(row2, text="FM Radio", width=10, 
                  command=lambda: (self.spectrum_start_mhz.set("83"), self.spectrum_stop_mhz.set("113"))).pack(side=tk.LEFT, padx=3)
        ttk.Button(row2, text="Cellular", width=10, 
                  command=lambda: (self.spectrum_start_mhz.set("600"), self.spectrum_stop_mhz.set("1000"))).pack(side=tk.LEFT, padx=3)
        ttk.Button(row2, text="WiFi 2.4G", width=10, 
                  command=lambda: (self.spectrum_start_mhz.set("2300"), self.spectrum_stop_mhz.set("2600"))).pack(side=tk.LEFT, padx=3)
        
        # Generate Tests button inside this config frame
        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_row, text="🔄 Generate Tests", command=self._generate_tests).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="↩ Restore Defaults", command=self._restore_defaults).pack(side=tk.LEFT, padx=5)
        
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(info_frame, text="ℹ️ Connect an antenna to the selected channel. Works with MSO 4/5/6 Series.",
                 font=("Segoe UI", 9, "italic")).pack(anchor=tk.W)
        ttk.Label(info_frame, text="   Max scan frequency is limited by the scope's installed bandwidth.",
                 font=("Segoe UI", 8, "italic")).pack(anchor=tk.W)

    def _create_eye_diagram_config(self, parent):
        """Create eye diagram configuration widgets"""
        # Data Rate section
        rate_frame = ttk.LabelFrame(parent, text="Data Rate")
        rate_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row1 = ttk.Frame(rate_frame)
        row1.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row1, text="Data Rate (Gbps):").pack(side=tk.LEFT)
        self.eye_data_rate = tk.StringVar(value="1.62")
        ttk.Entry(row1, textvariable=self.eye_data_rate, width=10).pack(side=tk.LEFT, padx=10)
        
        # PLL Presets
        row2 = ttk.Frame(rate_frame)
        row2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row2, text="Presets:").pack(side=tk.LEFT)
        ttk.Button(row2, text="DP RBR", width=8,
                  command=lambda: self.eye_data_rate.set("1.62")).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="DP HBR", width=8,
                  command=lambda: self.eye_data_rate.set("2.7")).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="SATA-2", width=8,
                  command=lambda: self.eye_data_rate.set("3.0")).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="USB3", width=8,
                  command=lambda: self.eye_data_rate.set("5.0")).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="PCIe2", width=8,
                  command=lambda: self.eye_data_rate.set("5.0")).pack(side=tk.LEFT, padx=2)
        
        # Acquisition settings
        acq_frame = ttk.LabelFrame(parent, text="Acquisition")
        acq_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row3 = ttk.Frame(acq_frame)
        row3.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row3, text="Number of acquisitions:").pack(side=tk.LEFT)
        self.eye_num_acq = tk.StringVar(value="1")
        ttk.Spinbox(row3, textvariable=self.eye_num_acq, from_=1, to=1000, width=8).pack(side=tk.LEFT, padx=10)
        
        # Expected signal
        sig_frame = ttk.LabelFrame(parent, text="Expected Signal (for auto-scaling)")
        sig_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row4 = ttk.Frame(sig_frame)
        row4.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row4, text="Amplitude (mVpp):").pack(side=tk.LEFT)
        self.eye_vpp = tk.StringVar(value="650")
        ttk.Entry(row4, textvariable=self.eye_vpp, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row4, text="DC Offset (mV):").pack(side=tk.LEFT, padx=(15, 0))
        self.eye_offset = tk.StringVar(value="350")
        ttk.Entry(row4, textvariable=self.eye_offset, width=8).pack(side=tk.LEFT, padx=10)
        
        # Pass/Fail Limits
        limits_frame = ttk.LabelFrame(parent, text="Pass/Fail Limits")
        limits_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row5a = ttk.Frame(limits_frame)
        row5a.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(row5a, text="Eye Height Min (mV):").pack(side=tk.LEFT)
        self.eye_height_min = tk.StringVar(value="200")
        ttk.Entry(row5a, textvariable=self.eye_height_min, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row5a, text="Eye Height Max (mV):").pack(side=tk.LEFT, padx=(15, 0))
        self.eye_height_max = tk.StringVar(value="")
        ttk.Entry(row5a, textvariable=self.eye_height_max, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row5a, text="(blank = no limit)", font=("Segoe UI", 8, "italic")).pack(side=tk.LEFT)
        
        row5b = ttk.Frame(limits_frame)
        row5b.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(row5b, text="Eye Width Min (ps):").pack(side=tk.LEFT)
        self.eye_width_min = tk.StringVar(value="100")
        ttk.Entry(row5b, textvariable=self.eye_width_min, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row5b, text="Eye Width Max (ps):").pack(side=tk.LEFT, padx=(15, 0))
        self.eye_width_max = tk.StringVar(value="")
        ttk.Entry(row5b, textvariable=self.eye_width_max, width=8).pack(side=tk.LEFT, padx=10)
        
        # Row 6: Pattern Length (for PRBS pattern validation)
        row6 = ttk.Frame(parent)
        row6.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(row6, text="Expected Pattern Length (bits):").pack(side=tk.LEFT)
        self.eye_pattern_length = tk.StringVar(value="")
        ttk.Entry(row6, textvariable=self.eye_pattern_length, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(row6, text="(e.g., 127 for PRBS7, 255 for PRBS8, blank to skip)",
                 font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT, padx=5)
        
        # Info
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(info_frame, text="ℹ️ Single long acquisition (10 µs/div) captures many bits for eye diagram. "
                 "Set Acquisitions > 1 only if you need multi-acquisition statistics (uses population limiting). "
                 "50Ω termination. PLL selected automatically based on data rate.",
                 font=("Segoe UI", 9, "italic"), wraplength=500).pack(anchor=tk.W)
        
        # Generate Tests button inside this config frame
        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_row, text="🔄 Generate Tests", command=self._generate_tests).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="↩ Restore Defaults", command=self._restore_defaults).pack(side=tk.LEFT, padx=5)

    def _create_reference_config(self, parent):
        """Create reference waveform configuration tab (per test suite)"""
        
        # Store parent for later updates
        self.ref_config_parent = parent
        
        # Initialize reference waveform storage (UI variables)
        self.ref_waveforms = {
            "REF1": tk.StringVar(value=""),
            "REF2": tk.StringVar(value=""),
            "REF3": tk.StringVar(value=""),
            "REF4": tk.StringVar(value=""),
        }
        self.use_references = tk.BooleanVar(value=False)
        self.ref_test_numbers = tk.StringVar(value="all")
        
        # Callbacks to sync UI with current suite's reference_config
        def on_use_refs_changed(*args):
            if self.current_suite:
                self.current_suite.reference_config.enabled = self.use_references.get()
        
        def on_ref_file_changed(ref_name):
            def callback(*args):
                if self.current_suite:
                    self.current_suite.reference_config.ref_files[ref_name] = self.ref_waveforms[ref_name].get()
            return callback
        
        def on_test_numbers_changed(*args):
            if self.current_suite:
                self.current_suite.reference_config.test_numbers = self.ref_test_numbers.get()
        
        # Bind callbacks
        self.use_references.trace_add('write', on_use_refs_changed)
        self.ref_test_numbers.trace_add('write', on_test_numbers_changed)
        for ref_name in self.ref_waveforms:
            self.ref_waveforms[ref_name].trace_add('write', on_ref_file_changed(ref_name))
        
        # Header with enable checkbox
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ttk.Checkbutton(header_frame, text="Use Reference Waveforms instead of Live Acquisition",
                       variable=self.use_references).pack(anchor=tk.W)
        
        # Info label
        ttk.Label(header_frame, text="Load pre-recorded .WFM, .ISF, or .CSV files. No acquisition will occur for selected tests.",
                 font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(5, 0))
        
        # Test numbers specification
        test_num_frame = ttk.LabelFrame(parent, text="Apply References to Test Numbers")
        test_num_frame.pack(fill=tk.X, padx=15, pady=10)
        
        test_num_row = ttk.Frame(test_num_frame)
        test_num_row.pack(fill=tk.X, padx=10, pady=8)
        
        ttk.Label(test_num_row, text="Tests:").pack(side=tk.LEFT)
        ttk.Entry(test_num_row, textvariable=self.ref_test_numbers, width=30).pack(side=tk.LEFT, padx=10)
        ttk.Label(test_num_row, text='(e.g., "all" or "1-5,10,15-20")', 
                 font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT)
        
        # Reference waveform assignment frame
        ref_frame = ttk.LabelFrame(parent, text="Reference Waveform Files")
        ref_frame.pack(fill=tk.X, padx=15, pady=10)
        
        def browse_waveform(ref_name):
            """Browse for a waveform file"""
            filetypes = [
                ("Tektronix Waveforms", "*.wfm *.isf"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ]
            filepath = filedialog.askopenfilename(
                title=f"Select Waveform for {ref_name}",
                filetypes=filetypes
            )
            if filepath:
                self.ref_waveforms[ref_name].set(filepath)
        
        def clear_waveform(ref_name):
            """Clear a waveform assignment"""
            self.ref_waveforms[ref_name].set("")
        
        # Create rows for REF1-REF4 with channel mapping labels
        channel_labels = {"REF1": "CH1", "REF2": "CH2", "REF3": "CH3", "REF4": "CH4"}
        for ref_name in ["REF1", "REF2", "REF3", "REF4"]:
            row = ttk.Frame(ref_frame)
            row.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(row, text=f"{ref_name} → {channel_labels[ref_name]}:", width=14).pack(side=tk.LEFT)
            
            entry = ttk.Entry(row, textvariable=self.ref_waveforms[ref_name], width=45)
            entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            ttk.Button(row, text="Browse...", width=10,
                      command=lambda r=ref_name: browse_waveform(r)).pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="Clear", width=6,
                      command=lambda r=ref_name: clear_waveform(r)).pack(side=tk.LEFT, padx=2)
        
        # Action buttons
        btn_frame = tk.Frame(parent, bg=TekColors.BG_DARK)
        btn_frame.pack(fill=tk.X, padx=15, pady=15)
        
        RoundedButton(btn_frame, "📤 Load to Scope", command=self._load_references_to_scope,
                     width=130, height=36).pack(side=tk.LEFT, padx=5)
        RoundedButton(btn_frame, "🗑️ Clear All", command=self._clear_all_references,
                     style="secondary", width=100, height=36).pack(side=tk.LEFT, padx=5)
        
        # Status display
        self.ref_status_label = ttk.Label(parent, text="Select a test suite to configure references",
                                         font=("Segoe UI", 9, "italic"))
        self.ref_status_label.pack(anchor=tk.W, padx=20, pady=5)
        
        # Info box
        info_frame = ttk.LabelFrame(parent, text="How Reference Mode Works")
        info_frame.pack(fill=tk.X, padx=15, pady=10)
        
        info_text = """• Reference waveforms are loaded to the scope's REF1-REF4 channels
• When enabled, tests will measure from REF channels instead of CH channels
• No acquisition commands are sent - only measurements and scaling
• Vertical and horizontal scales are still adjusted as needed
• Configuration is saved per test suite"""
        
        ttk.Label(info_frame, text=info_text, font=("Segoe UI", 9),
                 justify=tk.LEFT).pack(padx=10, pady=10, anchor=tk.W)

    def _update_reference_ui_from_suite(self):
        """Update the reference config UI from the current suite's settings"""
        if not self.current_suite:
            self.ref_status_label.configure(text="Select a test suite to configure references")
            return
        
        ref_config = self.current_suite.reference_config
        
        # Update UI from suite's reference config
        self.use_references.set(ref_config.enabled)
        self.ref_test_numbers.set(ref_config.test_numbers)
        
        for ref_name in self.ref_waveforms:
            filepath = ref_config.ref_files.get(ref_name, "")
            self.ref_waveforms[ref_name].set(filepath)
        
        # Update status
        if ref_config.enabled:
            loaded = sum(1 for f in ref_config.ref_files.values() if f)
            self.ref_status_label.configure(
                text=f"Reference mode ENABLED for {self.current_suite.name} ({loaded} file(s) assigned)")
        else:
            self.ref_status_label.configure(
                text=f"Reference mode disabled for {self.current_suite.name}")

    def _load_references_to_scope(self):
        """Load reference waveform files to the oscilloscope"""
        if not self.inst.scope:
            messagebox.showerror("Error", "No oscilloscope connected")
            return
        
        loaded_count = 0
        errors = []
        
        for ref_name, filepath_var in self.ref_waveforms.items():
            filepath = filepath_var.get().strip()
            if not filepath:
                continue
            
            if not os.path.exists(filepath):
                errors.append(f"{ref_name}: File not found - {filepath}")
                continue
            
            try:
                # Convert to scope path format (forward slashes, quotes)
                # For local files, we need to transfer them first or use a network path
                scope_path = filepath.replace("\\", "/")
                
                self._log(f"Loading {ref_name} from: {filepath}")
                
                # Add the reference channel if it doesn't exist
                self.inst.scope.write(f'REF:ADDNew "{ref_name}"')
                time.sleep(0.2)
                
                # Recall the waveform to the reference
                # Note: File must be accessible from scope (local drive or network)
                self.inst.scope.write(f'RECAll:WAVEform "{scope_path}",{ref_name}')
                time.sleep(0.5)
                
                # Check for errors
                self.inst.scope.write("*ESR?")
                esr = int(self.inst.scope.read().strip())
                if esr & 0x20:  # Command error
                    self.inst.scope.write("EVMsg?")
                    err_msg = self.inst.scope.read().strip()
                    errors.append(f"{ref_name}: {err_msg}")
                else:
                    loaded_count += 1
                    self._log(f"✓ {ref_name} loaded successfully")
                
            except Exception as e:
                errors.append(f"{ref_name}: {str(e)}")
        
        # Update status
        if errors:
            self.ref_status_label.configure(
                text=f"Loaded {loaded_count} reference(s). Errors: {len(errors)}")
            error_msg = "\n".join(errors)
            messagebox.showwarning("Reference Loading", 
                                  f"Some references failed to load:\n\n{error_msg}")
        elif loaded_count > 0:
            self.ref_status_label.configure(
                text=f"✓ {loaded_count} reference(s) loaded to scope")
            self._log(f"Successfully loaded {loaded_count} reference waveform(s)")
        else:
            messagebox.showinfo("Reference Loading", 
                               "No waveform files selected. Use Browse to select files.")

    def _clear_all_references(self):
        """Clear all reference waveform assignments and optionally from scope"""
        # Clear the file paths
        for ref_var in self.ref_waveforms.values():
            ref_var.set("")
        
        # Optionally clear from scope
        if self.inst.scope:
            try:
                # Query existing references
                self.inst.scope.write("REF:LIST?")
                ref_list = self.inst.scope.read().strip()
                
                if ref_list and "REF" in ref_list:
                    if messagebox.askyesno("Clear References", 
                                          "Also clear reference waveforms from the oscilloscope?"):
                        for ref_name in ["REF1", "REF2", "REF3", "REF4"]:
                            try:
                                self.inst.scope.write(f'REF:DELete "{ref_name}"')
                            except:
                                pass
                        self._log("Cleared references from oscilloscope")
            except:
                pass
        
        self.ref_status_label.configure(text="All references cleared")
        self._log("Reference waveform assignments cleared")

    def _auto_load_references(self) -> bool:
        """Automatically load reference waveforms to scope before test execution.
        
        Called by _run_tests when reference mode is enabled.
        
        Returns:
            True if at least one reference was loaded successfully
        """
        if not self.inst.scope:
            self._log("ERROR: No oscilloscope connected for reference loading")
            return False
        
        ref_config = self.current_suite.reference_config
        if not ref_config or not ref_config.enabled:
            return False
        
        loaded_count = 0
        
        # Check both UI variables and config ref_files
        ref_sources = {}
        
        # First, try UI variables (if available)
        if hasattr(self, 'ref_waveforms'):
            for ref_name, filepath_var in self.ref_waveforms.items():
                filepath = filepath_var.get().strip()
                if filepath:
                    ref_sources[ref_name] = filepath
        
        # Also check config ref_files (may have been set programmatically)
        if ref_config.ref_files:
            for ref_name, filepath in ref_config.ref_files.items():
                if filepath and filepath.strip():
                    ref_sources[ref_name] = filepath.strip()
        
        if not ref_sources:
            self._log("No reference waveform files specified")
            return False
        
        self._log(f"Auto-loading {len(ref_sources)} reference waveform(s)...")
        
        for ref_name, filepath in ref_sources.items():
            if not os.path.exists(filepath):
                self._log(f"WARNING: {ref_name} file not found: {filepath}")
                continue
            
            try:
                # Convert to scope path format
                scope_path = filepath.replace("\\", "/")
                
                self._log(f"Loading {ref_name} from: {filepath}")
                
                # Add the reference channel if it doesn't exist
                self.inst.scope.write(f'REF:ADDNew "{ref_name}"')
                time.sleep(0.2)
                
                # Recall the waveform to the reference
                self.inst.scope.write(f'RECAll:WAVEform "{scope_path}",{ref_name}')
                time.sleep(0.5)
                
                # Enable the reference display
                self.inst.scope.write(f'DISplay:GLObal:{ref_name}:STATE ON')
                
                # Check for errors
                self.inst.scope.write("*ESR?")
                esr = int(self.inst.scope.read().strip())
                if esr & 0x20:  # Command error
                    self.inst.scope.write("EVMsg?")
                    err_msg = self.inst.scope.read().strip()
                    self._log(f"ERROR loading {ref_name}: {err_msg}")
                else:
                    loaded_count += 1
                    self._log(f"✓ {ref_name} loaded and displayed")
                
            except Exception as e:
                self._log(f"ERROR loading {ref_name}: {str(e)}")
        
        if loaded_count > 0:
            self._log(f"Successfully loaded {loaded_count} reference waveform(s)")
            # Update status label if it exists
            if hasattr(self, 'ref_status_label'):
                self.ref_status_label.configure(
                    text=f"✓ {loaded_count} reference(s) auto-loaded")
        
        return loaded_count > 0

    def _create_channel_config(self, parent):
        """Create channel configuration with probe settings"""
        ch_frame = ttk.LabelFrame(parent, text="Scope Channel Selection")
        ch_frame.pack(fill=tk.X, padx=15, pady=10)
        
        row1 = ttk.Frame(ch_frame)
        row1.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row1, text="Measurement Channel:").pack(side=tk.LEFT)
        self.scope_channel = tk.StringVar(value="1")
        ch_combo = ttk.Combobox(row1, textvariable=self.scope_channel, values=["1", "2", "3", "4", "5", "6", "7", "8"], width=5)
        ch_combo.pack(side=tk.LEFT, padx=10)
        
        probe_frame = ttk.LabelFrame(parent, text="Probe Settings")
        probe_frame.pack(fill=tk.X, padx=15, pady=10)
        
        row2 = ttk.Frame(probe_frame)
        row2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row2, text="Termination:").pack(side=tk.LEFT)
        self.ch_termination = tk.StringVar(value="1M")
        ttk.Radiobutton(row2, text="50Ω (BNC/Direct)", variable=self.ch_termination, value="50").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(row2, text="1MΩ (Passive Probe)", variable=self.ch_termination, value="1M").pack(side=tk.LEFT, padx=10)
        
        row3 = ttk.Frame(probe_frame)
        row3.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(row3, text="Bandwidth:").pack(side=tk.LEFT)
        self.ch_bandwidth = tk.StringVar(value="20E6")
        bw_combo = ttk.Combobox(row3, textvariable=self.ch_bandwidth, 
                               values=["FULL", "500E6", "250E6", "100E6", "20E6"], width=10)
        bw_combo.pack(side=tk.LEFT, padx=10)
        ttk.Label(row3, text="(Lower BW reduces noise for slow signals)").pack(side=tk.LEFT, padx=5)
        
        # Keep old variable for backwards compatibility
        self.ch1_term = self.ch_termination
        self.afg_amp = tk.StringVar(value="1.0")

    def _toggle_specific_values(self):
        """Enable/disable specific values entry based on checkbox"""
        if self.use_specific_values.get():
            self.specific_entry.configure(state='normal')
        else:
            self.specific_entry.configure(state='disabled')

    def _restore_defaults(self):
        """Restore default configuration values"""
        if self.current_suite:
            cfg = self.current_suite.config
            if self.current_suite.test_type == "afg_freq":
                self.freq_start.set(str(cfg.get("freq_start", 1000)))
                self.freq_stop.set(str(cfg.get("freq_stop", 25e6)))
                self.num_points.set(str(cfg.get("num_points", 20)))
                self.tolerance.set(str(cfg.get("tolerance", 0.2)))
                self.spacing.set(cfg.get("spacing", "logarithmic"))
                self.afg_amp.set(str(cfg.get("afg_amp", 1.0)))
            elif self.current_suite.test_type == "led_current":
                voltages = cfg.get("voltages", [2, 2.5, 3, 3.5, 4, 4.5, 5])
                self.volt_start.set(str(min(voltages)))
                self.volt_stop.set(str(max(voltages)))
                self.volt_points.set(str(len(voltages)))
                self.led_tolerance.set("300")
                self.volt_spacing.set("linear")
                self.specific_values.set(", ".join(str(v) for v in voltages))
                self.use_specific_values.set(False)
                self.scope_channel.set(str(cfg.get("channel", 3)))
            self._log("Restored default settings")

    def _show_config_for_test_type(self, test_type: str):
        """Show appropriate configuration panel for test type"""
        # Hide all config frames
        self.freq_config_frame.pack_forget()
        self.voltage_config_frame.pack_forget()
        if hasattr(self, 'spectrum_config_frame'):
            self.spectrum_config_frame.pack_forget()
        if hasattr(self, 'eye_diagram_config_frame'):
            self.eye_diagram_config_frame.pack_forget()
        
        # Show relevant frame
        if test_type == "afg_freq":
            self.freq_config_frame.pack(fill=tk.X, padx=15, pady=10)
            self.scope_channel.set("1")
            self.ch_termination.set("50")
            self.ch_bandwidth.set("FULL")
        elif test_type == "led_current":
            self.voltage_config_frame.pack(fill=tk.X, padx=15, pady=10)
            self.scope_channel.set("3")
            self.ch_termination.set("1M")
            self.ch_bandwidth.set("20E6")
        elif test_type == "spectrum_scan":
            if hasattr(self, 'spectrum_config_frame'):
                self.spectrum_config_frame.pack(fill=tk.X, padx=15, pady=10)
            self.scope_channel.set("2")
            self.ch_termination.set("1M")
            self.ch_bandwidth.set("FULL")
        elif test_type == "eye_diagram":
            if hasattr(self, 'eye_diagram_config_frame'):
                self.eye_diagram_config_frame.pack(fill=tk.X, padx=15, pady=10)
            self.scope_channel.set("1")
            self.ch_termination.set("50")
            self.ch_bandwidth.set("FULL")
        elif test_type == "agc_sample":
            # AGC Sample Test uses CH1 and CH3, no special config frame needed
            self.scope_channel.set("1")  # Primary channel (trigger source)
            self.ch_termination.set("50")
            self.ch_bandwidth.set("FULL")

    def _create_results_panel(self, parent):
        # Progress bar at top
        progress_frame = tk.Frame(parent, bg=TekColors.BG_DARK)
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_label = tk.Label(progress_frame, text="Ready", font=TekFonts.SUBHEADER,
                                    bg=TekColors.BG_DARK, fg=TekColors.TEXT_ACCENT)
        self.status_label.pack(anchor=tk.W)
        
        self.progress = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        counters = tk.Frame(progress_frame, bg=TekColors.BG_DARK)
        counters.pack(fill=tk.X, pady=5)
        self.progress_text = tk.StringVar(value="0/0")
        self.pass_count = tk.StringVar(value="0")
        self.fail_count = tk.StringVar(value="0")
        tk.Label(counters, text="Progress:", font=TekFonts.SMALL, bg=TekColors.BG_DARK, fg=TekColors.TEXT_SECONDARY).pack(side=tk.LEFT)
        tk.Label(counters, textvariable=self.progress_text, font=TekFonts.SMALL, bg=TekColors.BG_DARK, fg=TekColors.TEXT_PRIMARY).pack(side=tk.LEFT, padx=5)
        tk.Label(counters, text="Pass:", font=TekFonts.SMALL, bg=TekColors.BG_DARK, fg=TekColors.TEXT_SECONDARY).pack(side=tk.LEFT, padx=(20,0))
        tk.Label(counters, textvariable=self.pass_count, font=TekFonts.NORMAL, bg=TekColors.BG_DARK, fg=TekColors.STATUS_PASS).pack(side=tk.LEFT, padx=3)
        tk.Label(counters, text="Fail:", font=TekFonts.SMALL, bg=TekColors.BG_DARK, fg=TekColors.TEXT_SECONDARY).pack(side=tk.LEFT, padx=(20,0))
        tk.Label(counters, textvariable=self.fail_count, font=TekFonts.NORMAL, bg=TekColors.BG_DARK, fg=TekColors.STATUS_FAIL).pack(side=tk.LEFT, padx=3)
        
        # Results table - will be reconfigured based on test type
        tree_frame = tk.Frame(parent, bg=TekColors.BG_DARK)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.results_tree_frame = tree_frame
        
        # Default columns (will be updated when test suite is selected)
        cols = ('test', 'voltage', 'i_smu', 'i_scope', 'error', 'status')
        self.results_tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
        self.results_tree.heading('test', text='#')
        self.results_tree.heading('voltage', text='V Input')
        self.results_tree.heading('i_smu', text='I (SMU)')
        self.results_tree.heading('i_scope', text='I (Scope)')
        self.results_tree.heading('error', text='Error %')
        self.results_tree.heading('status', text='Status')
        self.results_tree.column('test', width=50)
        self.results_tree.column('voltage', width=80)
        self.results_tree.column('i_smu', width=100)
        self.results_tree.column('i_scope', width=100)
        self.results_tree.column('error', width=100)
        self.results_tree.column('status', width=80)
        self.results_tree.tag_configure('pass', background='#1a472a', foreground=TekColors.STATUS_PASS)
        self.results_tree.tag_configure('fail', background='#4a1a1a', foreground=TekColors.STATUS_FAIL)
        self.results_tree.tag_configure('error', background='#4a3a1a', foreground=TekColors.STATUS_ERROR)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scroll.set)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _configure_results_tree_for_test_type(self, test_type: str):
        """Reconfigure results tree columns based on test type"""
        # Clear existing items
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        if test_type == "led_current":
            # LED Current Test: #, V Input, I (SMU), I (Scope), Error (µA), Status
            self.results_tree['columns'] = ('test', 'voltage', 'i_smu', 'i_scope', 'error', 'status')
            self.results_tree.heading('test', text='#')
            self.results_tree.heading('voltage', text='V Input')
            self.results_tree.heading('i_smu', text='I (SMU)')
            self.results_tree.heading('i_scope', text='I (Scope)')
            self.results_tree.heading('error', text='Error (µA)')
            self.results_tree.heading('status', text='Status')
            self.results_tree.column('test', width=50)
            self.results_tree.column('voltage', width=80)
            self.results_tree.column('i_smu', width=100)
            self.results_tree.column('i_scope', width=100)
            self.results_tree.column('error', width=100)
            self.results_tree.column('status', width=80)
        elif test_type == "spectrum_scan":
            # Spectrum Scan: #, Frequency, Amplitude, Band
            self.results_tree['columns'] = ('rank', 'frequency', 'amplitude', 'band')
            self.results_tree.heading('rank', text='#')
            self.results_tree.heading('frequency', text='Frequency')
            self.results_tree.heading('amplitude', text='Amplitude (dBm)')
            self.results_tree.heading('band', text='Band')
            self.results_tree.column('rank', width=50)
            self.results_tree.column('frequency', width=150)
            self.results_tree.column('amplitude', width=120)
            self.results_tree.column('band', width=150)
        elif test_type == "eye_diagram":
            # Eye Diagram: Parameter, Lower Limit, Mean, Upper Limit, Min, Max, Status
            self.results_tree['columns'] = ('param', 'low_lim', 'mean', 'high_lim', 'min', 'max', 'status')
            self.results_tree.heading('param', text='Parameter')
            self.results_tree.heading('low_lim', text='Lower Limit')
            self.results_tree.heading('mean', text='Mean')
            self.results_tree.heading('high_lim', text='Upper Limit')
            self.results_tree.heading('min', text='Min')
            self.results_tree.heading('max', text='Max')
            self.results_tree.heading('status', text='Status')
            self.results_tree.column('param', width=100)
            self.results_tree.column('low_lim', width=90)
            self.results_tree.column('mean', width=140)
            self.results_tree.column('high_lim', width=90)
            self.results_tree.column('min', width=90)
            self.results_tree.column('max', width=90)
            self.results_tree.column('status', width=60)
        elif test_type in ("agc_sample", "awg70002b_pulse"):
            # AGC Sample / AWG Pulse Timing Test: #, Test Name, Nominal, Lower Limit, Upper Limit, Measured, Status
            self.results_tree['columns'] = ('test', 'measurement', 'nominal', 'low_lim', 'high_lim', 'measured', 'status')
            self.results_tree.heading('test', text='#')
            self.results_tree.heading('measurement', text='Test Name')
            self.results_tree.heading('nominal', text='Nominal')
            self.results_tree.heading('low_lim', text='Lower Limit')
            self.results_tree.heading('high_lim', text='Upper Limit')
            self.results_tree.heading('measured', text='Measured')
            self.results_tree.heading('status', text='Status')
            self.results_tree.column('test', width=30)
            self.results_tree.column('measurement', width=120)
            self.results_tree.column('nominal', width=85)
            self.results_tree.column('low_lim', width=90)
            self.results_tree.column('high_lim', width=90)
            self.results_tree.column('measured', width=85)
            self.results_tree.column('status', width=60)
        else:
            # Default format for all other tests: #, Test Name, Nominal, Lower Limit, Upper Limit, Measured, Status
            self.results_tree['columns'] = ('test', 'measurement', 'nominal', 'low_lim', 'high_lim', 'measured', 'status')
            self.results_tree.heading('test', text='#')
            self.results_tree.heading('measurement', text='Test Name')
            self.results_tree.heading('nominal', text='Nominal')
            self.results_tree.heading('low_lim', text='Lower Limit')
            self.results_tree.heading('high_lim', text='Upper Limit')
            self.results_tree.heading('measured', text='Measured')
            self.results_tree.heading('status', text='Status')
            self.results_tree.column('test', width=30)
            self.results_tree.column('measurement', width=120)
            self.results_tree.column('nominal', width=85)
            self.results_tree.column('low_lim', width=90)
            self.results_tree.column('high_lim', width=90)
            self.results_tree.column('measured', width=85)
            self.results_tree.column('status', width=60)

    def _create_screenshot_panel(self, parent):
        tk.Label(parent, text="Screenshots from oscilloscope", font=TekFonts.NORMAL,
                bg=TekColors.BG_DARK, fg=TekColors.TEXT_SECONDARY).pack(anchor=tk.W, padx=20, pady=10)
        
        # Main container with list on left, image on right
        main_frame = tk.Frame(parent, bg=TekColors.BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left side: Screenshot list
        list_frame = tk.Frame(main_frame, bg=TekColors.BG_MEDIUM, width=180)
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        list_frame.pack_propagate(False)
        
        tk.Label(list_frame, text="Screenshot List", font=TekFonts.SMALL,
                bg=TekColors.BG_MEDIUM, fg=TekColors.TEXT_SECONDARY).pack(pady=5)
        
        # Listbox with scrollbar
        list_container = tk.Frame(list_frame, bg=TekColors.BG_MEDIUM)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.screenshot_listbox = tk.Listbox(list_container, bg=TekColors.BG_CARD, 
                                              fg=TekColors.TEXT_PRIMARY, 
                                              selectbackground=TekColors.TEK_CYAN,
                                              font=TekFonts.SMALL,
                                              yscrollcommand=scrollbar.set)
        self.screenshot_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.screenshot_listbox.yview)
        
        # Bind selection event
        self.screenshot_listbox.bind('<<ListboxSelect>>', self._on_screenshot_select)
        
        # Right side: Image display
        image_frame = tk.Frame(main_frame, bg=TekColors.BG_MEDIUM)
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Container frame for the screenshot - we'll track its size
        self.screenshot_container = tk.Frame(image_frame, bg=TekColors.BG_MEDIUM)
        self.screenshot_container.pack(fill=tk.BOTH, expand=True)
        
        self.screenshot_label = tk.Label(self.screenshot_container, text="No screenshot", 
                                        font=TekFonts.NORMAL, bg=TekColors.BG_MEDIUM, 
                                        fg=TekColors.TEXT_SECONDARY)
        self.screenshot_label.pack(fill=tk.BOTH, expand=True)
        
        # Bind resize event to refit image
        self.screenshot_container.bind('<Configure>', self._on_screenshot_resize)
        self.current_screenshot_path = None
        
        # Navigation buttons below image
        nav = tk.Frame(image_frame, bg=TekColors.BG_MEDIUM)
        nav.pack(fill=tk.X, pady=10)
        RoundedButton(nav, "◀ Prev", command=self._prev_screenshot, style="secondary", width=80, height=30).pack(side=tk.LEFT, padx=5)
        self.screenshot_info = tk.StringVar(value="")
        tk.Label(nav, textvariable=self.screenshot_info, font=TekFonts.NORMAL, 
                bg=TekColors.BG_MEDIUM, fg=TekColors.TEXT_PRIMARY).pack(side=tk.LEFT, padx=20)
        RoundedButton(nav, "Next ▶", command=self._next_screenshot, style="secondary", width=80, height=30).pack(side=tk.LEFT, padx=5)
    
    def _on_screenshot_select(self, event):
        """Handle screenshot listbox selection"""
        selection = self.screenshot_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.screenshot_paths):
                self.screenshot_idx = idx
                self._show_screenshot(self.screenshot_paths[idx])
    
    def _update_screenshot_list(self):
        """Update the screenshot listbox with current paths"""
        if not hasattr(self, 'screenshot_listbox'):
            return
        self.screenshot_listbox.delete(0, tk.END)
        for i, path in enumerate(self.screenshot_paths):
            name = Path(path).name
            # Truncate long names
            if len(name) > 25:
                name = name[:22] + "..."
            self.screenshot_listbox.insert(tk.END, f"{i+1}. {name}")

    def _create_log_panel(self, parent):
        """Create log panel on the right side with SCPI color coding"""
        header = tk.Frame(parent, bg=TekColors.BG_PANEL)
        header.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(header, text="📝 SCPI Log", font=TekFonts.SUBHEADER,
                bg=TekColors.BG_PANEL, fg=TekColors.TEXT_ACCENT).pack(side=tk.LEFT)
        RoundedButton(header, "Clear", command=self._clear_log,
                     style="secondary", width=60, height=26).pack(side=tk.RIGHT)
        
        self.log_text = scrolledtext.ScrolledText(parent, font=TekFonts.MONO,
                                                  bg=TekColors.BG_MEDIUM, fg=TekColors.TEXT_PRIMARY,
                                                  wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_text.configure(state=tk.DISABLED)
        
        # Configure tags for SCPI log colors
        self.log_text.tag_configure("cmd", foreground=TekColors.SCPI_CMD)
        self.log_text.tag_configure("query", foreground=TekColors.SCPI_QUERY)
        self.log_text.tag_configure("response", foreground=TekColors.SCPI_RESPONSE)
        self.log_text.tag_configure("info", foreground=TekColors.TEXT_PRIMARY)
        self.log_text.tag_configure("error", foreground=TekColors.STATUS_FAIL)

    def _create_suites(self) -> List[TestSuite]:
        """Create built-in test suites and discover external plugins"""
        
        # All test suites now come from plugins in test_suites/ folder
        # No built-in suites - everything is discovered via plugin system
        builtin_suites = []
        
        # Discover external plugins (e.g., from test_suites/ folder)
        try:
            discovered, self.plugin_engines = discover_test_suite_plugins()
            if discovered:
                self._log(f"Discovered {len(discovered)} external test suite(s)")
            builtin_suites = discovered
        except Exception as e:
            print(f"Plugin discovery error: {e}")
            self.plugin_engines = {}
        
        return builtin_suites

    def _setup_callbacks(self):
        def _on_complete_with_pause(tp):
            """Callback that runs on the ENGINE thread. 
            Posts the result, then if it failed, waits for user response."""
            self.msg_queue.put(('complete', tp))
            if tp.status == TestStatus.FAIL:
                # Clear the event to block this (engine) thread
                self.failure_pause_event.clear()
                # Wait until UI thread sets the event (user clicks Continue/Abort)
                self.failure_pause_event.wait(timeout=300)  # 5 min max wait
        
        self.afg_engine.on_log = lambda m: self.msg_queue.put(('log', m))
        self.afg_engine.on_test_start = lambda t: self.msg_queue.put(('start', t))
        self.afg_engine.on_test_complete = _on_complete_with_pause
        self.afg_engine.on_progress = lambda p, m: self.msg_queue.put(('progress', (p, m)))
        self.afg_engine.on_screenshot = lambda p: self.msg_queue.put(('screenshot', p))
        self.afg_engine.on_complete = lambda p, f: self.msg_queue.put(('done', (p, f)))
        self.led_engine.on_log = lambda m: self.msg_queue.put(('log', m))
        self.led_engine.on_test_start = lambda t: self.msg_queue.put(('start', t))
        self.led_engine.on_test_complete = _on_complete_with_pause
        self.led_engine.on_progress = lambda p, m: self.msg_queue.put(('progress', (p, m)))
        self.led_engine.on_screenshot = lambda p: self.msg_queue.put(('screenshot', p))
        self.led_engine.on_complete = lambda p, f: self.msg_queue.put(('done', (p, f)))
        self.spectrum_engine.on_log = lambda m: self.msg_queue.put(('log', m))
        self.spectrum_engine.on_test_start = lambda t: self.msg_queue.put(('start', t))
        self.spectrum_engine.on_test_complete = _on_complete_with_pause
        self.spectrum_engine.on_progress = lambda p, m: self.msg_queue.put(('progress', (p, m)))
        self.spectrum_engine.on_complete = lambda p, f: self.msg_queue.put(('done', (p, f)))
        self.eye_engine.on_log = lambda m: self.msg_queue.put(('log', m))
        self.eye_engine.on_test_start = lambda t: self.msg_queue.put(('start', t))
        self.eye_engine.on_test_complete = _on_complete_with_pause
        self.eye_engine.on_progress = lambda p, m: self.msg_queue.put(('progress', (p, m)))
        self.eye_engine.on_screenshot = lambda p: self.msg_queue.put(('screenshot', p))
        self.eye_engine.on_complete = lambda p, f: self.msg_queue.put(('done', (p, f)))
        self.agc_engine.on_log = lambda m: self.msg_queue.put(('log', m))
        self.agc_engine.on_test_start = lambda t: self.msg_queue.put(('start', t))
        self.agc_engine.on_test_complete = _on_complete_with_pause
        self.agc_engine.on_progress = lambda p, m: self.msg_queue.put(('progress', (p, m)))
        self.agc_engine.on_screenshot = lambda p: self.msg_queue.put(('screenshot', p))
        self.agc_engine.on_complete = lambda p, f: self.msg_queue.put(('done', (p, f)))

    def _process_messages(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == 'log':
                    self._log(data)
                elif msg_type == 'scpi':
                    self._log_scpi_display(data[0], data[1])
                elif msg_type == 'start':
                    self._update_test_status(data)
                elif msg_type == 'complete':
                    self._update_test_status(data)
                    self._add_result(data)
                    self._update_counters()
                    # Check if test failed and show dialog - compare by value for plugin compatibility
                    if data.status.value == "FAIL":
                        self._show_failure_dialog(data)
                elif msg_type == 'progress':
                    self.progress.set(data[0])
                    self.status_label.configure(text=data[1])
                elif msg_type == 'screenshot':
                    self._show_screenshot(data)
                elif msg_type == 'done':
                    self._on_done(*data)
        except queue.Empty:
            pass
        self.root.after(100, self._process_messages)
    
    def _show_failure_dialog(self, tp: TestPoint):
        """Show failure dialog. Engine thread is already paused waiting for response."""
        if self.failure_dialog is not None:
            return  # Already showing a dialog
        
        # Check if "continue all" is active - if so, auto-continue without dialog
        if TestFailureDialog.continue_all_failures:
            self._log("Auto-continuing after failure (continue-all enabled)...")
            self.failure_pause_event.set()  # Resume engine thread
            return
        
        self.test_paused_for_failure = True
        self.failure_response = None
        
        def on_response(action: str, save_waveforms: bool):
            self.failure_response = action
            self.failure_save_waveforms = save_waveforms
            self.failure_dialog = None
            self.test_paused_for_failure = False
            
            if save_waveforms:
                self._save_waveforms_on_failure(tp)
            
            if action == 'abort':
                self._log("Test sequence ABORTED by user after failure", "error")
                # Set the stop flag on the engine BEFORE resuming its thread
                if self.current_engine:
                    self.current_engine.should_stop = True
            else:
                self._log("Continuing test sequence after failure...")
            
            # Resume the engine thread (it's waiting on this event)
            self.failure_pause_event.set()
        
        self.failure_dialog = TestFailureDialog(self.root, tp, on_response)
    
    def _save_waveforms_on_failure(self, tp: TestPoint):
        """Save waveforms from scope when user requests it on failure."""
        if not self.inst.scope or not self.output_dir:
            self._log("Cannot save waveforms - scope not connected or no output directory")
            return
        
        try:
            # Save waveforms for active channels (support up to 8 channels)
            timestamp = datetime.datetime.now().strftime("%H%M%S")
            for ch in range(1, 9):
                try:
                    # Check if channel is displayed
                    state = self.inst.scope_query(f"DISplay:WAVEView1:CH{ch}:STATE?")
                    if state.strip() == "1":
                        filename = f"fail_test{tp.test_id}_CH{ch}_{timestamp}.wfm"
                        filepath = self.output_dir / filename
                        scope_path = f"C:/Temp/{filename}"
                        
                        self.inst.scope_write(f'SAVe:WAVEform CH{ch},"{scope_path}"')
                        self.inst.scope_query("*OPC?")
                        self.inst.scope_write(f'FILESystem:READFile "{scope_path}"')
                        data = self.inst.scope.read_raw()
                        
                        with open(filepath, 'wb') as f:
                            f.write(data)
                        
                        # Cleanup
                        try:
                            self.inst.scope_write(f'FILESystem:DELEte "{scope_path}"')
                        except:
                            pass
                        
                        self._log(f"Saved waveform: {filename}")
                except Exception as e:
                    pass  # Channel might not be available
            
            # Also save REF waveforms if displayed (support up to 8)
            for ref in range(1, 9):
                try:
                    state = self.inst.scope_query(f"DISplay:WAVEView1:REF{ref}:STATE?")
                    if state.strip() == "1":
                        filename = f"fail_test{tp.test_id}_REF{ref}_{timestamp}.wfm"
                        filepath = self.output_dir / filename
                        scope_path = f"C:/Temp/{filename}"
                        
                        self.inst.scope_write(f'SAVe:WAVEform REF{ref},"{scope_path}"')
                        self.inst.scope_query("*OPC?")
                        self.inst.scope_write(f'FILESystem:READFile "{scope_path}"')
                        data = self.inst.scope.read_raw()
                        
                        with open(filepath, 'wb') as f:
                            f.write(data)
                        
                        try:
                            self.inst.scope_write(f'FILESystem:DELEte "{scope_path}"')
                        except:
                            pass
                        
                        self._log(f"Saved waveform: {filename}")
                except Exception as e:
                    pass
                    
        except Exception as e:
            self._log(f"Error saving waveforms: {e}", "error")

    def _log(self, msg, tag="info"):
        """Log a message with optional tag for coloring"""
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{ts}] {msg}"
        # Store in persistent log (for saving to file)
        self.persistent_scpi_log.append(log_entry)
        # Display in UI
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}] ", "info")
        self.log_text.insert(tk.END, f"{msg}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _log_scpi(self, scpi_type: str, message: str):
        """Handle SCPI log from instrument manager (may be called from worker thread)"""
        # Queue it for the main thread
        self.msg_queue.put(('scpi', (scpi_type, message)))

    def _log_scpi_display(self, scpi_type: str, message: str):
        """Display SCPI log with appropriate color (called from main thread)"""
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{ts}] {message}"
        # Store in persistent log (for saving to file)
        self.persistent_scpi_log.append(log_entry)
        # Display in UI
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}] ", "info")
        self.log_text.insert(tk.END, f"{message}\n", scpi_type)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_log(self):
        """Clear the visible log display (but keep persistent log for saving)"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)
        # Note: persistent_scpi_log is NOT cleared - it will be saved with results
    
    def _save_scpi_log(self, output_dir: Path):
        """Save the persistent SCPI log to a file"""
        if not self.persistent_scpi_log:
            return
        log_file = output_dir / "scpi_log.txt"
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Tek PTA SCPI Log\n")
                f.write(f"================\n")
                f.write(f"Test Suite: {self.current_suite.name if self.current_suite else 'Unknown'}\n")
                f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"================\n\n")
                for entry in self.persistent_scpi_log:
                    f.write(f"{entry}\n")
            self._log(f"SCPI log saved: {log_file}")
        except Exception as e:
            self._log(f"Failed to save SCPI log: {e}", "error")

    def _refresh_instruments(self):
        self._log("Checking instrument connections...")
        
        # First, check health of currently connected instruments
        health = self.inst.check_connection_health()
        for inst_type, (is_healthy, msg) in health.items():
            if not is_healthy:
                self._log(f"⚠️ {inst_type.upper()}: {msg}")
                # Offer to reconnect
                serial = None
                if inst_type == 'scope' and self.inst.scope_info:
                    serial = self.inst.scope_info.serial_number
                    inst_type_name = "Oscilloscope"
                elif inst_type == 'smu' and self.inst.smu_info:
                    serial = self.inst.smu_info.serial_number
                    inst_type_name = "SMU"
                elif inst_type == 'awg' and self.inst.awg_info:
                    serial = self.inst.awg_info.serial_number
                    inst_type_name = "Function Generator"
                
                if serial:
                    self._log(f"Will search for {inst_type_name} S/N: {serial}")
        
        self._log("Discovering instruments...")
        self._log("(Scanning known subnets - should take ~5-10 seconds)")
        for w in self.instruments_frame.winfo_children():
            w.destroy()
        scanning_lbl = tk.Label(self.instruments_frame, text="Scanning known subnets...",
                font=TekFonts.SMALL, bg=TekColors.BG_CARD, fg=TekColors.TEXT_ACCENT)
        scanning_lbl.pack(pady=20)
        self.root.update()
        instruments = self.inst.discover_instruments()
        scanning_lbl.destroy()
        
        # Also add any connected instruments that weren't discovered
        # (e.g., SMU connected via Add button but not on discoverable network)
        discovered_addrs = {inst.visa_address for inst in instruments}
        
        if self.inst.smu_info and self.inst.smu_info.visa_address not in discovered_addrs:
            self.inst.smu_info.is_connected = True
            instruments.append(self.inst.smu_info)
        
        if self.inst.scope_info and self.inst.scope_info.visa_address not in discovered_addrs:
            self.inst.scope_info.is_connected = True
            instruments.append(self.inst.scope_info)
        
        if self.inst.awg_info and self.inst.awg_info.visa_address not in discovered_addrs:
            self.inst.awg_info.is_connected = True
            instruments.append(self.inst.awg_info)
        
        if not instruments:
            tk.Label(self.instruments_frame, text="No instruments found.\nTry Add button with IP address.",
                    font=TekFonts.SMALL, bg=TekColors.BG_CARD, fg=TekColors.TEXT_SECONDARY).pack(pady=20)
            self._log("No instruments found")
            return
        self._log(f"Found {len(instruments)} instrument(s)")
        for inst in instruments:
            self._create_instrument_card(self.instruments_frame, inst)

    def _add_instrument(self):
        addr = simpledialog.askstring("Add Instrument",
            "Enter IP address or VISA address:\n\nExamples:\n  169.254.10.36\n  TCPIP::192.168.1.100::INSTR",
            parent=self.root)
        if addr:
            self._log(f"Connecting to {addr}...")
            ok, msg, inst = self.inst.add_manual(addr)
            if ok:
                self._log(msg)
                self._create_instrument_card(self.instruments_frame, inst)
            else:
                messagebox.showerror("Failed", msg)
                self._log(f"Failed: {msg}")

    def _connect_scope(self, inst: InstrumentInfo):
        self._log(f"Connecting to {inst.model}...")
        ok, msg = self.inst.connect_scope(inst.visa_address)
        if ok:
            self._log(msg)
            inst.is_connected = True
            has_probe, probe_type = self.inst.check_probe(1)
            if not has_probe:
                result = messagebox.askyesno("Channel Setup",
                    "No probe detected on CH1.\n\nSet CH1 termination to 50Ω for BNC cable connection?",
                    parent=self.root)
                if result:
                    self.ch1_term.set("50")
                    self._log("CH1 termination set to 50Ω")
            else:
                self._log(f"Probe detected: {probe_type}")
                self.ch1_term.set("1M")
            self._refresh_instruments()
        else:
            messagebox.showerror("Failed", msg)

    def _connect_smu(self, inst: InstrumentInfo):
        self._log(f"Connecting to {inst.model}...")
        ok, msg = self.inst.connect_smu(inst.visa_address)
        if ok:
            self._log(msg)
            inst.is_connected = True
            self._refresh_instruments()
        else:
            messagebox.showerror("Failed", msg)

    def _connect_awg(self, inst: InstrumentInfo):
        self._log(f"Connecting to {inst.model}...")
        ok, msg = self.inst.connect_awg(inst.visa_address)
        if ok:
            self._log(msg)
            inst.is_connected = True
            self._refresh_instruments()
        else:
            messagebox.showerror("Failed", msg)

    def _show_suite_selector(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Test Suite")
        dialog.geometry("1100x750")  # Slightly taller for sort controls
        dialog.configure(bg=TekColors.BG_DARK)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        # Header
        header_frame = tk.Frame(dialog, bg=TekColors.BG_DARK)
        header_frame.pack(fill=tk.X, padx=20, pady=(15, 5))
        
        tk.Label(header_frame, text="📋 Available Test Suites", font=TekFonts.HEADER,
                bg=TekColors.BG_DARK, fg=TekColors.TEXT_ACCENT).pack(side=tk.LEFT)
        
        tk.Label(header_frame, text=f"{len(self.test_suites)} suites loaded", 
                font=TekFonts.SMALL, bg=TekColors.BG_DARK, 
                fg=TekColors.TEXT_DIM).pack(side=tk.RIGHT)
        
        # Sort controls
        sort_frame = tk.Frame(dialog, bg=TekColors.BG_DARK)
        sort_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        tk.Label(sort_frame, text="Sort by:", font=TekFonts.SMALL,
                bg=TekColors.BG_DARK, fg=TekColors.TEXT_SECONDARY).pack(side=tk.LEFT)
        
        sort_var = tk.StringVar(value="default")
        
        def apply_sort():
            nonlocal sorted_suites
            sort_type = sort_var.get()
            if sort_type == "name":
                sorted_suites = sorted(self.test_suites, key=lambda s: s.name.lower())
            elif sort_type == "recent":
                sorted_suites = sorted(self.test_suites, 
                                      key=lambda s: s.modified_time or "0000-00-00", reverse=True)
            else:  # default - plugin order
                sorted_suites = list(self.test_suites)
            rebuild_list()
        
        ttk.Radiobutton(sort_frame, text="Default", variable=sort_var, value="default",
                       command=apply_sort).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(sort_frame, text="Name (A-Z)", variable=sort_var, value="name",
                       command=apply_sort).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(sort_frame, text="Recently Modified", variable=sort_var, value="recent",
                       command=apply_sort).pack(side=tk.LEFT, padx=5)
        
        # Main frame with scrollable canvas
        main_frame = tk.Frame(dialog, bg=TekColors.BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        canvas = tk.Canvas(main_frame, bg=TekColors.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=TekColors.BG_DARK)
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        
        def configure_scroll_frame(event):
            canvas.itemconfig(canvas_window, width=event.width - 4)
        canvas.bind('<Configure>', configure_scroll_frame)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        dialog.bind_all("<MouseWheel>", on_mousewheel)
        
        selected = tk.IntVar(value=0)
        sorted_suites = list(self.test_suites)  # Default order
        
        def rebuild_list():
            # Clear existing cards
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            
            for i, suite in enumerate(sorted_suites):
                # Card container
                card = tk.Frame(scroll_frame, bg=TekColors.BG_CARD)
                card.pack(fill=tk.X, pady=4, padx=5)
                
                inner = tk.Frame(card, bg=TekColors.BG_CARD)
                inner.pack(fill=tk.X, padx=12, pady=10)
                
                # Top row: Radio button + Name + Modified date
                top_row = tk.Frame(inner, bg=TekColors.BG_CARD)
                top_row.pack(fill=tk.X)
                
                rb = tk.Radiobutton(top_row, variable=selected, value=i, bg=TekColors.BG_CARD,
                                   fg=TekColors.TEXT_PRIMARY, selectcolor=TekColors.BG_LIGHT,
                                   activebackground=TekColors.BG_CARD)
                rb.pack(side=tk.LEFT)
                
                tk.Label(top_row, text=suite.name, font=TekFonts.SUBHEADER,
                        bg=TekColors.BG_CARD, fg=TekColors.TEXT_PRIMARY).pack(side=tk.LEFT, padx=(5, 0))
                
                # Modification date on the right
                mod_time = suite.modified_time if suite.modified_time else datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                tk.Label(top_row, text=f"📅 {mod_time}", font=("Segoe UI", 8),
                        bg=TekColors.BG_CARD, fg=TekColors.TEXT_DIM).pack(side=tk.RIGHT, padx=(10, 0))
                
                # Required instruments
                if suite.required_instruments:
                    req_text = "⚡ Requires: " + ", ".join(suite.required_instruments)
                    tk.Label(inner, text=req_text, font=("Segoe UI", 9, "italic"),
                            bg=TekColors.BG_CARD, fg=TekColors.TEK_CYAN,
                            anchor=tk.W).pack(fill=tk.X, padx=(25, 0), pady=(2, 0))
                
                # Description
                desc_text = suite.description.replace('\n', ' ').strip()
                if len(desc_text) > 200:
                    desc_text = desc_text[:200] + "..."
                
                tk.Label(inner, text=desc_text, font=TekFonts.SMALL,
                        bg=TekColors.BG_CARD, fg=TekColors.TEXT_SECONDARY,
                        anchor=tk.W, wraplength=950, justify=tk.LEFT).pack(fill=tk.X, padx=(25, 0), pady=(3, 0))
        
        # Initial build
        rebuild_list()
        
        # Button frame at the bottom
        btn_frame = tk.Frame(dialog, bg=TekColors.BG_DARK)
        btn_frame.pack(fill=tk.X, padx=20, pady=(5, 15))
        
        def select():
            dialog.unbind_all("<MouseWheel>")
            self._load_suite(sorted_suites[selected.get()])
            dialog.destroy()
        
        def cancel():
            dialog.unbind_all("<MouseWheel>")
            dialog.destroy()
        
        RoundedButton(btn_frame, "✓ Select", command=select, style="success", width=120).pack(side=tk.RIGHT, padx=5)
        RoundedButton(btn_frame, "Cancel", command=cancel, style="secondary", width=100).pack(side=tk.RIGHT)
        
        # Center dialog on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 1100) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 750) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _browse_plugin_file(self):
        """Open file dialog to import a test suite plugin file"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Import Test Suite Plugin",
            filetypes=[
                ("Python files", "*.py"),
                ("All files", "*.*")
            ],
            initialdir=Path.home()
        )
        
        if not file_path:
            return
        
        file_path = Path(file_path)
        
        try:
            suites, engines = import_plugin_file(file_path)
            
            if not suites:
                TekStyledDialog.showwarning(
                    self.root,
                    "No Test Suites Found",
                    f"No test suites were found in {file_path.name}.\n\n"
                    "Make sure the file has a register_suites() function "
                    "that returns a list of TestSuitePlugin objects."
                )
                return
            
            # Add discovered suites and engines
            self.test_suites.extend(suites)
            if hasattr(self, 'plugin_engines'):
                self.plugin_engines.update(engines)
            else:
                self.plugin_engines = engines
            
            TekStyledDialog.showinfo(
                self.root,
                "Plugins Loaded",
                f"Loaded {len(suites)} test suite(s) from {file_path.name}:\n\n"
                + "\n".join(f"• {s.name}" for s in suites)
            )
            
            self._log(f"Imported {len(suites)} test suite(s) from {file_path.name}")
            
        except Exception as e:
            TekStyledDialog.showerror(
                self.root,
                "Import Error",
                f"Failed to import plugin file:\n{e}"
            )

    def _load_suite(self, suite: TestSuite):
        self.current_suite = suite
        self.suite_label.configure(text=f"Running: {suite.name}")
        self.suite_desc_label.configure(text=suite.description)
        cfg = suite.config
        
        # Show appropriate config panel and results columns
        self._show_config_for_test_type(suite.test_type)
        self._configure_results_tree_for_test_type(suite.test_type)
        
        if suite.test_type == "afg_freq":
            self.freq_start.set(str(cfg.get("freq_start", 1000)))
            self.freq_stop.set(str(cfg.get("freq_stop", 25e6)))
            self.num_points.set(str(cfg.get("num_points", 20)))
            self.tolerance.set(str(cfg.get("tolerance", 0.2)))
            self.afg_amp.set(str(cfg.get("afg_amp", 1.0)))
            self.spacing.set(cfg.get("spacing", "logarithmic"))
            self.current_engine = self.afg_engine
        elif suite.test_type == "led_current":
            voltages = cfg.get("voltages", [2, 2.5, 3, 3.5, 4, 4.5, 5])
            self.volt_start.set(str(min(voltages)))
            self.volt_stop.set(str(max(voltages)))
            self.volt_points.set(str(len(voltages)))
            self.specific_values.set(", ".join(str(v) for v in voltages))
            self.scope_channel.set(str(cfg.get("channel", 3)))
            self.current_engine = self.led_engine
            # Update shunt resistance in engine
            self.led_engine.SHUNT_RESISTANCE = float(self.shunt_resistance.get())
        elif suite.test_type == "spectrum_scan":
            self.spectrum_start_mhz.set(str(cfg.get("start_mhz", 80)))
            self.spectrum_stop_mhz.set(str(cfg.get("stop_mhz", 120)))
            self.scope_channel.set(str(cfg.get("channel", 2)))
            self.current_engine = self.spectrum_engine
        elif suite.test_type == "eye_diagram":
            self.eye_data_rate.set(str(cfg.get("data_rate_bps", 1.62e9) / 1e9))
            self.eye_num_acq.set(str(cfg.get("num_acquisitions", 1)))  # Default to single long acquisition
            self.eye_vpp.set(str(cfg.get("expected_vpp", 0.650) * 1000))  # V to mV
            self.eye_offset.set(str(cfg.get("expected_offset", 0.350) * 1000))  # V to mV
            # Load limits if present
            if "eye_height_min" in cfg:
                self.eye_height_min.set(str(cfg.get("eye_height_min", 200)))
            if "eye_width_min" in cfg:
                self.eye_width_min.set(str(cfg.get("eye_width_min", 100)))
            if "pattern_length" in cfg:
                self.eye_pattern_length.set(str(cfg.get("pattern_length", "")))
            self.scope_channel.set(str(cfg.get("channel", 1)))
            self.current_engine = self.eye_engine
        elif suite.test_type == "agc_sample":
            # AGC Sample Test - configure engine from suite config
            self.agc_engine.channel_from = cfg.get("channel_from", 1)
            self.agc_engine.channel_to = cfg.get("channel_to", 3)
            self.agc_engine.expected_delay = cfg.get("expected_delay", 10e-6)
            self.agc_engine.delay_tolerance_pct = cfg.get("delay_tolerance_pct", 5.0)
            self.agc_engine.expected_rise_time = cfg.get("expected_rise_time", 100e-9)
            self.agc_engine.signal_high = cfg.get("signal_high", 2.5)
            self.agc_engine.signal_low = cfg.get("signal_low", 0.0)
            self.agc_engine.trigger_level = cfg.get("trigger_level", 1.25)
            self.agc_engine.horizontal_position = cfg.get("horizontal_position", 10)
            self.scope_channel.set(str(cfg.get("channel_from", 1)))
            self.current_engine = self.agc_engine
        elif suite.test_type in self.plugin_engines:
            # Custom plugin engine - instantiate and wire up callbacks
            engine_class = self.plugin_engines[suite.test_type]
            engine = engine_class(self.inst)
            engine.on_log = lambda m: self.msg_queue.put(('log', m))
            engine.on_progress = lambda p, m: self.msg_queue.put(('progress', (p, m)))
            engine.on_test_start = lambda t: self.msg_queue.put(('start', t))
            # Use pause-on-failure callback (same as built-in engines)
            # Compare by value since plugin uses its own TestStatus enum
            def _plugin_on_complete(tp):
                self.msg_queue.put(('complete', tp))
                if tp.status.value == "FAIL":
                    self.failure_pause_event.clear()
                    self.failure_pause_event.wait(timeout=300)
            engine.on_test_complete = _plugin_on_complete
            engine.on_screenshot = lambda p: self.msg_queue.put(('screenshot', p))
            engine.on_complete = lambda p, f: self.msg_queue.put(('done', (p, f)))
            engine.test_points = engine.generate_test_points(cfg)
            self.current_engine = engine
        
        self._log(f"Loaded: {suite.name}")
        self._update_reference_ui_from_suite()  # Update reference config UI
        self._generate_tests()

    def _generate_tests(self):
        if not self.current_suite:
            messagebox.showwarning("No Suite", "Please select a test suite first.")
            return
        try:
            if self.current_suite.test_type == "afg_freq":
                self.afg_engine.generate_test_points(
                    float(self.freq_start.get()), float(self.freq_stop.get()),
                    int(self.num_points.get()), float(self.tolerance.get()), self.spacing.get())
                self._populate_test_list(self.afg_engine.test_points)
            elif self.current_suite.test_type == "led_current":
                # Generate voltages based on UI settings
                if self.use_specific_values.get():
                    # Parse specific values
                    values_str = self.specific_values.get()
                    voltages = [float(v.strip()) for v in values_str.split(",") if v.strip()]
                else:
                    # Generate from range
                    start = float(self.volt_start.get())
                    stop = float(self.volt_stop.get())
                    points = int(self.volt_points.get())
                    if self.volt_spacing.get() == "linear":
                        step = (stop - start) / (points - 1) if points > 1 else 0
                        voltages = [start + i * step for i in range(points)]
                    else:  # logarithmic
                        import numpy as np
                        voltages = list(np.logspace(np.log10(start), np.log10(stop), points))
                
                # Update tolerance in engine  
                self.led_engine.TOLERANCE_UA = float(self.led_tolerance.get())  # Now in µA
                self.led_engine.SHUNT_RESISTANCE = float(self.shunt_resistance.get())
                self.led_engine.generate_test_points(voltages)
                self._populate_test_list(self.led_engine.test_points)
            elif self.current_suite.test_type == "spectrum_scan":
                start_mhz = float(self.spectrum_start_mhz.get())
                stop_mhz = float(self.spectrum_stop_mhz.get())
                self.spectrum_engine.generate_test_points(start_mhz, stop_mhz)
                self._populate_test_list(self.spectrum_engine.test_points)
            elif self.current_suite.test_type == "eye_diagram":
                self.eye_engine.data_rate_bps = float(self.eye_data_rate.get()) * 1e9
                self.eye_engine.num_acquisitions = int(self.eye_num_acq.get())
                self.eye_engine.expected_vpp = float(self.eye_vpp.get()) / 1000  # mV to V
                self.eye_engine.expected_offset = float(self.eye_offset.get()) / 1000  # mV to V
                self.eye_engine.generate_test_points()
                self._populate_test_list(self.eye_engine.test_points)
            elif self.current_suite.test_type == "agc_sample":
                self.agc_engine.generate_test_points()
                self._populate_test_list(self.agc_engine.test_points)
            elif self.current_suite.test_type in self.plugin_engines:
                # Plugin engine - test_points already generated in _load_suite
                if self.current_engine and self.current_engine.test_points:
                    self._populate_test_list(self.current_engine.test_points)
            self._clear_results()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _populate_test_list(self, test_points: List[TestPoint]):
        for w in self.test_list_frame.winfo_children():
            w.destroy()
        self.test_checkboxes.clear()
        self.test_status_labels.clear()
        for tp in test_points:
            row = tk.Frame(self.test_list_frame, bg=TekColors.BG_CARD)
            row.pack(fill=tk.X, pady=1)
            var = tk.BooleanVar(value=tp.enabled)
            cb = tk.Checkbutton(row, variable=var, bg=TekColors.BG_CARD, selectcolor=TekColors.BG_LIGHT,
                               command=lambda t=tp, v=var: setattr(t, 'enabled', v.get()))
            cb.pack(side=tk.LEFT, padx=5)
            self.test_checkboxes[tp.test_id] = var
            lbl = tk.Label(row, text="●", font=("Segoe UI", 10), bg=TekColors.BG_CARD, fg=TekColors.STATUS_NOT_RUN)
            lbl.pack(side=tk.LEFT, padx=5)
            self.test_status_labels[tp.test_id] = lbl
            tk.Label(row, text=tp.name, font=TekFonts.SMALL, bg=TekColors.BG_CARD, fg=TekColors.TEXT_PRIMARY).pack(side=tk.LEFT)
        self._log(f"Generated {len(test_points)} test points")

    def _select_all(self):
        if self.current_engine:
            for tp in self.current_engine.test_points:
                tp.enabled = True
                if tp.test_id in self.test_checkboxes:
                    self.test_checkboxes[tp.test_id].set(True)

    def _select_none(self):
        if self.current_engine:
            for tp in self.current_engine.test_points:
                tp.enabled = False
                if tp.test_id in self.test_checkboxes:
                    self.test_checkboxes[tp.test_id].set(False)

    def _update_test_status(self, tp: TestPoint):
        if tp.test_id not in self.test_status_labels:
            return
        # Compare by value since plugin may use different TestStatus enum
        colors_map = {"PASS": TekColors.STATUS_PASS, "FAIL": TekColors.STATUS_FAIL,
                  "Running": TekColors.STATUS_RUNNING, "ERROR": TekColors.STATUS_ERROR,
                  "Not Run": TekColors.STATUS_NOT_RUN}
        self.test_status_labels[tp.test_id].configure(fg=colors_map.get(tp.status.value, TekColors.STATUS_NOT_RUN))

    def _clear_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.screenshot_paths.clear()
        if hasattr(self, 'screenshot_listbox'):
            self.screenshot_listbox.delete(0, tk.END)
        self.pass_count.set("0")
        self.fail_count.set("0")
        self.progress_text.set("0/0")
        self.progress.set(0)

    def _add_result(self, tp: TestPoint):
        # Compare by value since plugin may use different TestStatus enum
        tag = {'PASS': 'pass', 'FAIL': 'fail', 'ERROR': 'error'}.get(tp.status.value, '')
        
        if self.current_suite and self.current_suite.test_type == "led_current":
            # LED Current Test: #, V Input, I (SMU), I (Scope), Error (µA), Status
            voltage = tp.extra_data.get('voltage', tp.nominal_value)
            smu_curr = tp.extra_data.get('smu_current_mA', 0)
            scope_curr = tp.extra_data.get('scope_current_mA', 0)
            error_uA = tp.extra_data.get('error_uA', 0)
            error_str = f"{error_uA:+.1f} µA" if tp.measured_value else "---"
            self.results_tree.insert('', tk.END, 
                values=(tp.test_id, f"{voltage:.2f} V", f"{smu_curr:.3f} mA", 
                       f"{scope_curr:.3f} mA", error_str, tp.status.value), 
                tags=(tag,))
        elif self.current_suite and self.current_suite.test_type == "spectrum_scan":
            # Spectrum Scan: Display top 10 peaks
            peaks = tp.extra_data.get('peaks', [])
            for i, peak in enumerate(peaks[:10], 1):
                self.results_tree.insert('', tk.END, 
                    values=(i, peak.format_frequency(), f"{peak.amplitude_dbm:.1f}", peak.band_name), 
                    tags=('pass',))  # All peaks show as green
        elif self.current_suite and self.current_suite.test_type == "eye_diagram":
            # Eye Diagram: Display eye height and eye width statistics
            # Columns: ('param', 'low_lim', 'mean', 'high_lim', 'min', 'max', 'status')
            eh = tp.extra_data.get('eye_height', {})
            ew = tp.extra_data.get('eye_width', {})
            eh_limits = tp.extra_data.get('eye_height_limits', {})
            ew_limits = tp.extra_data.get('eye_width_limits', {})
            num_acq = tp.extra_data.get('num_acquisitions', 0)
            
            def format_eye_value(val, scale, unit):
                """Format eye measurement values, handling invalid/infinity values"""
                if val is None:
                    return "---"
                try:
                    v = float(val) * scale
                    # Check for invalid values (9.9e37 is Tek's "invalid" marker)
                    if abs(v) > 1e30 or math.isnan(v) or math.isinf(v):
                        return "Invalid"
                    return f"{v:.2f} {unit}"
                except (ValueError, TypeError):
                    return "---"
            
            def format_limit(val, scale, unit):
                """Format limit value"""
                if val is None:
                    return "---"
                try:
                    v = float(val) * scale
                    return f"{v:.1f} {unit}"
                except (ValueError, TypeError):
                    return "---"
            
            def check_status(mean_val, min_limit, max_limit):
                """Check if mean value is within limits"""
                if mean_val is None:
                    return "ERROR"
                try:
                    mean_f = float(mean_val)
                    if abs(mean_f) > 1e30 or math.isnan(mean_f) or math.isinf(mean_f):
                        return "ERROR"
                    # Check limits
                    if min_limit is not None and mean_f < min_limit:
                        return "FAIL"
                    if max_limit is not None and mean_f > max_limit:
                        return "FAIL"
                    if min_limit is not None or max_limit is not None:
                        return "PASS"
                    return "Info"  # No limits defined
                except (ValueError, TypeError):
                    return "ERROR"
            
            # Eye Height row
            if eh:
                eh_status = check_status(eh.get('mean'), eh_limits.get('min'), eh_limits.get('max'))
                eh_tag = {'PASS': 'pass', 'FAIL': 'fail', 'ERROR': 'error'}.get(eh_status, '')
                self.results_tree.insert('', tk.END,
                    values=("Eye Height", 
                           format_limit(eh_limits.get('min'), 1000, "mV"),
                           format_eye_value(eh.get('mean'), 1000, "mV"),
                           format_limit(eh_limits.get('max'), 1000, "mV"),
                           format_eye_value(eh.get('min'), 1000, "mV"),
                           format_eye_value(eh.get('max'), 1000, "mV"),
                           eh_status),
                    tags=(eh_tag,))
            
            # Eye Width row
            if ew:
                ew_status = check_status(ew.get('mean'), ew_limits.get('min'), ew_limits.get('max'))
                ew_tag = {'PASS': 'pass', 'FAIL': 'fail', 'ERROR': 'error'}.get(ew_status, '')
                ui_pct = tp.extra_data.get('eye_width_ui_pct', 0)
                ui_str = f" ({ui_pct:.1f}%UI)" if ui_pct and ui_pct < 1e10 else ""
                mean_str = format_eye_value(ew.get('mean'), 1e12, "ps")
                if mean_str != "Invalid" and mean_str != "---" and ui_str:
                    mean_str = mean_str.replace(" ps", f"{ui_str}")
                self.results_tree.insert('', tk.END,
                    values=("Eye Width",
                           format_limit(ew_limits.get('min'), 1e12, "ps"),
                           mean_str,
                           format_limit(ew_limits.get('max'), 1e12, "ps"),
                           format_eye_value(ew.get('min'), 1e12, "ps"),
                           format_eye_value(ew.get('max'), 1e12, "ps"),
                           ew_status),
                    tags=(ew_tag,))
            
            # Pattern Length row
            pl = tp.extra_data.get('pattern_length', {})
            pl_expected = tp.extra_data.get('pattern_length_expected')
            pl_value = pl.get('value') if pl else None
            pl_status = "Info"
            pl_tag = ''
            if pl_expected is not None:
                if pl_value is not None:
                    if pl_value == pl_expected:
                        pl_status = "PASS"
                        pl_tag = 'pass'
                    else:
                        pl_status = "FAIL"
                        pl_tag = 'fail'
                else:
                    pl_status = "ERROR"
                    pl_tag = 'error'
            
            pl_measured = f"{pl_value} bits" if pl_value else "---"
            pl_expected_str = f"{pl_expected} bits" if pl_expected else "---"
            
            self.results_tree.insert('', tk.END,
                values=("Pattern Length",
                       pl_expected_str,
                       pl_measured,
                       pl_expected_str,
                       "---", "---",
                       pl_status),
                tags=(pl_tag,))
            
            # Data Rate (measured) row
            dr = tp.extra_data.get('data_rate_measured', {})
            expected_dr = tp.extra_data.get('data_rate_bps', 0)
            if dr:
                dr_mean = dr.get('mean', 0)
                dr_measured_str = f"{dr_mean/1e9:.6f} Gbps" if dr_mean else "---"
                dr_expected_str = f"{expected_dr/1e9:.3f} Gbps" if expected_dr else "---"
                # Calculate error percentage
                if dr_mean and expected_dr:
                    dr_error_pct = abs(dr_mean - expected_dr) / expected_dr * 100
                    dr_status = "PASS" if dr_error_pct < 1.0 else "Info"  # Within 1% = PASS
                    dr_tag = 'pass' if dr_status == "PASS" else ''
                else:
                    dr_status = "Info"
                    dr_tag = ''
                self.results_tree.insert('', tk.END,
                    values=("Data Rate",
                           dr_expected_str,
                           dr_measured_str,
                           dr_expected_str,
                           f"{dr.get('min', 0)/1e9:.6f} Gbps" if dr.get('min') else "---",
                           f"{dr.get('max', 0)/1e9:.6f} Gbps" if dr.get('max') else "---",
                           dr_status),
                    tags=(dr_tag,))
            
            # Deterministic Jitter (DJ) row
            dj = tp.extra_data.get('dj', {})
            if dj:
                dj_mean = dj.get('mean', 0)
                dj_measured_str = f"{dj_mean*1e12:.2f} ps" if dj_mean else "---"
                self.results_tree.insert('', tk.END,
                    values=("DJ (Det. Jitter)",
                           "---",
                           dj_measured_str,
                           "---",
                           f"{dj.get('min', 0)*1e12:.2f} ps" if dj.get('min') else "---",
                           f"{dj.get('max', 0)*1e12:.2f} ps" if dj.get('max') else "---",
                           "Info"),
                    tags=('',))
            
            # Info row with PLL and acquisitions
            pll = tp.extra_data.get('selected_pll', 'N/A')
            ref_mode = tp.extra_data.get('reference_mode', False)
            acq_str = "REF" if ref_mode else str(num_acq)
            self.results_tree.insert('', tk.END,
                values=(f"PLL: {pll}", 
                       f"Acquisitions: {acq_str}",
                       "",
                       "", "", "", ""),
                tags=('',))
        elif self.current_suite and self.current_suite.test_type in ("agc_sample", "awg70002b_pulse"):
            # AGC Sample / AWG Pulse Timing Test: #, Test Name, Nominal, Lower Limit, Upper Limit, Measured, Status
            nom_str = format_si(tp.nominal_value, "s")
            meas_str = format_si(tp.measured_value, "s") if tp.measured_value else "---"
            low_str = format_si(tp.lower_limit, "s") if tp.has_limits else "---"
            high_str = format_si(tp.upper_limit, "s") if tp.has_limits else "---"
            status_str = tp.status.value if tp.has_limits else "Info"
            
            self.results_tree.insert('', tk.END,
                values=(tp.test_id, tp.name, nom_str, low_str, high_str, meas_str, status_str),
                tags=(tag,))
        else:
            # Default format: #, Test Name, Nominal, Lower Limit, Upper Limit, Measured, Status
            # Format values based on unit type
            if tp.unit == "Hz":
                nom_str = format_si(tp.nominal_value, "Hz")
                meas_str = format_si(tp.measured_value, "Hz", precision=6) if tp.measured_value else "---"
                low_str = format_si(tp.lower_limit, "Hz") if tp.has_limits else "---"
                high_str = format_si(tp.upper_limit, "Hz") if tp.has_limits else "---"
            elif tp.unit in ("s", "sec", "seconds"):
                nom_str = format_si(tp.nominal_value, "s")
                meas_str = format_si(tp.measured_value, "s") if tp.measured_value else "---"
                low_str = format_si(tp.lower_limit, "s") if tp.has_limits else "---"
                high_str = format_si(tp.upper_limit, "s") if tp.has_limits else "---"
            elif tp.unit in ("V", "A", "W", "Ohm", "F", "H"):
                nom_str = format_si(tp.nominal_value, tp.unit)
                meas_str = format_si(tp.measured_value, tp.unit) if tp.measured_value else "---"
                low_str = format_si(tp.lower_limit, tp.unit) if tp.has_limits else "---"
                high_str = format_si(tp.upper_limit, tp.unit) if tp.has_limits else "---"
            elif tp.unit in ("Mbps", "bps", "bits"):
                # Data rate and bit-related units
                nom_str = f"{tp.nominal_value:.3f} {tp.unit}"
                meas_str = f"{tp.measured_value:.3f} {tp.unit}" if tp.measured_value else "---"
                low_str = f"{tp.lower_limit:.3f} {tp.unit}" if tp.has_limits else "---"
                high_str = f"{tp.upper_limit:.3f} {tp.unit}" if tp.has_limits else "---"
            else:
                # Generic formatting
                nom_str = format_si(tp.nominal_value, tp.unit) if tp.unit else f"{tp.nominal_value:.6g}"
                meas_str = format_si(tp.measured_value, tp.unit) if tp.measured_value else "---"
                low_str = format_si(tp.lower_limit, tp.unit) if tp.has_limits else "---"
                high_str = format_si(tp.upper_limit, tp.unit) if tp.has_limits else "---"
            
            status_str = tp.status.value if tp.has_limits else "Info"
            self.results_tree.insert('', tk.END,
                values=(tp.test_id, tp.name, nom_str, low_str, high_str, meas_str, status_str),
                tags=(tag,))
        
        self.results_tree.yview_moveto(1)
        if tp.screenshot_path:
            self.screenshot_paths.append(tp.screenshot_path)
            self._update_screenshot_list()

    def _update_counters(self):
        if not self.current_engine:
            return
        tps = self.current_engine.test_points
        # Compare by value since plugin may use different TestStatus enum
        p = sum(1 for t in tps if t.status.value == "PASS")
        f = sum(1 for t in tps if t.status.value == "FAIL")
        r = sum(1 for t in tps if t.status.value not in ["Not Run", "Skipped"])
        self.pass_count.set(str(p))
        self.fail_count.set(str(f))
        self.progress_text.set(f"{r}/{len(tps)}")

    def _on_screenshot_resize(self, event=None):
        """Refit current screenshot when container resizes"""
        if self.current_screenshot_path and os.path.exists(self.current_screenshot_path):
            self._show_screenshot(self.current_screenshot_path, from_resize=True)

    def _show_screenshot(self, path, from_resize=False):
        if not PIL_AVAILABLE or not os.path.exists(path):
            self.screenshot_label.configure(text=f"Screenshot: {path}", image='')
            return
        try:
            self.current_screenshot_path = path
            img = Image.open(path)
            orig_width, orig_height = img.size
            
            # Get container size
            container_width = self.screenshot_container.winfo_width()
            container_height = self.screenshot_container.winfo_height()
            
            # Use reasonable minimums if not yet rendered
            if container_width < 100:
                container_width = 800
            if container_height < 100:
                container_height = 500
            
            # Calculate scale to fit while maintaining aspect ratio
            # Leave some padding
            max_width = container_width - 20
            max_height = container_height - 20
            
            scale = min(max_width / orig_width, max_height / orig_height)
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img_resized)
            
            # Cache with size info
            self.screenshot_cache[f"{path}_{new_width}x{new_height}"] = photo
            self.screenshot_label.configure(image=photo, text='')
            self.screenshot_label.image = photo  # Keep reference
            
            if not from_resize:
                if path in self.screenshot_paths:
                    self.screenshot_idx = self.screenshot_paths.index(path)
                self.screenshot_info.set(f"{self.screenshot_idx + 1} of {len(self.screenshot_paths)}")
                # Don't auto-switch tabs - let user stay on their current tab
                # self.notebook.select(2)  # Screenshots tab
        except Exception as e:
            self.screenshot_label.configure(text=f"Error: {e}", image='')

    def _prev_screenshot(self):
        if self.screenshot_paths:
            self.screenshot_idx = max(0, self.screenshot_idx - 1)
            self._show_screenshot(self.screenshot_paths[self.screenshot_idx])

    def _next_screenshot(self):
        if self.screenshot_paths:
            self.screenshot_idx = min(len(self.screenshot_paths) - 1, self.screenshot_idx + 1)
            self._show_screenshot(self.screenshot_paths[self.screenshot_idx])

    def _show_setup_instructions(self) -> bool:
        """Show setup instructions dialog with diagram. Returns True if user confirms ready."""
        
        # For tests with block diagrams, show a custom dialog
        diagram_dir = Path.home() / "TekPTA_Diagrams"
        diagram_dir.mkdir(exist_ok=True)
        
        if self.current_suite.test_type == "afg_freq":
            # AFG Frequency Test - show block diagram
            ch = int(self.scope_channel.get())
            diagram_path = generate_afg_test_setup_diagram(diagram_dir / "afg_test_setup.png", channel=ch)
            instructions = f"""AFG FREQUENCY SWEEP TEST

Connect AFG OUTPUT (rear) → CH{ch} (front) with 50Ω BNC cable
Sweep: {self.freq_start.get()} Hz to {self.freq_stop.get()} Hz

Tolerance: ±{self.tolerance.get()}%"""
            if not diagram_path:
                # Fallback to text-only dialog if diagram generation fails
                return TekStyledDialog.askokcancel(self.root, "Test Setup Required",
                    instructions + "\n\nClick OK to begin testing.", icon='info')
            base_width, base_height = 850, 680  # Larger for new diagram
            img_max_width, img_max_height = 800, 420
            
        elif self.current_suite.test_type == "awg70002b_pulse":
            # AWG Pulse Timing Test - show block diagram
            diagram_path = generate_awg_test_setup_diagram(diagram_dir / "awg_test_setup.png")
            instructions = """AWG70002B PULSE TIMING TEST

AWG CH1+ → Scope CH1 (50Ω)
AWG CH2+ → Scope CH3 (50Ω)

Measures: Delay, Rise Time, Fall Time
Statistics: 100 samples per measurement"""
            if not diagram_path:
                # Fallback to text-only dialog if diagram generation fails
                setup_text = self.current_suite.config.get("setup_instructions", instructions)
                return TekStyledDialog.askokcancel(self.root, "Test Setup Required",
                    setup_text + "\n\nClick OK to begin testing.", icon='info')
            base_width, base_height = 1000, 780  # Larger for updated diagram
            img_max_width, img_max_height = 950, 480
        
        elif self.current_suite.test_type == "led_current":
            ch = self.scope_channel.get()
            diagram_path = generate_led_test_setup_diagram(diagram_dir / "led_test_setup.png")
            instructions = f"""LED CURRENT TEST SETUP

Circuit: SMU HI → 470Ω → LED → 10Ω shunt → SMU LO
Probe: CH{ch} across the 10Ω shunt (tip on high side)

Pass criteria: Scope within ±300 µA of SMU reading"""
            base_width, base_height = 770, 670
            img_max_width, img_max_height = 720, 400
            
        elif self.current_suite.test_type == "spectrum_scan":
            ch = self.scope_channel.get()
            start_mhz = self.spectrum_start_mhz.get()
            stop_mhz = self.spectrum_stop_mhz.get()
            diagram_path = generate_spectrum_test_setup_diagram(diagram_dir / "spectrum_test_setup.png")
            instructions = f"""SPECTRUM SCANNER SETUP

Connect antenna to CH{ch} (50Ω termination)
Scan range: {start_mhz} - {stop_mhz} MHz

Output: Top 10 peaks sorted by amplitude"""
            base_width, base_height = 770, 570
            img_max_width, img_max_height = 720, 300
            
        elif self.current_suite.test_type == "eye_diagram":
            ch = self.scope_channel.get()
            data_rate = self.eye_data_rate.get()
            num_acq = self.eye_num_acq.get()
            diagram_path = generate_eye_diagram_setup_diagram(diagram_dir)
            instructions = f"Connect DUT → SMA cable → SMA-BNC adapter → CH{ch} (50Ω)  |  Rate: {data_rate} Gbps  |  Acq: {num_acq}"
            base_width, base_height = 850, 680  # Match AFG dialog size
            img_max_width, img_max_height = 800, 420
            
        else:
            # Check if plugin has setup_instructions in config
            setup_text = self.current_suite.config.get("setup_instructions", "")
            if setup_text:
                # Show plugin's custom setup instructions using styled dialog
                return TekStyledDialog.askokcancel(
                    self.root,
                    "Test Setup Required",
                    setup_text + "\n\nClick OK to begin testing.",
                    icon='info'
                )
            # No setup instructions configured - proceed without dialog
            return True
        
        # Show dialog with diagram (common code for all diagram-based tests)
        dialog = tk.Toplevel(self.root)
        dialog.title("Test Setup Required")
        dialog.configure(bg=TekColors.BG_DARK)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        # Get screen size and cap dialog at 90% of screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        dialog_width = min(base_width, int(screen_width * 0.9))
        dialog_height = min(base_height, int(screen_height * 0.9))
        
        # Scale image constraints proportionally if dialog was shrunk
        if dialog_width < base_width:
            img_max_width = int(img_max_width * dialog_width / base_width)
        if dialog_height < base_height:
            img_max_height = int(img_max_height * dialog_height / base_height)
        
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        
        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog_width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog_height) // 2
        dialog.geometry(f"+{x}+{y}")
        
        frame = tk.Frame(dialog, bg=TekColors.BG_DARK)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Title
        tk.Label(frame, text="Setup Diagram", font=TekFonts.HEADER,
                bg=TekColors.BG_DARK, fg=TekColors.TEK_CYAN).pack(pady=(0, 5))
        
        # Diagram image - sized to fit dialog with room for text and buttons
        if diagram_path and os.path.exists(diagram_path) and PIL_AVAILABLE:
            try:
                img = Image.open(diagram_path)
                # Scale to fit within constraints
                img.thumbnail((img_max_width, img_max_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(frame, image=photo, bg=TekColors.BG_DARK)
                img_label.image = photo  # Keep reference
                img_label.pack(pady=5)
            except Exception as e:
                tk.Label(frame, text=f"Could not load diagram: {e}",
                        bg=TekColors.BG_DARK, fg=TekColors.STATUS_FAIL).pack()
        
        # Instructions text
        tk.Label(frame, text=instructions, font=TekFonts.NORMAL,
                bg=TekColors.BG_DARK, fg=TekColors.TEXT_SECONDARY,
                justify=tk.CENTER).pack(pady=10)
        
        # Result variable
        result = [False]
        
        def on_ok():
            result[0] = True
            dialog.destroy()
        
        def on_cancel():
            result[0] = False
            dialog.destroy()
        
        # Buttons
        btn_frame = tk.Frame(frame, bg=TekColors.BG_DARK)
        btn_frame.pack(pady=10)
        RoundedButton(btn_frame, "Start Test", command=on_ok, 
                     style="success", width=100, height=35).pack(side=tk.LEFT, padx=10)
        RoundedButton(btn_frame, "Cancel", command=on_cancel,
                     style="secondary", width=100, height=35).pack(side=tk.LEFT, padx=10)
        
        # Wait for dialog to close
        dialog.wait_window()
        return result[0]

    def _run_tests(self):
        if not self.current_suite:
            TekStyledDialog.showwarning(self.root, "No Suite", "Please select a test suite first.")
            return
        if not self.inst.scope:
            TekStyledDialog.showwarning(self.root, "Not Connected", "Connect to oscilloscope first.")
            return
        if self.current_suite.test_type == "led_current" and not self.inst.smu:
            # Only require SMU if not in full reference mode
            if not self.current_suite.reference_config.enabled:
                TekStyledDialog.showwarning(self.root, "SMU Not Connected", "This test requires a 2450 SMU.")
                return
        
        # Show setup instructions and wait for confirmation
        if not self._show_setup_instructions():
            return  # User cancelled
        
        # Clear persistent log for new test session
        self.persistent_scpi_log = []
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("test_results") / f"session_{ts}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "screenshots").mkdir(exist_ok=True)
        self.run_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.status_label.configure(text="Starting...")
        self._clear_results()
        for tp in self.current_engine.test_points:
            if tp.enabled:
                tp.status = TestStatus.NOT_RUN
            self._update_test_status(tp)
        # Don't auto-switch tabs - let user stay on their current tab
        # self.notebook.select(1)
        self._log("Starting test sequence...")
        
        # Reset failure pause state for new run
        self.failure_pause_event.set()  # Ensure not paused
        self.test_paused_for_failure = False
        TestFailureDialog.reset_continue_all()  # Reset "continue through all failures" flag
        if self.failure_dialog:
            self.failure_dialog.destroy()
            self.failure_dialog = None
        
        # Log reference mode status
        if self.current_suite.reference_config.enabled:
            self._log(f"Reference mode ENABLED (tests: {self.current_suite.reference_config.test_numbers})")
            # Auto-load reference waveforms to scope if not already loaded
            if not self._auto_load_references():
                self._log("WARNING: No reference waveforms loaded - test may fail")
        
        # Get channel from UI
        ch = int(self.scope_channel.get())
        
        if self.current_suite.test_type == "afg_freq":
            # Pass reference config to engine
            self.afg_engine.reference_config = self.current_suite.reference_config
            # Always use 50 ohms for AFG tests (both AFG output and CH1 termination)
            term = "50"
            amp = float(self.afg_amp.get())
            thread = threading.Thread(target=self.afg_engine.run_sequence,
                                      args=(ch, term, amp, self.output_dir / "screenshots"))
        elif self.current_suite.test_type == "led_current":
            # Pass reference config to engine
            self.led_engine.reference_config = self.current_suite.reference_config
            # Update shunt resistance before running
            self.led_engine.SHUNT_RESISTANCE = float(self.shunt_resistance.get())
            self.led_engine.TOLERANCE_UA = float(self.led_tolerance.get())
            thread = threading.Thread(target=self.led_engine.run_sequence,
                                      args=(ch, self.output_dir / "screenshots"))
        elif self.current_suite.test_type == "spectrum_scan":
            # Pass reference config to engine
            self.spectrum_engine.reference_config = self.current_suite.reference_config
            start_mhz = float(self.spectrum_start_mhz.get())
            stop_mhz = float(self.spectrum_stop_mhz.get())
            thread = threading.Thread(target=self.spectrum_engine.run_sequence,
                                      args=(ch, self.output_dir / "screenshots", start_mhz, stop_mhz))
        elif self.current_suite.test_type == "eye_diagram":
            # Pass reference config to engine
            self.eye_engine.reference_config = self.current_suite.reference_config
            # Update engine parameters from UI
            self.eye_engine.data_rate_bps = float(self.eye_data_rate.get()) * 1e9
            self.eye_engine.num_acquisitions = int(self.eye_num_acq.get())
            self.eye_engine.expected_vpp = float(self.eye_vpp.get()) / 1000  # mV to V
            self.eye_engine.expected_offset = float(self.eye_offset.get()) / 1000  # mV to V
            # Pass/Fail limits (convert from UI units)
            eh_min = self.eye_height_min.get().strip()
            eh_max = self.eye_height_max.get().strip()
            ew_min = self.eye_width_min.get().strip()
            ew_max = self.eye_width_max.get().strip()
            pl_exp = self.eye_pattern_length.get().strip()
            self.eye_engine.eye_height_min = float(eh_min) / 1000 if eh_min else None  # mV to V
            self.eye_engine.eye_height_max = float(eh_max) / 1000 if eh_max else None  # mV to V
            self.eye_engine.eye_width_min = float(ew_min) * 1e-12 if ew_min else None  # ps to s
            self.eye_engine.eye_width_max = float(ew_max) * 1e-12 if ew_max else None  # ps to s
            self.eye_engine.pattern_length_expected = int(pl_exp) if pl_exp else None  # bits
            thread = threading.Thread(target=self.eye_engine.run_sequence,
                                      args=(ch, self.output_dir / "screenshots"))
        elif self.current_suite.test_type == "agc_sample":
            # Pass reference config to engine
            self.agc_engine.reference_config = self.current_suite.reference_config
            # Update engine parameters from config
            config = self.current_suite.config
            self.agc_engine.channel_from = config.get("channel_from", 1)
            self.agc_engine.channel_to = config.get("channel_to", 3)
            self.agc_engine.expected_delay = config.get("expected_delay", 10e-6)
            self.agc_engine.delay_tolerance_pct = config.get("delay_tolerance_pct", 5.0)
            self.agc_engine.expected_rise_time = config.get("expected_rise_time", 100e-9)
            self.agc_engine.signal_high = config.get("signal_high", 2.5)
            self.agc_engine.signal_low = config.get("signal_low", 0.0)
            self.agc_engine.trigger_level = config.get("trigger_level", 1.25)
            self.agc_engine.horizontal_position = config.get("horizontal_position", 10)
            self.agc_engine.generate_test_points()
            thread = threading.Thread(target=self.agc_engine.run_sequence,
                                      args=(self.output_dir / "screenshots",))
        elif self.current_suite.test_type in self.plugin_engines:
            # Custom plugin engine - use the standard run() method from TestEngineBase
            engine = self.current_engine
            engine.output_dir = self.output_dir / "screenshots"
            engine.reference_config = self.current_suite.reference_config
            thread = threading.Thread(target=engine.run, args=(self.current_suite.config,))
        else:
            messagebox.showerror("Error", f"Unknown test type: {self.current_suite.test_type}")
            return
        thread.start()

    def _stop_tests(self):
        if self.current_engine:
            self.current_engine.should_stop = True
            self.current_engine.stop()
        # Release any failure pause so the engine thread can finish
        self.failure_pause_event.set()
        # Close any open failure dialog
        if self.failure_dialog:
            self.failure_dialog.destroy()
            self.failure_dialog = None
            self.test_paused_for_failure = False
        self._log("Stop requested...")

    def _on_done(self, passed, failed):
        # Process any remaining queued messages before saving (ensures all SCPI logs are captured)
        self._flush_message_queue()
        
        self.run_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        
        # Switch to Results tab automatically
        self.notebook.select(1)  # Results tab is index 1
        
        if failed == 0:
            self.status_label.configure(text="✓ ALL TESTS PASSED", fg=TekColors.STATUS_PASS)
            TekStyledDialog.showinfo(self.root, "Test Complete", f"All {passed} tests passed!")
        else:
            self.status_label.configure(text=f"✗ {failed} FAILED", fg=TekColors.STATUS_FAIL)
            TekStyledDialog.showwarning(self.root, "Test Complete", f"{passed} passed, {failed} failed")
        self._save_results()
        # Save SCPI log to output directory
        if self.output_dir:
            self._save_scpi_log(self.output_dir)
    
    def _flush_message_queue(self):
        """Process all remaining messages in the queue"""
        while True:
            try:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == 'log':
                    self._log(*data)
                elif msg_type == 'scpi':
                    self._log_scpi_display(*data)
                elif msg_type == 'test_start':
                    self._on_test_start(data)
                elif msg_type == 'test_complete':
                    self._on_test_complete(*data)
                elif msg_type == 'screenshot':
                    self._show_screenshot(data)
                elif msg_type == 'progress':
                    self._on_progress(data)
                # Skip 'done' messages here - we're already in _on_done
            except queue.Empty:
                break

    def _save_results(self):
        if not self.output_dir or not self.current_engine:
            return
        engine = self.current_engine
        
        # Save text report
        with open(self.output_dir / "test_report.txt", 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\nTEK PTA - PRODUCTION TEST REPORT\n" + "=" * 80 + "\n\n")
            f.write(f"Date: {datetime.datetime.now()}\nTest Suite: {self.current_suite.name}\n")
            f.write(f"Operator: {self.operator.get()}\nDUT Serial: {self.dut_serial.get()}\n\n")
            if self.inst.scope_info:
                f.write(f"Oscilloscope: {self.inst.scope_info.model} (S/N: {self.inst.scope_info.serial_number})\n")
            if self.inst.smu_info:
                f.write(f"SMU: {self.inst.smu_info.model} (S/N: {self.inst.smu_info.serial_number})\n")
            f.write("\nRESULTS\n" + "-" * 80 + "\n")
            
            for tp in engine.test_points:
                if self.current_suite.test_type == "afg_freq":
                    # Frequency test
                    f.write(f"{tp.test_id:3d}. {tp.name:30s} Meas: {tp.measured_value:15.2f} Hz "
                           f"Err: {tp.error_pct:+8.4f}%  [{tp.status.value}]\n")
                elif self.current_suite.test_type == "led_current":
                    # LED current test - show voltage, SMU current, scope current, error
                    smu_curr = tp.extra_data.get('smu_current_mA', 0)
                    scope_curr = tp.extra_data.get('scope_current_mA', 0)
                    voltage = tp.extra_data.get('voltage', tp.nominal_value)
                    error_uA = tp.extra_data.get('error_uA', 0)
                    f.write(f"{tp.test_id:3d}. V={voltage:.2f}V  SMU: {smu_curr:8.3f} mA  "
                           f"Scope: {scope_curr:8.3f} mA  Err: {error_uA:+7.1f} µA  [{tp.status.value}]\n")
            
            p = sum(1 for t in engine.test_points if t.status == TestStatus.PASS)
            fl = sum(1 for t in engine.test_points if t.status == TestStatus.FAIL)
            f.write("-" * 80 + f"\nSUMMARY: {p} PASS, {fl} FAIL\n")
        
        # Generate plots before PDF so they can be included
        if self.current_suite.test_type == "led_current":
            self._save_iv_plot()
        elif self.current_suite.test_type == "afg_freq":
            self._save_frequency_plot()
        
        # Save PDF report (includes plots)
        self._save_pdf_report()
        
        self._log(f"Results saved to: {self.output_dir}")

    def _save_pdf_report(self):
        """Generate a professional PDF test report with logo, plots, and probe info"""
        if not REPORTLAB_AVAILABLE:
            self._log("PDF generation skipped (reportlab not installed)")
            return
        
        try:
            pdf_path = self.output_dir / "test_report.pdf"
            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                                   topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                        fontSize=18, textColor=colors.HexColor('#00629B'),
                                        spaceAfter=20)
            header_style = ParagraphStyle('Header', parent=styles['Heading2'],
                                         fontSize=12, textColor=colors.HexColor('#00629B'),
                                         spaceBefore=15, spaceAfter=10)
            normal_style = styles['Normal']
            small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8)
            
            elements = []
            
            # Try to add Tektronix logo
            logo_paths = [Path("Tek_Logo_2016.png"), Path(__file__).parent / "Tek_Logo_2016.png"]
            for logo_path in logo_paths:
                if logo_path.exists():
                    try:
                        logo = RLImage(str(logo_path), width=1.5*inch, height=0.4*inch)
                        elements.append(logo)
                        elements.append(Spacer(1, 0.1*inch))
                        break
                    except Exception:
                        pass
            
            # Title
            elements.append(Paragraph("TEKTRONIX PRODUCTION TEST REPORT", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Test info table
            info_data = [
                ['Date:', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['Test Suite:', self.current_suite.name if self.current_suite else 'N/A'],
                ['Operator:', self.operator.get() or 'N/A'],
                ['DUT Serial:', self.dut_serial.get() or 'N/A'],
            ]
            if self.inst.scope_info:
                info_data.append(['Oscilloscope:', f"{self.inst.scope_info.model} (S/N: {self.inst.scope_info.serial_number})"])
            if self.inst.smu_info:
                info_data.append(['SMU:', f"{self.inst.smu_info.model} (S/N: {self.inst.smu_info.serial_number})"])
            
            info_table = Table(info_data, colWidths=[1.5*inch, 5*inch])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(info_table)
            
            # Probe information section
            if self.inst.scope:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph("PROBE CONFIGURATION", header_style))
                probe_data = [['Channel', 'Probe Type', 'Serial Number']]
                for ch in range(1, 9):  # Support up to 8 channels
                    probe_info = self.inst.get_probe_info(ch)
                    if probe_info["connected"]:
                        probe_data.append([
                            f"CH{ch}",
                            probe_info["type"] or "Unknown",
                            probe_info["serial"] or "N/A"
                        ])
                
                if len(probe_data) > 1:  # Has probe data
                    probe_table = Table(probe_data, colWidths=[1*inch, 2.5*inch, 2*inch])
                    probe_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00629B')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ]))
                    elements.append(probe_table)
                else:
                    elements.append(Paragraph("No probes detected", normal_style))
            
            elements.append(Spacer(1, 0.3*inch))
            
            # Results header
            elements.append(Paragraph("TEST RESULTS", header_style))
            
            # Results table
            engine = self.current_engine
            if engine and engine.test_points:
                if self.current_suite.test_type == "afg_freq":
                    # Frequency test results
                    result_data = [['#', 'Test Point', 'Nominal', 'Measured', 'Error', 'Status']]
                    for tp in engine.test_points:
                        if tp.nominal_value >= 1e6:
                            nom = f"{tp.nominal_value/1e6:.3f} MHz"
                            meas = f"{tp.measured_value/1e6:.6f} MHz" if tp.measured_value else "---"
                        elif tp.nominal_value >= 1e3:
                            nom = f"{tp.nominal_value/1e3:.3f} kHz"
                            meas = f"{tp.measured_value/1e3:.6f} kHz" if tp.measured_value else "---"
                        else:
                            nom = f"{tp.nominal_value:.1f} Hz"
                            meas = f"{tp.measured_value:.3f} Hz" if tp.measured_value else "---"
                        err = f"{tp.error_pct:+.4f}%" if tp.measured_value else "---"
                        result_data.append([str(tp.test_id), tp.name, nom, meas, err, tp.status.value])
                elif self.current_suite.test_type == "led_current":
                    # LED current test results - extra precision on voltage
                    result_data = [['#', 'Voltage', 'SMU Current', 'Scope Current', 'Error (µA)', 'Status']]
                    for tp in engine.test_points:
                        voltage = tp.extra_data.get('voltage', tp.nominal_value)
                        smu_curr = tp.extra_data.get('smu_current_mA', 0)
                        scope_curr = tp.extra_data.get('scope_current_mA', 0)
                        error_uA = tp.extra_data.get('error_uA', 0)
                        result_data.append([
                            str(tp.test_id), 
                            f"{voltage:.2f} V",  # Extra precision
                            f"{smu_curr:.3f} mA",
                            f"{scope_curr:.3f} mA",
                            f"{error_uA:+.1f}",
                            tp.status.value
                        ])
                elif self.current_suite.test_type == "spectrum_scan":
                    # Spectrum scan results - show top peaks
                    result_data = [['#', 'Frequency', 'Amplitude', 'Band']]
                    peaks = []
                    for tp in engine.test_points:
                        peaks = tp.extra_data.get('peaks', [])
                        break
                    for i, peak in enumerate(peaks[:10], 1):
                        result_data.append([
                            str(i),
                            peak.format_frequency(),
                            f"{peak.amplitude_dbm:.1f} dBm",
                            peak.band_name
                        ])
                elif self.current_suite.test_type in ("agc_sample", "awg70002b_pulse"):
                    # AGC Sample / AWG Pulse Timing - timing measurements with SI units and limits
                    result_data = [['#', 'Test Name', 'Nominal', 'Lower Limit', 'Upper Limit', 'Measured', 'Status']]
                    for tp in engine.test_points:
                        nom = format_si(tp.nominal_value, "s")
                        meas = format_si(tp.measured_value, "s") if tp.measured_value else "---"
                        low = format_si(tp.lower_limit, "s") if tp.has_limits else "---"
                        high = format_si(tp.upper_limit, "s") if tp.has_limits else "---"
                        result_data.append([str(tp.test_id), tp.name, nom, low, high, meas, tp.status.value])
                elif self.current_suite.test_type == "eye_diagram":
                    # Eye diagram - extract measurements from extra_data
                    result_data = [['Parameter', 'Lower Limit', 'Mean', 'Upper Limit', 'Min', 'Max', 'Status']]
                    
                    # Get the single test point with all the extra_data
                    if engine.test_points:
                        tp = engine.test_points[0]
                        ed = tp.extra_data
                        
                        # Eye Height
                        eh = ed.get('eye_height', {})
                        eh_limits = ed.get('eye_height_limits', {})
                        if eh:
                            eh_mean = eh.get('mean', 0)
                            eh_min_val = eh.get('min', 0)
                            eh_max_val = eh.get('max', 0)
                            eh_low = eh_limits.get('min')
                            eh_high = eh_limits.get('max')
                            eh_status = "PASS"
                            if eh_low and eh_mean < eh_low:
                                eh_status = "FAIL"
                            if eh_high and eh_mean > eh_high:
                                eh_status = "FAIL"
                            if eh_low is None and eh_high is None:
                                eh_status = "Info"
                            result_data.append([
                                "Eye Height",
                                f"{eh_low*1000:.1f} mV" if eh_low else "---",
                                f"{eh_mean*1000:.2f} mV",
                                f"{eh_high*1000:.1f} mV" if eh_high else "---",
                                f"{eh_min_val*1000:.2f} mV",
                                f"{eh_max_val*1000:.2f} mV",
                                eh_status
                            ])
                        
                        # Eye Width
                        ew = ed.get('eye_width', {})
                        ew_limits = ed.get('eye_width_limits', {})
                        ui_pct = ed.get('eye_width_ui_pct', 0)
                        if ew:
                            ew_mean = ew.get('mean', 0)
                            ew_min_val = ew.get('min', 0)
                            ew_max_val = ew.get('max', 0)
                            ew_low = ew_limits.get('min')
                            ew_high = ew_limits.get('max')
                            ew_status = "PASS"
                            if ew_low and ew_mean < ew_low:
                                ew_status = "FAIL"
                            if ew_high and ew_mean > ew_high:
                                ew_status = "FAIL"
                            if ew_low is None and ew_high is None:
                                ew_status = "Info"
                            ui_str = f" ({ui_pct:.1f}%UI)" if ui_pct else ""
                            result_data.append([
                                "Eye Width",
                                f"{ew_low*1e12:.1f} ps" if ew_low else "---",
                                f"{ew_mean*1e12:.2f} ps{ui_str}",
                                f"{ew_high*1e12:.1f} ps" if ew_high else "---",
                                f"{ew_min_val*1e12:.2f} ps",
                                f"{ew_max_val*1e12:.2f} ps",
                                ew_status
                            ])
                        
                        # Pattern Length
                        pl = ed.get('pattern_length', {})
                        pl_expected = ed.get('pattern_length_expected')
                        if pl:
                            pl_val = pl.get('value', 0)
                            pl_status = "Info"
                            if pl_expected:
                                pl_status = "PASS" if pl_val == pl_expected else "FAIL"
                            result_data.append([
                                "Pattern Length",
                                f"{pl_expected} bits" if pl_expected else "---",
                                f"{pl_val} bits",
                                f"{pl_expected} bits" if pl_expected else "---",
                                "---", "---",
                                pl_status
                            ])
                        
                        # Data Rate (measured)
                        dr = ed.get('data_rate_measured', {})
                        expected_dr = ed.get('data_rate_bps', 0)
                        if dr:
                            dr_mean = dr.get('mean', 0)
                            dr_min_val = dr.get('min', 0)
                            dr_max_val = dr.get('max', 0)
                            dr_status = "Info"
                            if expected_dr and dr_mean:
                                dr_error = abs(dr_mean - expected_dr) / expected_dr * 100
                                dr_status = "PASS" if dr_error < 1.0 else "Info"
                            result_data.append([
                                "Data Rate",
                                f"{expected_dr/1e9:.3f} Gbps" if expected_dr else "---",
                                f"{dr_mean/1e9:.6f} Gbps",
                                f"{expected_dr/1e9:.3f} Gbps" if expected_dr else "---",
                                f"{dr_min_val/1e9:.6f} Gbps",
                                f"{dr_max_val/1e9:.6f} Gbps",
                                dr_status
                            ])
                        
                        # Deterministic Jitter (DJ)
                        dj = ed.get('dj', {})
                        if dj:
                            dj_mean = dj.get('mean', 0)
                            dj_min_val = dj.get('min', 0)
                            dj_max_val = dj.get('max', 0)
                            result_data.append([
                                "DJ (Det. Jitter)",
                                "---",
                                f"{dj_mean*1e12:.2f} ps",
                                "---",
                                f"{dj_min_val*1e12:.2f} ps",
                                f"{dj_max_val*1e12:.2f} ps",
                                "Info"
                            ])
                        
                        # Info row
                        pll = ed.get('selected_pll', 'N/A')
                        ref_mode = ed.get('reference_mode', False)
                        num_acq = ed.get('num_acquisitions', 1)
                        acq_str = "REF" if ref_mode else str(num_acq)
                        result_data.append([
                            f"PLL: {pll}", f"Acq: {acq_str}", "", "", "", "", ""
                        ])
                else:
                    # Default format: #, Test Name, Nominal, Lower Limit, Upper Limit, Measured, Status
                    result_data = [['#', 'Test Name', 'Nominal', 'Lower Limit', 'Upper Limit', 'Measured', 'Status']]
                    for tp in engine.test_points:
                        # Format values based on unit type
                        if tp.unit == "Hz":
                            nom = format_si(tp.nominal_value, "Hz")
                            meas = format_si(tp.measured_value, "Hz") if tp.measured_value else "---"
                            low = format_si(tp.lower_limit, "Hz") if tp.has_limits else "---"
                            high = format_si(tp.upper_limit, "Hz") if tp.has_limits else "---"
                        elif tp.unit in ("s", "sec", "seconds"):
                            nom = format_si(tp.nominal_value, "s")
                            meas = format_si(tp.measured_value, "s") if tp.measured_value else "---"
                            low = format_si(tp.lower_limit, "s") if tp.has_limits else "---"
                            high = format_si(tp.upper_limit, "s") if tp.has_limits else "---"
                        elif tp.unit in ("V", "A", "W", "Ohm", "F", "H"):
                            nom = format_si(tp.nominal_value, tp.unit)
                            meas = format_si(tp.measured_value, tp.unit) if tp.measured_value else "---"
                            low = format_si(tp.lower_limit, tp.unit) if tp.has_limits else "---"
                            high = format_si(tp.upper_limit, tp.unit) if tp.has_limits else "---"
                        elif tp.unit in ("Mbps", "bps", "bits"):
                            nom = f"{tp.nominal_value:.3f} {tp.unit}"
                            meas = f"{tp.measured_value:.3f} {tp.unit}" if tp.measured_value else "---"
                            low = f"{tp.lower_limit:.3f} {tp.unit}" if tp.has_limits else "---"
                            high = f"{tp.upper_limit:.3f} {tp.unit}" if tp.has_limits else "---"
                        else:
                            nom = format_si(tp.nominal_value, tp.unit) if tp.unit else f"{tp.nominal_value:.6g}"
                            meas = format_si(tp.measured_value, tp.unit) if tp.measured_value else "---"
                            low = format_si(tp.lower_limit, tp.unit) if tp.has_limits else "---"
                            high = format_si(tp.upper_limit, tp.unit) if tp.has_limits else "---"
                        result_data.append([str(tp.test_id), tp.name, nom, low, high, meas, tp.status.value])
                
                result_table = Table(result_data, repeatRows=1)
                result_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00629B')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                # Color code pass/fail rows
                if self.current_suite.test_type == "eye_diagram":
                    # For eye_diagram, color based on Status column in result_data
                    for i, row in enumerate(result_data[1:], start=1):  # Skip header
                        status = row[-1] if row[-1] else ""
                        if status == "PASS":
                            result_table.setStyle(TableStyle([
                                ('BACKGROUND', (-1, i), (-1, i), colors.HexColor('#d4edda')),
                            ]))
                        elif status == "FAIL":
                            result_table.setStyle(TableStyle([
                                ('BACKGROUND', (-1, i), (-1, i), colors.HexColor('#f8d7da')),
                            ]))
                else:
                    # For other tests, iterate over test_points
                    for i, tp in enumerate(engine.test_points, start=1):
                        if tp.status.value == "PASS":
                            result_table.setStyle(TableStyle([
                                ('BACKGROUND', (-1, i), (-1, i), colors.HexColor('#d4edda')),
                            ]))
                        elif tp.status.value == "FAIL":
                            result_table.setStyle(TableStyle([
                                ('BACKGROUND', (-1, i), (-1, i), colors.HexColor('#f8d7da')),
                            ]))
                
                elements.append(result_table)
            
            # Summary - compare by value since plugin may use different TestStatus enum
            elements.append(Spacer(1, 0.3*inch))
            if self.current_suite.test_type == "eye_diagram":
                # For eye_diagram, count from result_data rows
                p = sum(1 for row in result_data[1:] if row[-1] == "PASS")
                fl = sum(1 for row in result_data[1:] if row[-1] == "FAIL")
            else:
                p = sum(1 for t in engine.test_points if t.status.value == "PASS")
                fl = sum(1 for t in engine.test_points if t.status.value == "FAIL")
            summary_text = f"<b>SUMMARY:</b> {p} PASS, {fl} FAIL"
            if fl == 0:
                summary_text += " - <font color='green'>ALL TESTS PASSED</font>"
            else:
                summary_text += f" - <font color='red'>{fl} TESTS FAILED</font>"
            elements.append(Paragraph(summary_text, normal_style))
            
            # SCPI Log reference
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph(
                f"<i>Complete SCPI command log saved to: scpi_log.txt</i>", small_style))
            
            # Add I-V or frequency plot if available
            if self.current_suite.test_type == "led_current":
                plot_path = self.output_dir / "iv_characteristic.png"
                if plot_path.exists():
                    elements.append(PageBreak())
                    elements.append(Paragraph("I-V CHARACTERISTIC PLOT", header_style))
                    try:
                        plot_img = RLImage(str(plot_path), width=6*inch, height=4*inch)
                        elements.append(plot_img)
                    except Exception:
                        pass
            elif self.current_suite.test_type == "afg_freq":
                plot_path = self.output_dir / "frequency_response.png"
                if plot_path.exists():
                    elements.append(PageBreak())
                    elements.append(Paragraph("FREQUENCY RESPONSE PLOT", header_style))
                    try:
                        plot_img = RLImage(str(plot_path), width=6*inch, height=4*inch)
                        elements.append(plot_img)
                    except Exception:
                        pass
            
            # Screenshots section
            if self.screenshot_paths:
                elements.append(PageBreak())
                elements.append(Paragraph("SCREENSHOTS", header_style))
                
                for i, path in enumerate(self.screenshot_paths):
                    if os.path.exists(path) and "characteristic" not in path and "frequency_response" not in path:
                        try:
                            # Add screenshot image (scaled to fit page)
                            img = RLImage(path, width=7*inch, height=4.5*inch)
                            elements.append(img)
                            elements.append(Paragraph(f"Test {i+1}: {os.path.basename(path)}", normal_style))
                            elements.append(Spacer(1, 0.2*inch))
                        except Exception:
                            pass
            
            # Build PDF
            doc.build(elements)
            self._log(f"PDF report saved: {pdf_path.name}")
            
        except Exception as e:
            self._log(f"PDF generation error: {e}")

    def _save_iv_plot(self):
        """Generate I-V characteristic plot for LED current test"""
        if not MATPLOTLIB_AVAILABLE:
            self._log("I-V plot skipped (matplotlib not installed)")
            return
        
        try:
            engine = self.current_engine
            if not engine or not engine.test_points:
                self._log("I-V plot skipped (no test points)")
                return
            
            # Extract data
            voltages = []
            smu_currents = []
            scope_currents = []
            
            for tp in engine.test_points:
                v = tp.extra_data.get('voltage', tp.nominal_value)
                smu_i = tp.extra_data.get('smu_current_mA', 0)
                scope_i = tp.extra_data.get('scope_current_mA', 0)
                voltages.append(v)
                smu_currents.append(smu_i)
                scope_currents.append(scope_i)
            
            # Check if we have valid data
            if not voltages or all(v == 0 for v in smu_currents):
                self._log("I-V plot skipped (no valid current data)")
                return
            
            self._log(f"Generating I-V plot with {len(voltages)} points...")
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot both curves
            ax.plot(voltages, smu_currents, 'b-o', linewidth=2, markersize=8, 
                   label='SMU Measurement', color='#00629B')
            ax.plot(voltages, scope_currents, 'g-s', linewidth=2, markersize=8,
                   label='Scope Measurement', color='#00A3E0')
            
            # Styling
            ax.set_xlabel('Voltage (V)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Current (mA)', fontsize=12, fontweight='bold')
            ax.set_title('LED I-V Characteristic\nSMU vs Oscilloscope Current Measurement', 
                        fontsize=14, fontweight='bold', color='#00629B')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left', fontsize=10)
            
            # Add tolerance band info
            tolerance_uA = LEDCurrentTestEngine.TOLERANCE_UA
            ax.text(0.98, 0.02, f'Pass criteria: ±{tolerance_uA} µA agreement', 
                   transform=ax.transAxes, ha='right', va='bottom',
                   fontsize=9, style='italic', color='gray')
            
            # Set axis limits with some padding
            ax.set_xlim(min(voltages) - 0.2, max(voltages) + 0.2)
            y_max = max(max(smu_currents), max(scope_currents)) * 1.1
            ax.set_ylim(0, y_max)
            
            # Tight layout and save
            plt.tight_layout()
            plot_path = self.output_dir / "iv_characteristic.png"
            plt.savefig(plot_path, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close(fig)
            
            self._log(f"I-V plot saved: {plot_path.name}")
            
            # Add to screenshots for viewing
            self.screenshot_paths.append(str(plot_path))
            self._update_screenshot_list()
            
        except Exception as e:
            self._log(f"I-V plot error: {e}")

    def _save_frequency_plot(self):
        """Generate frequency response plot for AFG test"""
        if not MATPLOTLIB_AVAILABLE:
            self._log("Frequency plot skipped (matplotlib not installed)")
            return
        
        try:
            engine = self.current_engine
            if not engine or not engine.test_points:
                return
            
            # Extract data
            nominal_freqs = []
            measured_freqs = []
            errors = []
            
            for tp in engine.test_points:
                if tp.measured_value > 0:
                    nominal_freqs.append(tp.nominal_value)
                    measured_freqs.append(tp.measured_value)
                    errors.append(tp.error_pct)
            
            if not nominal_freqs:
                return
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
            
            # Plot 1: Nominal vs Measured frequency (log scale)
            ax1.loglog(nominal_freqs, measured_freqs, 'b-o', linewidth=2, markersize=6, 
                      label='Measured', color='#00629B')
            ax1.loglog(nominal_freqs, nominal_freqs, 'r--', linewidth=1, 
                      label='Ideal (1:1)', color='gray', alpha=0.7)
            
            ax1.set_xlabel('Input Frequency (Hz)', fontsize=11, fontweight='bold')
            ax1.set_ylabel('Measured Frequency (Hz)', fontsize=11, fontweight='bold')
            ax1.set_title('Frequency Response: Input vs Output', 
                         fontsize=12, fontweight='bold', color='#00629B')
            ax1.grid(True, alpha=0.3, which='both')
            ax1.legend(loc='upper left', fontsize=9)
            
            # Plot 2: Error vs Frequency
            ax2.semilogx(nominal_freqs, errors, 'g-s', linewidth=2, markersize=6, 
                        color='#00A3E0')
            ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
            
            # Add tolerance band
            tolerance = engine.test_points[0].tolerance_pct if engine.test_points else 0.2
            ax2.axhline(y=tolerance, color='red', linestyle=':', linewidth=1, alpha=0.5)
            ax2.axhline(y=-tolerance, color='red', linestyle=':', linewidth=1, alpha=0.5)
            ax2.fill_between(nominal_freqs, -tolerance, tolerance, alpha=0.1, color='green')
            
            ax2.set_xlabel('Input Frequency (Hz)', fontsize=11, fontweight='bold')
            ax2.set_ylabel('Error (%)', fontsize=11, fontweight='bold')
            ax2.set_title(f'Frequency Error (Pass band: ±{tolerance}%)', 
                         fontsize=12, fontweight='bold', color='#00629B')
            ax2.grid(True, alpha=0.3, which='both')
            
            # Tight layout and save
            plt.tight_layout()
            plot_path = self.output_dir / "frequency_response.png"
            plt.savefig(plot_path, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close(fig)
            
            self._log(f"Frequency response plot saved: {plot_path.name}")
            
            # Add to screenshots for viewing
            self.screenshot_paths.append(str(plot_path))
            self._update_screenshot_list()
            
        except Exception as e:
            self._log(f"Frequency plot error: {e}")

    def run(self):
        self.root.after(500, self._refresh_instruments)
        self.root.mainloop()


# =============================================================================
# FUTURE FEATURES / ROADMAP (Placeholders for future development)
# =============================================================================
#
# The following features are commonly requested and could be added:
#
# 1. CUSTOM OUTPUT LOCATION
#    - Allow user to specify where test results are saved
#    - Add file dialog to choose output directory
#    - Store preference in config file
#
# 2. CUSTOM REPORT NAMING
#    - Allow user to name the test results folder
#    - Allow user to customize PDF report filename
#    - Include DUT serial number in filename automatically
#
# 3. CUSTOM INSTRUMENT SUPPORT
#    - Allow users to provide SCPI command sets for other instruments
#    - Generic instrument driver with user-defined commands
#    - Import/export instrument profiles (JSON format)
#    - See: InstrumentManager.add_manual() for connection pattern
#
# 4. JITTER AND EYE DIAGRAM TESTS
#    - Use TIE (Time Interval Error) measurements
#    - DPOJET analysis for jitter components (RJ, DJ, TJ@BER)
#    - Eye height, eye width measurements
#    - Requires: pattern generator or real serial data source
#    - Key commands: MEASUrement:MEAS<x>:TYPe TIE, HEIGHT, WIDTH
#
# 5. MULTI-STAGE TESTS WITH SETUP PROMPTS
#    - Tests requiring configuration changes between sub-tests
#    - Multiple setup dialogs with user-provided connection diagrams
#    - Support for user-uploaded schematic images (PNG/JPG)
#    - State machine for test sequencing with pauses
#
# 6. USER-PROVIDED SETUP DIAGRAMS
#    - Allow users to upload their own connection diagrams
#    - Store diagrams with test suite definitions
#    - Support PNG, JPG, SVG formats
#
# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    if not PYVISA_AVAILABLE:
        print("\n" + "=" * 60)
        print("MISSING: pip install pyvisa pyvisa-py Pillow reportlab")
        print("=" * 60 + "\n")
    app = TektronixProductionTestApp()
    app.run()


if __name__ == "__main__":
    main()
