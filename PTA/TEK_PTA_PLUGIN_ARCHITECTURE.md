# Tek PTA Plugin Architecture Design

## Overview

This document describes the modular test suite architecture for Tek PTA, enabling test suites to be defined in external Python files rather than embedded in the main `tek_pta.py` application.

## Goals

1. **Separation of Concerns**: Core application code remains stable; new tests added as separate files
2. **Easy Test Development**: Claude (or engineers) can create new tests without modifying tek_pta.py
3. **Discoverability**: Automatic loading of test suites from a designated folder
4. **Extensibility**: Browse button to import additional test suite files

## Architecture

### Directory Structure

```
tek_pta/
├── tek_pta.py              # Main application (stable, rarely changed)
├── test_suites/            # Plugin directory (auto-discovered)
│   ├── __init__.py         # Package marker
│   ├── builtin_suites.py   # Built-in test suites (AFG, LED, Spectrum, Eye, AGC)
│   ├── custom_power.py     # Example custom test
│   └── user_imported/      # User-imported suites via Browse button
│       └── my_tests.py
└── build_exe.py            # Exe builder
```

### Plugin File Format

Each plugin file must define a `register_suites()` function that returns a list of `TestSuitePlugin` objects:

```python
# Example: custom_power.py
from tek_pta_plugin_api import TestSuitePlugin, TestEngine

class PowerSupplyEngine(TestEngine):
    """Custom test engine for power supply verification"""
    
    def setup(self, scope, config):
        # Configure scope for power measurements
        pass
    
    def run_test(self, test_point):
        # Execute single test point
        pass

def register_suites():
    return [
        TestSuitePlugin(
            name="Power Supply Verification",
            description="Tests DC output voltage and ripple at various loads.",
            test_type="power_supply",
            config={
                "voltage_levels": [3.3, 5.0, 12.0],
                "load_currents": [0.1, 0.5, 1.0],
                "tolerance_pct": 2.0
            },
            required_instruments=["Oscilloscope", "DC Load"],
            engine_class=PowerSupplyEngine,  # Optional: custom engine
            config_panel_builder=build_power_config,  # Optional: custom UI
        ),
    ]
```

### Plugin API (tek_pta_plugin_api.py)

A simple API module that plugins import to get access to base classes:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Type

@dataclass
class TestSuitePlugin:
    name: str
    description: str
    test_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    required_instruments: List[str] = field(default_factory=list)
    engine_class: Optional[Type] = None  # Custom engine or None for built-in
    config_panel_builder: Optional[Callable] = None  # Custom config UI
    setup_diagram_generator: Optional[Callable] = None  # Custom diagram
    results_columns: Optional[List[tuple]] = None  # Custom result columns

class TestEngine:
    """Base class for custom test engines"""
    
    def __init__(self, inst_manager):
        self.inst = inst_manager
        self.on_log = None
        self.on_progress = None
        self.on_test_start = None
        self.on_test_complete = None
        self.on_screenshot = None
        self.on_complete = None
        self.test_points = []
    
    def setup(self, scope, config: dict):
        """Configure instruments before test run"""
        raise NotImplementedError
    
    def run_test(self, test_point) -> None:
        """Execute a single test point"""
        raise NotImplementedError
    
    def cleanup(self):
        """Cleanup after test run"""
        pass
```

### Discovery and Loading

The main application discovers plugins at startup:

```python
def discover_plugins(plugin_dirs: List[Path]) -> List[TestSuitePlugin]:
    """Discover and load test suite plugins from directories"""
    plugins = []
    
    for plugin_dir in plugin_dirs:
        if not plugin_dir.exists():
            continue
            
        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            
            try:
                spec = importlib.util.spec_from_file_location(
                    py_file.stem, py_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, 'register_suites'):
                    suites = module.register_suites()
                    plugins.extend(suites)
                    
            except Exception as e:
                print(f"Failed to load plugin {py_file}: {e}")
    
    return plugins
```

### UI Integration

1. **Browse Button**: Opens file dialog to import .py plugin files
2. **Plugin Manager**: Shows loaded plugins, allows enable/disable
3. **Automatic Reload**: Detects changes to plugin files

## Implementation Steps

### Phase 1: Extract Built-in Suites
1. Create `test_suites/builtin_suites.py` with existing test definitions
2. Move AFGFrequencyEngine, LEDCurrentEngine, etc. to separate files
3. Keep backward compatibility - tek_pta.py still works standalone

### Phase 2: Plugin Discovery
1. Add plugin discovery code to tek_pta.py
2. Merge discovered plugins with built-in suites
3. Add Browse button to import user plugins

### Phase 3: Custom Engine Support
1. Allow plugins to define custom test engines
2. Support custom config panels
3. Support custom result columns

## UI Changes for Word Wrap

### Select Test Suite Dialog (Line ~3858)
- Increase `wraplength` from 550 to match dialog width minus padding
- Make dialog resizable
- Use `fill=tk.BOTH, expand=True` for text labels

### Configuration Section (Line ~3124)
- Increase `wraplength` from 600 to dynamic width
- Bind to `<Configure>` event to update wraplength on resize
- Increase minimum width of notebook/config panel

## Migration Path

1. **Phase 1**: UI fixes only (immediate value)
2. **Phase 2**: Create plugin infrastructure, keep built-in tests in tek_pta.py
3. **Phase 3**: Extract built-in tests to plugins
4. **Phase 4**: Full plugin ecosystem with documentation

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| tek_pta.py | Modify | Add plugin discovery, UI fixes |
| tek_pta_plugin_api.py | Create | Base classes for plugins |
| test_suites/builtin_suites.py | Create | Built-in test suite definitions |
| test_suites/__init__.py | Create | Package marker |

## Benefits

1. **Claude Integration**: Claude can add tests by creating new files, not editing 5000 lines
2. **User Customization**: Users can add their own tests without touching core code
3. **Version Control**: Clear separation of stable core vs evolving tests
4. **Testing**: Easier to test individual plugins
5. **Distribution**: Ship core app + example plugins separately
