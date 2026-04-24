# Changelog

All notable changes to the Tektronix MCP Server and Tek PTA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.1] - 2026-02-03

### Added

#### MCP Server
- **Multitone Plugin** (`multitone_plugin.json`) - 31 commands for AWG70000/SourceXpress
  - Chirp waveform generation (frequency sweep, high/low frequency, sweep rate/time)
  - Tones generation (start/end frequency, phase, spacing, notch filters)
  - Compile settings and correction file support
- **Pulse Plugin** (`pulse_plugin.json`) - 34 commands for AWG5200/SourceXpress
  - Pulse train management (add/delete/select, amplitude, channel assignment)
  - Pulse frame configuration (shape, rise/fall time, width, PRI/PRF)
  - Sequence compilation support
- **RF Generic Signals Plugin** (`rfgsignal_plugin.json`) - 92 commands for AWG70000/AWG5200/SourceXpress
  - Multi-carrier signal generation
  - Digital modulation (PSK, QAM, FSK, ASK, APSK, CPM)
  - Analog modulation (AM, FM, PM)
  - IQ impairments, interference, multipath simulation
  - S-parameter channel emulation

#### Tek PTA
- **Eye Diagram Test Suite** - Automated eye diagram analysis for high-speed serial signals
  - Eye Height (HEIGHT) and Eye Width (WIDTH) measurements
  - Pattern Length and Data Rate measurements
  - Deterministic Jitter (DJ) analysis
  - DFE equalization support with tap configuration
  - PLL bandwidth presets for common standards (DisplayPort, USB, PCIe, HDMI)
- **Lessons Learned System** - Knowledge capture for future sessions
  - `tek_save_lessons_learned` tool for documenting test development insights
  - `tek_list_lessons_learned` tool for viewing saved documentation
  - Automatic integration with `tek_search_local_docs`
- **Eye Diagram Lessons Learned** (`eye_diagram_lessons_learned.md`)
  - Documented correct SCPI measurement types (HEIGHT vs EYEHEIGHT)
  - Reference waveform requirements for eye measurements
  - Single acquisition vs multiple acquisition strategies
  - Population limiting for stable statistics

### Changed
- Total verified SCPI commands increased from 12,688 to 12,845 (+157 commands)
- Documentation updates for new plugin support

### Fixed
- Minor documentation corrections in automation guidelines

---

## [1.0.0] - 2026-01-31

### Added

#### MCP Server - Initial Release
- **Core SCPI Database** - 12,688 verified commands from official Tektronix documentation
- **Supported Instrument Families:**
  - MSO 2/4/5/6 Series & DPO 7 Series Oscilloscopes (2,753 commands)
  - MDO 3 Series Mixed Domain Oscilloscopes (3,374 commands)
  - MDO4000/MSO4000B/DPO4000B/MDO3000 Series (3,788 commands)
  - MSO/DPO 5000/7000/70000 & DSA70000 Series (1,481 commands)
  - AFG31000 Series Arbitrary Function Generators (189 commands)
  - AWG5200 Series Arbitrary Waveform Generators (314 commands)
  - AWG70000 Series Arbitrary Waveform Generators (364 commands)
  - High Speed Serial (HSS) Plug-in (160 commands)
  - SignalVu Vector Signal Analysis Software (202 commands)
  - Keithley SMU Source Measure Units (63 commands)

- **MCP Tools:**
  - `tek_search_commands` - Keyword search across SCPI databases
  - `tek_get_command` - Detailed command information lookup
  - `tek_list_groups` - List available command groups
  - `tek_get_group_commands` - Get all commands in a group
  - `tek_list_instruments` - Show supported instrument families
  - `tek_search_local_docs` - Search markdown documentation and Python examples
  - `tek_vector_search` - OpenAI vector store search for complex queries
  - `tek_comprehensive_search` - Multi-tier intelligent search
  - `tek_get_test_template` - Python test automation templates
  - `tek_legacy_command_lookup` - Legacy to modern SCPI migration
  - `tek_status` - Server status and diagnostics

- **Documentation:**
  - Tektronix Automation Guidelines (best practices for SCPI automation)
  - TEK PTA Automation Guide (measurement patterns and lessons learned)
  - Legacy to Modern SCPI Migration Guide
  - Setup and Troubleshooting Guide

#### Tek PTA - Initial Release
- **Production Test Assistant GUI** - Standalone tkinter application
- **Instrument Management:**
  - Auto-discovery via PyVISA
  - Manual instrument connection
  - Multi-instrument support (oscilloscopes, SMUs, AWGs)
- **Test Suite Plugin System:**
  - Modular test suite architecture
  - Real-time test execution with progress tracking
  - Pass/fail reporting with detailed results
  - CSV and screenshot export
- **Built-in Test Suites:**
  - LED Current Test Suite (SMU + Oscilloscope)
  - Basic measurements template
- **Plugin Development Guide** - Documentation for creating custom test suites

### Technical Details
- Python 3.10+ required for MCP Server
- Python 3.9+ required for Tek PTA
- FastMCP framework for Claude Desktop integration
- PyVISA for instrument communication
- Optional OpenAI integration for vector store searches

---

## Version History Summary

| Version | Date | Commands | Key Features |
|---------|------|----------|--------------|
| 1.0.1 | 2026-02-03 | 12,845 | AWG plugins, Eye diagram test suite, Lessons learned |
| 1.0.0 | 2026-01-31 | 12,688 | Initial release, 10 instrument families |

---

## Roadmap

### Planned for Future Releases
- TBS2000B oscilloscope support
- MP5000 modular platform support
- AFG1000/2000 function generator support
- Keithley DMM support
- Web-based interface option
- Offline documentation bundles
- Additional test suite templates

---

## Contributing

This project is developed by Tektronix Application Engineers. For questions, feature requests, or bug reports, contact your Tektronix FAE or account manager.

**Maintainer:** Andre Asbury, Tektronix Application Engineer

---

## License

Tek PTA is free "AE-ware" from Tektronix - free to use, share, and modify for test automation purposes.
