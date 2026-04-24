#!/usr/bin/env python3
"""
Tek PTA v1.1.1 Upgrade Module
==============================

New components for Tek PTA v1.1.1. These classes and functions are designed
to be integrated into tek_pta.py. Each section is self-contained with clear
integration points noted.

Components:
1. SplashScreen - Launch disclaimer dialog
2. SuiteSelector - Multi-select suite chooser with favorites
3. ChannelSourceSelector - Unified CH + REF waveform source picker
4. RunQueueManager - Sequential multi-suite execution with progress
5. HelpViewer - Read-only document viewer window
6. FavoritesManager - Persist favorites and last-used suites

Integration: Search for "# INTEGRATION:" comments for where each piece
connects to the existing tek_pta.py codebase.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path


# =============================================================================
# VERSION - Single source of truth (update __version__ in tek_pta.py to match)
# =============================================================================
__version__ = "1.1.1"


# =============================================================================
# 1. SPLASH SCREEN
# =============================================================================
# INTEGRATION: Call SplashScreen.show() BEFORE creating the main TekPTA window.
# In tek_pta.py main block, replace:
#     root = tk.Tk()
# With:
#     splash_root = tk.Tk()
#     splash_root.withdraw()
#     if not SplashScreen.show(splash_root):
#         splash_root.destroy()
#         sys.exit(0)
#     splash_root.destroy()
#     root = tk.Tk()
# =============================================================================

class SplashScreen:
    """Modal splash screen with internal-use disclaimer."""
    
    # Disclaimer text - reads version from __version__ automatically
    DISCLAIMER = (
        "Tek PTA v{version} is a prototype development from Tektronix that is "
        "not publicly available. If you do not work for Tektronix and a Tektronix "
        "employee has given you access to this, it is for internal use only.\n\n"
        "By clicking OK you acknowledge that you understand that and you will not "
        "share outside of the immediate organization any details about this software."
    )
    
    @classmethod
    def show(cls, parent, version: str = None) -> bool:
        """
        Show the splash/disclaimer dialog.
        
        Args:
            parent: Parent tk window (can be withdrawn)
            version: Version string. If None, uses module __version__
            
        Returns:
            True if user clicked OK, False if user clicked Close
        """
        if version is None:
            # Pull from tek_pta.__version__ if available, else this module
            try:
                import tek_pta
                version = tek_pta.__version__
            except (ImportError, AttributeError):
                version = __version__
        
        result = [False]  # Mutable container for closure
        
        dialog = tk.Toplevel(parent)
        dialog.title("Tek PTA")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: _close(False))
        
        # Colors matching Tek PTA theme
        BG = "#1B2838"
        FG = "#E0E0E0"
        ACCENT = "#0098DB"  # Tektronix blue
        BORDER = "#4A6278"
        BUTTON_BG = "#2A3F54"
        
        dialog.configure(bg=BG)
        
        # Main frame with border
        outer = tk.Frame(dialog, bg=BORDER, padx=2, pady=2)
        outer.pack(padx=20, pady=20)
        
        inner = tk.Frame(outer, bg=BG, padx=30, pady=20)
        inner.pack()
        
        # Tektronix logo area / Title
        title_frame = tk.Frame(inner, bg=BG)
        title_frame.pack(pady=(10, 5))
        
        tk.Label(
            title_frame, text="Tek PTA", font=("Segoe UI", 28, "bold"),
            fg=ACCENT, bg=BG
        ).pack()
        
        tk.Label(
            title_frame, text="Production Test Assistant",
            font=("Segoe UI", 12), fg="#8899AA", bg=BG
        ).pack()
        
        tk.Label(
            title_frame, text=f"Version {version}",
            font=("Segoe UI", 10), fg="#667788", bg=BG
        ).pack(pady=(2, 0))
        
        # Separator
        ttk.Separator(inner, orient="horizontal").pack(fill="x", pady=15)
        
        # Disclaimer text
        disclaimer_text = cls.DISCLAIMER.format(version=version)
        
        text_frame = tk.Frame(inner, bg=BG)
        text_frame.pack(fill="both", padx=10)
        
        disclaimer_label = tk.Label(
            text_frame, text=disclaimer_text,
            font=("Segoe UI", 10), fg=FG, bg=BG,
            wraplength=450, justify="left", anchor="w"
        )
        disclaimer_label.pack(pady=10)
        
        # Separator
        ttk.Separator(inner, orient="horizontal").pack(fill="x", pady=10)
        
        # Button frame
        btn_frame = tk.Frame(inner, bg=BG)
        btn_frame.pack(pady=(5, 10))
        
        def _close(accepted):
            result[0] = accepted
            if accepted:
                # Log acknowledgment
                cls._log_acknowledgment(version)
            dialog.destroy()
        
        # Style the buttons
        ok_btn = tk.Button(
            btn_frame, text="  OK  ", font=("Segoe UI", 11, "bold"),
            fg="white", bg=ACCENT, activebackground="#007AB8",
            activeforeground="white", relief="flat", padx=20, pady=6,
            cursor="hand2", command=lambda: _close(True)
        )
        ok_btn.pack(side="left", padx=(0, 15))
        
        close_btn = tk.Button(
            btn_frame, text="  Close  ", font=("Segoe UI", 11),
            fg=FG, bg=BUTTON_BG, activebackground="#3A5068",
            activeforeground=FG, relief="flat", padx=20, pady=6,
            cursor="hand2", command=lambda: _close(False)
        )
        close_btn.pack(side="left")
        
        # Center on screen
        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Focus OK button
        ok_btn.focus_set()
        dialog.bind("<Return>", lambda e: _close(True))
        dialog.bind("<Escape>", lambda e: _close(False))
        
        parent.wait_window(dialog)
        return result[0]
    
    @staticmethod
    def _log_acknowledgment(version: str):
        """Log that the user acknowledged the disclaimer."""
        config_path = _get_config_path()
        config = _load_config(config_path)
        
        if "acknowledgments" not in config:
            config["acknowledgments"] = []
        
        config["acknowledgments"].append({
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "user": os.getenv("USERNAME", os.getenv("USER", "unknown"))
        })
        
        _save_config(config_path, config)


# =============================================================================
# 2. SUITE SELECTOR - Multi-select with checkboxes, description column, favorites
# =============================================================================
# INTEGRATION: Replace the existing suite selection radio-button panel in
# tek_pta.py's create_suite_selection() or equivalent method with this widget.
# =============================================================================

class SuiteSelector(tk.Frame):
    """
    Multi-select test suite selector with:
    - Checkbox column (larger checkboxes via custom rendering)
    - Suite name column
    - Description column  
    - Favorites star toggle
    - Sort options: Favorites first, Last used, Alphabetical
    """
    
    # Colors matching Tek PTA theme
    BG = "#1B2838"
    FG = "#E0E0E0"
    ACCENT = "#0098DB"
    ROW_BG = "#1E3044"
    ROW_ALT = "#22364A"
    SELECTED_BG = "#2A4A64"
    BORDER = "#4A6278"
    STAR_ON = "#FFD700"
    STAR_OFF = "#555555"
    
    def __init__(self, parent, suites: list, favorites_mgr=None, **kwargs):
        """
        Args:
            parent: Parent widget
            suites: List of suite objects with .name, .description attributes
                    (TestSuitePlugin instances)
            favorites_mgr: FavoritesManager instance for persistence
        """
        super().__init__(parent, bg=self.BG, **kwargs)
        
        self.suites = suites
        self.favorites_mgr = favorites_mgr or FavoritesManager()
        self.check_vars = {}  # suite_name -> BooleanVar
        self.suite_map = {}   # suite_name -> suite object
        self._sort_mode = tk.StringVar(value="favorites")
        
        self._build_ui()
        self._populate()
    
    def _build_ui(self):
        """Build the selector UI."""
        # Top bar with sort controls
        top_frame = tk.Frame(self, bg=self.BG)
        top_frame.pack(fill="x", padx=5, pady=(5, 2))
        
        tk.Label(
            top_frame, text="Test Suites", font=("Segoe UI", 11, "bold"),
            fg=self.ACCENT, bg=self.BG
        ).pack(side="left")
        
        # Sort dropdown
        sort_frame = tk.Frame(top_frame, bg=self.BG)
        sort_frame.pack(side="right")
        
        tk.Label(
            sort_frame, text="Sort:", font=("Segoe UI", 9),
            fg="#8899AA", bg=self.BG
        ).pack(side="left", padx=(0, 5))
        
        sort_combo = ttk.Combobox(
            sort_frame, textvariable=self._sort_mode, width=14,
            values=["favorites", "last used", "alphabetical"],
            state="readonly"
        )
        sort_combo.pack(side="left")
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._populate())
        
        # Select all / none buttons
        btn_frame = tk.Frame(top_frame, bg=self.BG)
        btn_frame.pack(side="right", padx=(0, 15))
        
        tk.Button(
            btn_frame, text="All", font=("Segoe UI", 8),
            fg=self.FG, bg="#2A3F54", relief="flat", padx=6, pady=1,
            command=self._select_all
        ).pack(side="left", padx=2)
        
        tk.Button(
            btn_frame, text="None", font=("Segoe UI", 8),
            fg=self.FG, bg="#2A3F54", relief="flat", padx=6, pady=1,
            command=self._select_none
        ).pack(side="left", padx=2)
        
        # Scrollable suite list frame
        list_container = tk.Frame(self, bg=self.BORDER, padx=1, pady=1)
        list_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Canvas + scrollbar for scrolling
        self._canvas = tk.Canvas(list_container, bg=self.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical",
                                   command=self._canvas.yview)
        self._list_frame = tk.Frame(self._canvas, bg=self.BG)
        
        self._list_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw"
        )
        self._canvas.configure(yscrollcommand=scrollbar.set)
        
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind canvas resize to stretch list frame
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        
        # Mouse wheel scrolling
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 * (e.delta // 120), "units"))
    
    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)
    
    def _populate(self):
        """Populate the list with suite rows."""
        # Clear existing
        for widget in self._list_frame.winfo_children():
            widget.destroy()
        
        # Sort suites
        sorted_suites = self._sort_suites(self.suites)
        
        for i, suite in enumerate(sorted_suites):
            name = suite.name
            desc = getattr(suite, 'description', '')
            
            # Create check var if not exists
            if name not in self.check_vars:
                self.check_vars[name] = tk.BooleanVar(value=False)
            self.suite_map[name] = suite
            
            row_bg = self.ROW_BG if i % 2 == 0 else self.ROW_ALT
            
            row = tk.Frame(self._list_frame, bg=row_bg, padx=8, pady=6)
            row.pack(fill="x", padx=2, pady=1)
            row.columnconfigure(1, weight=0)  # name
            row.columnconfigure(2, weight=1)  # description
            
            # Favorite star
            is_fav = self.favorites_mgr.is_favorite(name)
            star_label = tk.Label(
                row, text="★" if is_fav else "☆",
                font=("Segoe UI", 14),
                fg=self.STAR_ON if is_fav else self.STAR_OFF,
                bg=row_bg, cursor="hand2"
            )
            star_label.pack(side="left", padx=(0, 6))
            star_label.bind("<Button-1>",
                lambda e, n=name, lbl=star_label: self._toggle_favorite(n, lbl))
            
            # Checkbox (larger, themed)
            cb = tk.Checkbutton(
                row, variable=self.check_vars[name],
                bg=row_bg, activebackground=row_bg,
                selectcolor="#2A4A64", indicatoron=True,
                font=("Segoe UI", 12)
            )
            cb.pack(side="left", padx=(0, 8))
            
            # Suite name
            name_label = tk.Label(
                row, text=name, font=("Segoe UI", 10, "bold"),
                fg=self.FG, bg=row_bg, anchor="w", width=28
            )
            name_label.pack(side="left", padx=(0, 10))
            
            # Description (separate column, truncated)
            desc_text = desc if len(desc) < 60 else desc[:57] + "..."
            desc_label = tk.Label(
                row, text=desc_text, font=("Segoe UI", 9),
                fg="#8899AA", bg=row_bg, anchor="w"
            )
            desc_label.pack(side="left", fill="x", expand=True)
            
            # Make entire row clickable to toggle checkbox
            for widget in [row, name_label, desc_label]:
                widget.bind("<Button-1>",
                    lambda e, var=self.check_vars[name]: var.set(not var.get()))
    
    def _sort_suites(self, suites):
        """Sort suites based on current sort mode."""
        mode = self._sort_mode.get()
        
        if mode == "favorites":
            return sorted(suites, key=lambda s: (
                0 if self.favorites_mgr.is_favorite(s.name) else 1,
                s.name.lower()
            ))
        elif mode == "last used":
            return sorted(suites, key=lambda s: (
                self.favorites_mgr.get_last_used_rank(s.name),
                s.name.lower()
            ))
        else:  # alphabetical
            return sorted(suites, key=lambda s: s.name.lower())
    
    def _toggle_favorite(self, suite_name: str, label: tk.Label):
        """Toggle favorite status for a suite."""
        is_fav = self.favorites_mgr.toggle_favorite(suite_name)
        label.configure(
            text="★" if is_fav else "☆",
            fg=self.STAR_ON if is_fav else self.STAR_OFF
        )
        # Re-sort if in favorites mode
        if self._sort_mode.get() == "favorites":
            self._populate()
    
    def _select_all(self):
        for var in self.check_vars.values():
            var.set(True)
    
    def _select_none(self):
        for var in self.check_vars.values():
            var.set(False)
    
    def get_selected_suites(self) -> list:
        """Return list of selected suite objects in display order."""
        selected = []
        for name, var in self.check_vars.items():
            if var.get():
                selected.append(self.suite_map[name])
        
        # Record usage
        for suite in selected:
            self.favorites_mgr.record_usage(suite.name)
        
        return selected
    
    def get_selected_names(self) -> List[str]:
        """Return list of selected suite names."""
        return [s.name for s in self.get_selected_suites()]
    
    def restore_last_selection(self):
        """Restore the last checkbox selections from config."""
        last = self.favorites_mgr.get_last_selection()
        for name, var in self.check_vars.items():
            var.set(name in last)
    
    def save_selection(self):
        """Save current selections for next session."""
        selected = [n for n, v in self.check_vars.items() if v.get()]
        self.favorites_mgr.save_last_selection(selected)


# =============================================================================
# 3. CHANNEL SOURCE SELECTOR - Unified CH + REF dropdown
# =============================================================================
# INTEGRATION: Replace existing channel Combobox/Spinbox widgets in the
# test configuration panel. Wherever you have a channel selector, use
# ChannelSourceSelector instead.
# =============================================================================

class ChannelSourceSelector(tk.Frame):
    """
    Unified channel/reference source selector.
    Shows CH1-CH8 and REF1-REF4 in a single dropdown.
    
    Returns the source string (e.g., "CH1", "CH4", "REF2") which can be
    used directly in SCPI commands.
    """
    
    BG = "#1B2838"
    
    # Standard source options
    CHANNELS_4CH = ["CH1", "CH2", "CH3", "CH4"]
    CHANNELS_8CH = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7", "CH8"]
    REFERENCES = ["REF1", "REF2", "REF3", "REF4"]
    SEPARATOR = "────────────"  # Visual separator in dropdown
    
    def __init__(self, parent, label_text: str = "Source:",
                 max_channels: int = 4, include_refs: bool = True,
                 include_math: bool = False, default: str = "CH1",
                 on_change: Callable = None, **kwargs):
        """
        Args:
            parent: Parent widget
            label_text: Label to show before dropdown
            max_channels: 4 or 8 channels
            include_refs: Whether to include REF1-REF4
            include_math: Whether to include MATH1-MATH4
            default: Default selection
            on_change: Callback when selection changes
        """
        super().__init__(parent, bg=kwargs.pop('bg', self.BG), **kwargs)
        
        self._on_change = on_change
        self._var = tk.StringVar(value=default)
        
        # Build source list
        channels = self.CHANNELS_8CH[:max_channels]
        sources = list(channels)
        
        if include_refs:
            sources.append(self.SEPARATOR)
            sources.extend(self.REFERENCES)
        
        if include_math:
            sources.append(self.SEPARATOR)
            sources.extend([f"MATH{i}" for i in range(1, 5)])
        
        self._valid_sources = [s for s in sources if s != self.SEPARATOR]
        
        # Label
        if label_text:
            tk.Label(
                self, text=label_text, font=("Segoe UI", 9),
                fg="#E0E0E0", bg=self.cget("bg")
            ).pack(side="left", padx=(0, 5))
        
        # Dropdown
        self._combo = ttk.Combobox(
            self, textvariable=self._var, values=sources,
            state="readonly", width=10
        )
        self._combo.pack(side="left")
        self._combo.bind("<<ComboboxSelected>>", self._on_select)
    
    def _on_select(self, event=None):
        """Handle selection, skip separator rows."""
        val = self._var.get()
        if val == self.SEPARATOR:
            # Skip separator - revert to previous valid value
            self._var.set(self._valid_sources[0])
            return
        if self._on_change:
            self._on_change(val)
    
    def get(self) -> str:
        """Get current source selection (e.g., 'CH1', 'REF2')."""
        return self._var.get()
    
    def set(self, value: str):
        """Set the source selection."""
        if value in self._valid_sources:
            self._var.set(value)
    
    def get_channel_number(self) -> Optional[int]:
        """Get numeric channel number, or None if REF/MATH source."""
        val = self._var.get()
        if val.startswith("CH"):
            return int(val[2:])
        return None
    
    def is_reference(self) -> bool:
        """Check if current source is a reference waveform."""
        return self._var.get().startswith("REF")
    
    def get_scpi_source(self) -> str:
        """Get the SCPI-compatible source string."""
        return self._var.get()


# =============================================================================
# 4. RUN QUEUE MANAGER - Sequential multi-suite execution
# =============================================================================
# INTEGRATION: When user clicks "Run Test" with multiple suites selected,
# create a RunQueueManager and call run_queue(). This replaces the single
# suite run logic.
# =============================================================================

class RunQueueManager:
    """
    Manages sequential execution of multiple test suites.
    Provides a high-level progress bar and suite-level status tracking.
    Produces a single combined report.
    """
    
    def __init__(self, parent_frame: tk.Frame, status_callback: Callable = None):
        """
        Args:
            parent_frame: Frame to place the progress bar in
            status_callback: Callback for status updates: (message, suite_index, total)
        """
        self.parent_frame = parent_frame
        self.status_callback = status_callback
        self.queue: List[dict] = []  # List of {suite, results}
        self._cancelled = False
        self._progress_frame = None
        
    def build_progress_ui(self):
        """Create the multi-suite progress bar UI."""
        if self._progress_frame:
            self._progress_frame.destroy()
        
        BG = "#1B2838"
        FG = "#E0E0E0"
        ACCENT = "#0098DB"
        
        self._progress_frame = tk.Frame(self.parent_frame, bg=BG)
        self._progress_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        # Queue status label
        self._queue_label = tk.Label(
            self._progress_frame,
            text="Preparing test queue...",
            font=("Segoe UI", 10, "bold"),
            fg=ACCENT, bg=BG
        )
        self._queue_label.pack(anchor="w")
        
        # Overall progress bar
        self._overall_progress = ttk.Progressbar(
            self._progress_frame, mode="determinate", length=400
        )
        self._overall_progress.pack(fill="x", pady=(3, 2))
        
        # Suite detail label
        self._detail_label = tk.Label(
            self._progress_frame,
            text="",
            font=("Segoe UI", 9),
            fg="#8899AA", bg=BG
        )
        self._detail_label.pack(anchor="w")
        
        # Cancel button
        self._cancel_btn = tk.Button(
            self._progress_frame, text="Cancel Queue",
            font=("Segoe UI", 9), fg=FG, bg="#8B0000",
            activebackground="#AA0000", relief="flat",
            padx=10, pady=2, command=self.cancel
        )
        self._cancel_btn.pack(anchor="e", pady=(2, 0))
    
    def update_progress(self, suite_index: int, total: int,
                        suite_name: str, detail: str = ""):
        """Update the progress display."""
        if self._progress_frame is None:
            return
        
        pct = (suite_index / total) * 100
        self._overall_progress["value"] = pct
        self._queue_label.configure(
            text=f"Running suite {suite_index + 1} of {total}: {suite_name}"
        )
        if detail:
            self._detail_label.configure(text=detail)
        
        self._progress_frame.update_idletasks()
    
    def complete_progress(self, total_pass: int, total_fail: int):
        """Show completion status."""
        if self._progress_frame is None:
            return
        
        self._overall_progress["value"] = 100
        status = "PASS" if total_fail == 0 else "FAIL"
        color = "#2ECC71" if total_fail == 0 else "#E74C3C"
        
        self._queue_label.configure(
            text=f"Queue complete — {status}  ({total_pass} passed, {total_fail} failed)",
            fg=color
        )
        self._cancel_btn.configure(state="disabled")
        self._detail_label.configure(text="")
    
    def cancel(self):
        """Cancel remaining suites in the queue."""
        self._cancelled = True
        if self._queue_label:
            self._queue_label.configure(text="Cancelling...", fg="#F1C40F")
    
    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def cleanup(self):
        """Remove the progress UI."""
        if self._progress_frame:
            self._progress_frame.destroy()
            self._progress_frame = None


# =============================================================================
# 5. HELP VIEWER - Read-only document viewer
# =============================================================================
# INTEGRATION: Add a "Help" menu button to the main toolbar/menu bar.
# Call HelpViewer methods to open specific docs.
# =============================================================================

class HelpViewer:
    """
    Read-only document viewer that opens help content in a themed window.
    Can display local markdown/text files or open URLs in browser.
    """
    
    BG = "#1B2838"
    FG = "#E0E0E0"
    ACCENT = "#0098DB"
    CODE_BG = "#0D1B2A"
    
    # Help menu items - maps display name to (type, path/url)
    # Update these paths to match your MCP server doc locations
    HELP_ITEMS = {
        "Developing a New Test Suite": {
            "type": "doc",
            "filename": "TEK_PTA_PLUGIN_GUIDE.md",
            "description": "Guide to creating new Tek PTA test suite plugins"
        },
        "API Reference": {
            "type": "doc",
            "filename": "TEK_PTA_API_REFERENCE.md",
            "description": "Plugin API reference — classes, methods, callbacks"
        },
        "Theory of Operation": {
            "type": "doc",
            "filename": "TEK_PTA_AUTOMATION_GUIDE.md",
            "description": "Tek PTA architecture and automation best practices"
        },
        "Plugin Starting Template": {
            "type": "template",
            "description": "Copy a blank test suite template to get started"
        },
        "separator1": {"type": "separator"},
        "Tek Automate (Online)": {
            "type": "url",
            "url": "https://abnasim.github.io/TekAutomate/",
            "description": "Tektronix automation resources and guides"
        },
    }
    
    @classmethod
    def create_help_menu(cls, parent, menu_bar: tk.Menu, docs_dir: str = None):
        """
        Create a Help dropdown menu in the menu bar.
        
        Args:
            parent: Main application window
            menu_bar: The tk.Menu bar to add Help to
            docs_dir: Path to docs directory (where .md files live)
        """
        help_menu = tk.Menu(menu_bar, tearoff=0)
        
        for label, info in cls.HELP_ITEMS.items():
            if info["type"] == "separator":
                help_menu.add_separator()
            elif info["type"] == "url":
                import webbrowser
                help_menu.add_command(
                    label=f"🌐 {label}",
                    command=lambda url=info["url"]: webbrowser.open(url)
                )
            elif info["type"] == "doc":
                help_menu.add_command(
                    label=f"📄 {label}",
                    command=lambda fn=info["filename"], title=label:
                        cls._open_doc_viewer(parent, fn, title, docs_dir)
                )
            elif info["type"] == "template":
                help_menu.add_command(
                    label=f"📋 {label}",
                    command=lambda: cls._show_plugin_template(parent, docs_dir)
                )
        
        # About item
        help_menu.add_separator()
        help_menu.add_command(
            label="About Tek PTA",
            command=lambda: cls._show_about(parent)
        )
        
        menu_bar.add_cascade(label="Help", menu=help_menu)
    
    @classmethod
    def _open_doc_viewer(cls, parent, filename: str, title: str,
                          docs_dir: str = None):
        """Open a markdown/text file in a read-only viewer window."""
        # Search for the file in multiple locations
        search_paths = []
        if docs_dir:
            search_paths.append(os.path.join(docs_dir, filename))
        
        # Common locations relative to tek_pta.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths.extend([
            os.path.join(script_dir, "docs", filename),
            os.path.join(script_dir, "..", "docs", filename),
            os.path.join(script_dir, "..", "docs", "local_docs", filename),
            os.path.join(script_dir, filename),
        ])
        
        content = None
        found_path = None
        for path in search_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    found_path = path
                    break
                except Exception as e:
                    content = f"Error reading {path}: {e}"
        
        if content is None:
            messagebox.showwarning(
                "File Not Found",
                f"Could not find '{filename}'.\n\n"
                f"Searched in:\n" + "\n".join(search_paths[:3]),
                parent=parent
            )
            return
        
        # Create viewer window
        viewer = tk.Toplevel(parent)
        viewer.title(f"Help — {title}")
        viewer.geometry("800x600")
        viewer.configure(bg=cls.BG)
        
        # Top bar with filename
        top = tk.Frame(viewer, bg=cls.BG)
        top.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(
            top, text=title, font=("Segoe UI", 14, "bold"),
            fg=cls.ACCENT, bg=cls.BG
        ).pack(side="left")
        
        if found_path:
            tk.Label(
                top, text=os.path.basename(found_path),
                font=("Segoe UI", 9), fg="#667788", bg=cls.BG
            ).pack(side="right")
        
        # Text content area
        text_frame = tk.Frame(viewer, bg=cls.BG)
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        text = tk.Text(
            text_frame, wrap="word", font=("Consolas", 10),
            bg=cls.CODE_BG, fg=cls.FG, relief="flat",
            padx=15, pady=10, insertbackground=cls.FG,
            selectbackground="#2A4A64"
        )
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical",
                                   command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        
        # Apply basic markdown highlighting
        cls._apply_markdown_tags(text)
        
        # Insert content
        text.insert("1.0", content)
        
        # Apply tag styling to inserted content
        cls._highlight_markdown(text)
        
        # Make read-only
        text.configure(state="disabled")
        
        # Close button
        btn_frame = tk.Frame(viewer, bg=cls.BG)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Button(
            btn_frame, text="Close", font=("Segoe UI", 10),
            fg=cls.FG, bg="#2A3F54", relief="flat", padx=15, pady=4,
            command=viewer.destroy
        ).pack(side="right")
    
    @classmethod
    def _apply_markdown_tags(cls, text_widget):
        """Configure text tags for markdown rendering."""
        text_widget.tag_configure("h1", font=("Segoe UI", 16, "bold"),
                                   foreground=cls.ACCENT)
        text_widget.tag_configure("h2", font=("Segoe UI", 13, "bold"),
                                   foreground="#4FC3F7")
        text_widget.tag_configure("h3", font=("Segoe UI", 11, "bold"),
                                   foreground="#81D4FA")
        text_widget.tag_configure("code", font=("Consolas", 10),
                                   background="#162030", foreground="#98FB98")
        text_widget.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        text_widget.tag_configure("bullet", foreground="#0098DB")
    
    @classmethod
    def _highlight_markdown(cls, text_widget):
        """Apply basic markdown highlighting to text content."""
        content = text_widget.get("1.0", "end")
        lines = content.split("\n")
        
        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()
            
            if stripped.startswith("# "):
                text_widget.tag_add("h1", f"{line_num}.0", f"{line_num}.end")
            elif stripped.startswith("## "):
                text_widget.tag_add("h2", f"{line_num}.0", f"{line_num}.end")
            elif stripped.startswith("### "):
                text_widget.tag_add("h3", f"{line_num}.0", f"{line_num}.end")
            elif stripped.startswith("- ") or stripped.startswith("* "):
                text_widget.tag_add("bullet", f"{line_num}.0", f"{line_num}.2")
            elif stripped.startswith("```"):
                text_widget.tag_add("code", f"{line_num}.0", f"{line_num}.end")
    
    @classmethod
    def _show_plugin_template(cls, parent, docs_dir=None):
        """Show the plugin template and offer to save a copy."""
        template = _get_plugin_template()
        
        viewer = tk.Toplevel(parent)
        viewer.title("Help — Plugin Starting Template")
        viewer.geometry("800x600")
        viewer.configure(bg=cls.BG)
        
        # Top bar
        top = tk.Frame(viewer, bg=cls.BG)
        top.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(
            top, text="New Test Suite Template", font=("Segoe UI", 14, "bold"),
            fg=cls.ACCENT, bg=cls.BG
        ).pack(side="left")
        
        # Save button
        def save_template():
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                parent=viewer,
                title="Save Plugin Template",
                defaultextension=".py",
                filetypes=[("Python files", "*.py")],
                initialfile="my_test_suite.py"
            )
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(template)
                messagebox.showinfo("Saved",
                    f"Template saved to:\n{path}", parent=viewer)
        
        tk.Button(
            top, text="💾 Save Copy...", font=("Segoe UI", 10),
            fg=cls.FG, bg="#2A3F54", relief="flat", padx=10, pady=3,
            command=save_template
        ).pack(side="right")
        
        # Template content
        text_frame = tk.Frame(viewer, bg=cls.BG)
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        text = tk.Text(
            text_frame, wrap="none", font=("Consolas", 10),
            bg=cls.CODE_BG, fg="#98FB98", relief="flat",
            padx=15, pady=10
        )
        y_scroll = ttk.Scrollbar(text_frame, orient="vertical",
                                  command=text.yview)
        x_scroll = ttk.Scrollbar(text_frame, orient="horizontal",
                                  command=text.xview)
        text.configure(yscrollcommand=y_scroll.set,
                       xscrollcommand=x_scroll.set)
        
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")
        text.pack(side="left", fill="both", expand=True)
        
        text.insert("1.0", template)
        text.configure(state="disabled")
        
        # Close button
        btn_frame = tk.Frame(viewer, bg=cls.BG)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Button(
            btn_frame, text="Close", font=("Segoe UI", 10),
            fg=cls.FG, bg="#2A3F54", relief="flat", padx=15, pady=4,
            command=viewer.destroy
        ).pack(side="right")
    
    @classmethod
    def _show_about(cls, parent):
        """Show About dialog."""
        try:
            import tek_pta
            version = tek_pta.__version__
        except (ImportError, AttributeError):
            version = __version__
        
        messagebox.showinfo(
            "About Tek PTA",
            f"Tek PTA — Production Test Assistant\n"
            f"Version {version}\n\n"
            f"Developed by Tektronix Application Engineers\n"
            f"Contact: andre.asbury@tektronix.com\n\n"
            f"Internal prototype — not for distribution.",
            parent=parent
        )


# =============================================================================
# 6. FAVORITES MANAGER - Persistence for suite preferences
# =============================================================================

class FavoritesManager:
    """
    Manages favorite suites, last-used tracking, and last selections.
    Persists to tek_pta_config.json.
    """
    
    def __init__(self, config_path: str = None):
        self._config_path = config_path or _get_config_path()
        self._config = _load_config(self._config_path)
        
        if "favorites" not in self._config:
            self._config["favorites"] = []
        if "usage_history" not in self._config:
            self._config["usage_history"] = {}
        if "last_selection" not in self._config:
            self._config["last_selection"] = []
    
    def is_favorite(self, suite_name: str) -> bool:
        return suite_name in self._config["favorites"]
    
    def toggle_favorite(self, suite_name: str) -> bool:
        """Toggle favorite status. Returns new state."""
        favs = self._config["favorites"]
        if suite_name in favs:
            favs.remove(suite_name)
            result = False
        else:
            favs.append(suite_name)
            result = True
        self._save()
        return result
    
    def record_usage(self, suite_name: str):
        """Record that a suite was run."""
        self._config["usage_history"][suite_name] = datetime.now().isoformat()
        self._save()
    
    def get_last_used_rank(self, suite_name: str) -> float:
        """Lower rank = more recently used. Returns large value if never used."""
        history = self._config["usage_history"]
        if suite_name in history:
            try:
                dt = datetime.fromisoformat(history[suite_name])
                # Negative timestamp so more recent = lower rank
                return -dt.timestamp()
            except (ValueError, TypeError):
                pass
        return float('inf')
    
    def save_last_selection(self, suite_names: List[str]):
        """Save the current checkbox selections."""
        self._config["last_selection"] = list(suite_names)
        self._save()
    
    def get_last_selection(self) -> List[str]:
        """Get the last saved checkbox selections."""
        return self._config.get("last_selection", [])
    
    def _save(self):
        _save_config(self._config_path, self._config)


# =============================================================================
# HELPER: Plugin template text
# =============================================================================

def _get_plugin_template() -> str:
    """Return the starter plugin template as a string."""
    return '''#!/usr/bin/env python3
"""
My Custom Test Suite for Tek PTA
=================================

Description of what this test suite does.

Required Equipment:
- MSO 4/5/6 Series Oscilloscope

Instructions:
1. Place this file in the test_suites/ folder next to tek_pta.py
2. Restart Tek PTA - the suite will be auto-discovered
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

# =============================================================================
# PLUGIN API DEFINITIONS (copied for portability)
# =============================================================================

class TestStatus(Enum):
    NOT_RUN = "NOT_RUN"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"

@dataclass
class TestPoint:
    name: str
    unit: str = ""
    nominal: float = 0.0
    low_limit: float = 0.0
    high_limit: float = 0.0
    measured: Optional[float] = None
    status: TestStatus = TestStatus.NOT_RUN
    notes: str = ""

@dataclass
class TestSuitePlugin:
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    required_instruments: List[str] = field(default_factory=lambda: ["scope"])
    engine_class: Optional[type] = None
    config: Dict[str, Any] = field(default_factory=dict)
    setup_image_path: Optional[str] = None

class TestEngineBase:
    """Base class for custom test engines."""
    
    def __init__(self):
        self.test_points: List[TestPoint] = []
        self.instrument_manager = None  # Set by Tek PTA at runtime
    
    def generate_test_points(self, config=None) -> List[TestPoint]:
        """REQUIRED: Create and return test points for the UI table."""
        raise NotImplementedError
    
    def run_test(self, test_point: TestPoint, config=None) -> TestPoint:
        """REQUIRED: Execute a single test point measurement."""
        raise NotImplementedError
    
    def setup_instruments(self, config=None):
        """Optional: Configure instruments before test run."""
        pass
    
    def cleanup(self, config=None):
        """Optional: Reset instruments after test run."""
        pass


# =============================================================================
# YOUR CUSTOM TEST ENGINE
# =============================================================================

class MyTestEngine(TestEngineBase):
    """Custom test engine - implement your measurement logic here."""
    
    def generate_test_points(self, config=None) -> List[TestPoint]:
        """Define your test points with limits."""
        self.test_points = [
            TestPoint(
                name="Frequency",
                unit="Hz",
                nominal=1000.0,
                low_limit=990.0,
                high_limit=1010.0
            ),
            TestPoint(
                name="Amplitude",
                unit="V",
                nominal=1.0,
                low_limit=0.95,
                high_limit=1.05
            ),
        ]
        return self.test_points
    
    def setup_instruments(self, config=None):
        """Configure the oscilloscope for this test."""
        im = self.instrument_manager
        if im and im.scope:
            im.send_command(im.scope, "*RST")
            im.send_command(im.scope, "AUTOSet EXECute")
    
    def run_test(self, test_point: TestPoint, config=None) -> TestPoint:
        """Measure a single test point."""
        im = self.instrument_manager
        
        if test_point.name == "Frequency":
            if im and im.scope:
                # Example: query a measurement
                result = im.query(im.scope, "MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")
                test_point.measured = float(result)
            else:
                test_point.measured = 1000.5  # Simulated
        
        elif test_point.name == "Amplitude":
            if im and im.scope:
                result = im.query(im.scope, "MEASUrement:MEAS2:RESUlts:CURRentacq:MEAN?")
                test_point.measured = float(result)
            else:
                test_point.measured = 1.02  # Simulated
        
        # Check pass/fail
        if test_point.low_limit <= test_point.measured <= test_point.high_limit:
            test_point.status = TestStatus.PASS
        else:
            test_point.status = TestStatus.FAIL
        
        return test_point
    
    def cleanup(self, config=None):
        """Reset after test."""
        pass


# =============================================================================
# REGISTER SUITES (REQUIRED)
# =============================================================================

def register_suites() -> List[TestSuitePlugin]:
    """
    REQUIRED: Return a list of TestSuitePlugin instances.
    Tek PTA calls this function to discover your test suites.
    """
    return [
        TestSuitePlugin(
            name="My Custom Test",
            description="Measures frequency and amplitude of a signal",
            version="1.0.0",
            author="Your Name",
            required_instruments=["scope"],
            engine_class=MyTestEngine,
            config={
                "channel": "CH1",      # Can now use "REF1", "REF2", etc.
                "num_acquisitions": 10,
            },
        ),
    ]
'''


# =============================================================================
# SHARED CONFIG UTILITIES
# =============================================================================

def _get_config_path() -> str:
    """Get path to tek_pta_config.json next to the main script."""
    # Try to find it relative to tek_pta.py first
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "tek_pta_config.json")


def _load_config(path: str) -> dict:
    """Load config from JSON file, return empty dict if not found."""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def _save_config(path: str, config: dict):
    """Save config to JSON file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, default=str)
    except IOError as e:
        print(f"Warning: Could not save config to {path}: {e}")


# =============================================================================
# STANDALONE TEST - Run this file directly to preview the components
# =============================================================================

if __name__ == "__main__":
    print(f"Tek PTA v{__version__} Upgrade Module - Component Preview")
    print("=" * 60)
    
    root = tk.Tk()
    root.withdraw()
    
    # Test splash screen
    print("\n[1] Testing Splash Screen...")
    accepted = SplashScreen.show(root, version=__version__)
    print(f"    User {'accepted' if accepted else 'declined'}")
    
    if not accepted:
        print("    User declined — exiting.")
        root.destroy()
        exit(0)
    
    # Test suite selector with mock suites
    print("\n[2] Testing Suite Selector...")
    
    @dataclass
    class MockSuite:
        name: str
        description: str
    
    from dataclasses import dataclass
    
    mock_suites = [
        MockSuite("AFG Frequency Sweep", "Sweep AFG output and verify scope measurements"),
        MockSuite("LED Current Test", "SMU + Scope current comparison at multiple voltages"),
        MockSuite("Spectrum Scanner (FM)", "Scan FM radio band 88-108 MHz"),
        MockSuite("PRBS7 DUT Test", "AWG PRBS7 stimulus with scope verification"),
        MockSuite("Power Supply Ripple", "Measure ripple and noise on DC rails"),
    ]
    
    test_win = tk.Toplevel(root)
    test_win.title("Suite Selector Preview")
    test_win.geometry("700x400")
    test_win.configure(bg="#1B2838")
    
    selector = SuiteSelector(test_win, mock_suites)
    selector.pack(fill="both", expand=True)
    
    def on_run():
        selected = selector.get_selected_names()
        print(f"    Selected: {selected}")
        messagebox.showinfo("Selected", f"Suites: {', '.join(selected) or 'None'}")
    
    tk.Button(
        test_win, text="Run Selected", command=on_run,
        font=("Segoe UI", 11, "bold"), fg="white", bg="#0098DB",
        relief="flat", padx=20, pady=6
    ).pack(pady=10)
    
    # Test Help Viewer
    print("\n[3] Testing Help Menu...")
    menu_bar = tk.Menu(test_win)
    HelpViewer.create_help_menu(test_win, menu_bar)
    test_win.config(menu=menu_bar)
    
    print("\n    Preview window open. Close to exit.")
    root.mainloop()
