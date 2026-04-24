# =============================================================================
# PI TRANSLATOR TOOLS - SCPI Code Migration
# =============================================================================
# These tools help generate and validate PI Translator XML files for migrating
# legacy oscilloscope automation code to modern Tektronix instruments.
#
# Insert this section into tektronix_mcp_server.py BEFORE the status tool.
# Also add PI_TRANSLATOR_PATH to the CONFIGURATION section:
#   PI_TRANSLATOR_PATH = DOCS_REFERENCE_PATH / "pi_translator"
# And add to search_local_docs search_specs:
#   (PI_TRANSLATOR_PATH, "**/*.xml", "xml", 0),
#   (PI_TRANSLATOR_PATH, "**/*.md", "markdown", 0),
# =============================================================================

import re
import xml.etree.ElementTree as ET
from xml.dom import minidom


# --- Configuration (add to CONFIGURATION section) ---
# PI_TRANSLATOR_PATH = DOCS_REFERENCE_PATH / "pi_translator"  # PI Translator examples & reference


@mcp.tool()
@with_flush
def tek_pi_translator_reference() -> str:
    """Get the complete PI Translator XML syntax reference and best practices.
    
    Call this FIRST before generating any PI Translator XML.
    Returns the XML format specification, all keyword/translation attributes,
    and patterns for common translation scenarios.
    """
    return """## PI Translator XML Syntax Reference

### Overview
The PI Translator is built into modern Tektronix oscilloscopes (firmware v1.30+).
It intercepts legacy SCPI commands and translates them to modern equivalents.
Translations are defined in XML "Compatibility Files".

**Supported Scopes:** 2 Series MSO, 4/5/6 Series MSO, 5/6 Series B MSO, MSO58LP, LPD64

### XML File Structure

```xml
<?xml version='1.0' encoding='utf-8'?>
<!-- Compatibility file: [Source] to [Target] -->
<translations version='0.5'>
    
    <!-- Each legacy command is broken into keyword nodes -->
    <keyword name="HORizontal">
        <keyword name="RECOrdlength" leaf="1" command="1" query="1">
            <translation header=":HORizontal:RECOrdlength"/>
        </keyword>
    </keyword>
    
</translations>
```

### Keyword Attributes

| Attribute | Required | Description |
|-----------|----------|-------------|
| `name` | **YES** | Keyword in UPPERlower format (uppercase = short form). Use `?` for suffix placeholders (e.g., `CH?`, `MATH?`, `MEAS?`) |
| `leaf="1"` | No | This keyword is a valid end-of-command. MUST have a `<translation>` child |
| `command="1"` | No | Valid as a set command (with argument). Default: 0 |
| `query="1"` | No | Valid as a query (?). Default: 0 |
| `argument="1"` | No | Translation depends on the argument value. Pair with `sensitiveArgument` |
| `specialSuffix="1"` | No | Suffix (channel number) affects translation. Preserves suffix info |

### Translation Attributes

| Attribute | Required | Description |
|-----------|----------|-------------|
| `header` | **YES** | Modern command. Use `?` where suffix goes. Lead with colon. |
| `addedArgument="1"` | No | Header already includes its argument (no further arg handling) |
| `sensitiveArgument="VAL"` | No | Use this translation ONLY when argument matches VAL (UPPERlower) |
| `reuseSuffix="1"` | No | Preserve suffix for the NEXT translation in a one-to-many |
| `reuseArgument="1"` | No | Preserve argument for the NEXT translation. REQUIRES `countOfArguments` |
| `countOfArguments="1"` | No | Number of arguments to preserve. **REQUIRED** when using `reuseArgument` |
| `sendInQuery="0"` | No | Don't send this translation when command is a query. Default: 1 |
| `delyDuration="100"` | No | Add delay (ms) after this command executes |

### Translation Patterns

#### Pattern 1: Simple One-to-One
Legacy command maps directly to one modern command.
```xml
<!-- HOR:TRIG:POS → HOR:POS -->
<keyword name="HORizontal">
    <keyword name="TRIGger">
        <keyword name="POSition" leaf="1" command="1" query="1">
            <translation header=":HORizontal:POSition"/>
        </keyword>
    </keyword>
</keyword>
```

#### Pattern 2: One-to-Many
Single legacy command requires multiple modern commands.
```xml
<!-- HOR:RECORDLENGTH → set manual mode + set record length -->
<keyword name="HORizontal">
    <keyword name="RECOrdlength" leaf="1" command="1" argument="1" query="1">
        <translation header=":HORizontal:MODe MANUAL" addedArgument="1" sendInQuery="0"/>
        <translation header=":HORizontal:RECOrdlength"/>
    </keyword>
</keyword>
```

#### Pattern 3: Argument-Dependent
Translation changes based on the argument value.
```xml
<!-- CH1:IMPedance MEG → CH1:TERMination 1E6 -->
<!-- CH1:IMPedance FIFty → CH1:TERMination 50 -->
<keyword name='CH?' specialSuffix='1'>
    <keyword name="IMPedance" leaf="1" command="1" query="1" argument="1">
        <translation header=":CH?:TERMination 1E6" addedArgument='1' 
                     sensitiveArgument="MEG" sendInQuery="1"/>
        <translation header=":CH?:TERMination 50" addedArgument='1' 
                     sensitiveArgument="FIFty" sendInQuery="0"/>
    </keyword>
</keyword>
```

#### Pattern 4: Global → Per-Channel (reuseArgument)
Legacy global command must be applied to each channel individually.
```xml
<!-- TRIGGER:A:LEVEL 0.5 → set level on all channels -->
<keyword name="TRIGger">
    <keyword name="?">
        <keyword name="LEVel" leaf="1" command="1" query="0">
            <translation header=":trigger:?:level:ch1" reuseSuffix="1" 
                        reuseArgument="1" countOfArguments="1"/>
            <translation header=":trigger:?:level:ch2" reuseSuffix="1" 
                        reuseArgument="1" countOfArguments="1"/>
            <translation header=":trigger:?:level:ch3" reuseSuffix="1" 
                        reuseArgument="1" countOfArguments="1"/>
            <translation header=":trigger:?:level:ch4"/>
        </keyword>
    </keyword>
</keyword>
```
**CRITICAL:** `reuseArgument` on channels 1-3, removed on last channel. `countOfArguments` REQUIRED.

#### Pattern 5: Skip Unnecessary Command
Legacy command has no modern equivalent - send linefeed to no-op.
```xml
<!-- DISplay:SHOWREmote → not needed, skip it -->
<keyword name='DISplay'>
    <keyword name='SHOWREmote' leaf="1" command="1" argument="1">
        <translation header="&#10;" addedArgument="1"/>
    </keyword>
</keyword>
```

#### Pattern 6: Debug/Verification Entry
Include to verify your compatibility file loaded correctly.
```xml
<keyword name="BATman" leaf="1" command="1" query="1">
    <translation header='callouts:callout1:text'/>
</keyword>
```
Send: `BATman "File v1.0 loaded"` then `*ESR?` → if 0, file loaded OK.

### Common Migration Mappings (Quick Reference)

| Category | Legacy | Modern |
|----------|--------|--------|
| Timebase | `:HORizontal:MODe:SCAle` | `:HORizontal:SCAle` |
| Record Length | `:HORizontal:RECOrdlength` | `:HORizontal:MODe MANUAL` then `:HORizontal:RECOrdlength` |
| Sample Rate | `:HORizontal:MODe:SAMPLERate` | `:HORizontal:SAMPLERate` |
| Position | `:HORizontal:MAIn:POSition` | `:HORizontal:POSition` |
| Trigger Pos | `:HORizontal:TRIGger:POSition` | `:HORizontal:POSition` |
| Channel On | `:SELect:CH1 ON` | `:DISplay:GLObal:CH1:STATE ON` |
| Ch State | `:CH1:STATE ON` | `:DISplay:GLObal:CH1:STATE ON` |
| Impedance | `:CH1:IMPedance MEG` | `:CH1:TERMination 1E6` |
| Impedance | `:CH1:IMPedance FIFty` | `:CH1:TERMination 50` |
| Bandwidth | `:CH1:BANdwidth TWO` | `:CH1:BANdwidth 250E6` |
| Math Pos | `:MATH:MATH1:POSITION` | `:DISplay:WAVEView1:MATH:MATH1:VERTical:POSition` |
| Math Scale | `:MATH:MATH1:SCAle` | `:DISplay:WAVEView1:MATH:MATH1:VERTical:SCAle` |
| Math Def | `:MATH1:DEFine` | `:MATH:MATH1:DEFine` |
| Cursor Func | `:CURSor:FUNCtion` | `:DISplay:WAVEView1:CURSor:CURSOR:FUNCtion` |
| Cursor VBar | `:CURSor:VBArs:POSITION1` | `:DISplay:WAVEView1:CURSor:CURSOR1:VBArs:APOSition` |
| Probe | `:CH1:PROBE?` | `:CH1:PROBEFunc:EXTAtten?` |
| Wfm Header | `:WFMPRe?` | `:WFMOutpre?` |
| Hardcopy | `:HARDCOPY:FILENAME` | `:SAVe:IMAGe:FULLPath` |
| Acq Mode | `:ACQuire:MODe NORMALSAMPLE` | `:ACQuire:MODe SAMPLE` |
| DPOJET | `:DPOJET:GATing` | `:MEASUrement:MEAS1:GATing` |
| Meas Type | `:MEAS1:TYPe RISE` | `:MEAS1:TYPe risetime` |
| Trigger pol | `:TRIGger:A:TIMEOUT:POL STAYHigh` | `:TRIGger:A:TIMEOUT:POL STAYSHigh` |
| Trigger Type | `:TRIGger:A:TYPe PULSe` | `:TRIGger:A:TYPe width` |

### Critical Rules

1. **UPPERlower Format:** Uppercase = valid short form. `HORizontal` means `HOR` is accepted.
2. **Suffix Placeholder:** Use `?` in name for variable suffixes: `CH?`, `MATH?`, `MEAS?`
3. **Header Colon:** Translation headers should lead with colon: `header=":HORizontal:POSition"`
4. **reuseArgument REQUIRES countOfArguments:** Always pair these. Omit both on the LAST translation.
5. **sendInQuery:** In one-to-many, only ONE translation should send in query mode. Others = `sendInQuery="0"`.
6. **Last sensitiveArgument = default:** If no `sensitiveArgument` on the last translation, it becomes the fallback.
7. **&#10; for no-op:** Use XML linefeed `&#10;` with `addedArgument="1"` to skip commands.
8. **Test with *ESR?:** After each command, query `*ESR?`. Value of 0 means no error.

### Enabling the PI Translator
```
# Via SCPI:
COMPatibility:ENABLE 1

# File locations:
# Linux:   C:/PICompatibility/Compatibility.xml
# Windows: C:\\Users\\Public\\Tektronix\\TekScope\\PICompatibility\\Compatibility.xml
```
"""


@mcp.tool()
@with_flush
def tek_extract_scpi_from_code(code: str) -> str:
    """Extract SCPI commands from legacy automation code.
    
    Parses Python, LabVIEW, C, or other code to find SCPI command strings.
    Returns a categorized list of unique commands found.
    
    Args:
        code: The legacy automation source code (paste the code directly)
    
    Returns:
        Categorized list of SCPI commands with line numbers and context
    """
    commands = []
    seen = set()
    lines = code.split('\n')
    
    # Patterns to match SCPI commands in various languages
    patterns = [
        # Python: scope.write("CMD"), scope.query("CMD?"), inst.write(':CMD')
        re.compile(r'''(?:write|query|ask|send|command)\s*\(\s*['"]([:*]?[A-Za-z][A-Za-z0-9:;_\s<>{}|?.*+\-]+)['"]\s*\)''', re.IGNORECASE),
        # Python f-strings: scope.write(f":CH{ch}:SCAle {val}")
        re.compile(r'''(?:write|query|ask|send|command)\s*\(\s*f?['"]([:*]?[A-Za-z][A-Za-z0-9:;_\s<>{}|?.*+\-]+)['"]\s*\)''', re.IGNORECASE),
        # String assignments: cmd = ":CH1:SCAle 0.5"  
        re.compile(r'''=\s*['"](:[A-Za-z][A-Za-z0-9:;_\s<>{}|?.*+\-]+)['"]\s*'''),
        # LabVIEW/C-style: VISA_Write(":CMD arg")
        re.compile(r'''(?:VISA_Write|viWrite|Write|Send)\s*\([^"']*['"]([:*]?[A-Za-z][A-Za-z0-9:;_\s<>{}|?.*+\-]+)['"]\s*''', re.IGNORECASE),
        # Bare SCPI in strings (common in config arrays)
        re.compile(r'''['"]([:*][A-Z][A-Za-z0-9:]+(?:\s+\S+)?)['"]\s*'''),
    ]
    
    for line_num, line in enumerate(lines, 1):
        line_stripped = line.strip()
        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith('#') or line_stripped.startswith('//'):
            continue
        
        for pattern in patterns:
            for match in pattern.finditer(line):
                cmd_raw = match.group(1).strip()
                
                # Clean up: remove trailing quotes, normalize
                cmd_raw = cmd_raw.rstrip('"\'')
                
                # Skip if too short or not SCPI-like
                if len(cmd_raw) < 3:
                    continue
                # Must contain a colon or start with * (IEEE common commands)
                if ':' not in cmd_raw and not cmd_raw.startswith('*'):
                    continue
                
                # Extract just the header (before any argument/value)
                # Split on first space to separate header from argument
                parts = cmd_raw.split(None, 1)
                header = parts[0].strip().rstrip('?')
                is_query = '?' in cmd_raw.split(None, 1)[0]
                argument = parts[1].strip() if len(parts) > 1 else None
                
                # Normalize: strip leading colon for dedup, but preserve for display
                header_norm = header.lstrip(':').upper()
                
                if header_norm not in seen:
                    seen.add(header_norm)
                    commands.append({
                        'line': line_num,
                        'raw': cmd_raw,
                        'header': header,
                        'header_display': header if header.startswith(':') or header.startswith('*') else ':' + header,
                        'is_query': is_query,
                        'argument': argument,
                        'context': line_stripped[:120],
                    })
    
    if not commands:
        return """## SCPI Command Extraction

**No SCPI commands found.**

Make sure the code contains SCPI command strings in quotes, such as:
- `scope.write(":CH1:SCAle 0.5")`
- `scope.query("MEASUrement:MEAS1:RESUlts:CURRentacq:MEAN?")`

If commands are built dynamically or stored in variables, they may not be detected.
Try pasting the actual command strings directly."""
    
    # Categorize commands
    categories = {
        'Horizontal': [], 'Vertical/Channel': [], 'Trigger': [],
        'Measurement': [], 'Cursor': [], 'Display': [], 'Math': [],
        'Acquisition': [], 'Waveform Transfer': [], 'Save/Export': [],
        'Bus/Serial': [], 'DPOJET/Jitter': [], 'IEEE Common': [], 'Other': []
    }
    
    for cmd in commands:
        h = cmd['header_display'].upper()
        if h.startswith('*'):
            categories['IEEE Common'].append(cmd)
        elif any(h.startswith(p) for p in [':HOR', 'HOR']):
            categories['Horizontal'].append(cmd)
        elif any(h.startswith(p) for p in [':CH', 'CH', ':SEL', 'SEL']):
            categories['Vertical/Channel'].append(cmd)
        elif any(h.startswith(p) for p in [':TRIG', 'TRIG']):
            categories['Trigger'].append(cmd)
        elif any(h.startswith(p) for p in [':MEAS', 'MEAS', ':MEA', 'MEA']):
            categories['Measurement'].append(cmd)
        elif any(h.startswith(p) for p in [':CURS', 'CURS']):
            categories['Cursor'].append(cmd)
        elif any(h.startswith(p) for p in [':DISP', 'DISP']):
            categories['Display'].append(cmd)
        elif any(h.startswith(p) for p in [':MATH', 'MATH']):
            categories['Math'].append(cmd)
        elif any(h.startswith(p) for p in [':ACQ', 'ACQ']):
            categories['Acquisition'].append(cmd)
        elif any(h.startswith(p) for p in [':WFM', 'WFM', ':DAT', 'DAT', ':CURV', 'CURV']):
            categories['Waveform Transfer'].append(cmd)
        elif any(h.startswith(p) for p in [':SAV', 'SAV', ':HARD', 'HARD', ':EXP', 'EXP']):
            categories['Save/Export'].append(cmd)
        elif any(h.startswith(p) for p in [':BUS', 'BUS']):
            categories['Bus/Serial'].append(cmd)
        elif any(h.startswith(p) for p in [':DPOJ', 'DPOJ']):
            categories['DPOJET/Jitter'].append(cmd)
        else:
            categories['Other'].append(cmd)
    
    output = f"## SCPI Commands Extracted from Code\n\n"
    output += f"**Total unique commands found:** {len(commands)}\n\n"
    
    for cat_name, cat_cmds in categories.items():
        if not cat_cmds:
            continue
        output += f"### {cat_name} ({len(cat_cmds)} commands)\n\n"
        output += "| # | Command | Query? | Argument | Line |\n"
        output += "|---|---------|--------|----------|------|\n"
        for i, cmd in enumerate(cat_cmds, 1):
            q = "✅" if cmd['is_query'] else ""
            arg = f"`{cmd['argument']}`" if cmd['argument'] else ""
            output += f"| {i} | `{cmd['header_display']}` | {q} | {arg} | {cmd['line']} |\n"
        output += "\n"
    
    output += """---
### Next Steps

1. **Look up each command** with `tek_legacy_command_lookup` to find modern equivalents
2. **Check implicit compatibility** - many commands work as-is on modern scopes
3. **Classify each command:**
   - ✅ **Works as-is** - no translation needed
   - 🔄 **Needs XML translation** - add to PI Translator file
   - ⚠️ **Needs code change** - cannot be handled by PI Translator
4. **Generate XML** with `tek_generate_pi_xml` for commands needing translation
5. **Validate** the XML with `tek_validate_pi_xml`
"""
    return output


@mcp.tool()
@with_flush
def tek_generate_pi_xml(
    source_instrument: str,
    target_instrument: str,
    translations: str
) -> str:
    """Generate a PI Translator XML Compatibility File from translation specifications.
    
    ⚠️ Call `tek_pi_translator_reference()` FIRST to understand the XML syntax!
    
    Args:
        source_instrument: Legacy instrument (e.g., "DPO7104C", "TDS754", "DPO5104")
        target_instrument: Target modern instrument (e.g., "MSO58B", "MSO54B", "MSO56B")
        translations: JSON array of translation objects. Each object has:
            - legacy: Legacy SCPI command (e.g., ":HOR:TRIG:POS")
            - modern: Modern SCPI command or array for one-to-many
            - is_command: true/false (default true)
            - is_query: true/false (default true)  
            - argument_map: Optional dict of {legacy_arg: modern_arg} for sensitiveArgument
            - skip: true if command should be no-op'd (sends linefeed)
            - notes: Optional comment
            
            Example:
            [
                {"legacy": ":HOR:TRIG:POS", "modern": ":HOR:POS"},
                {"legacy": ":HOR:RECORDLENGTH", "modern": [":HOR:MODE MANUAL", ":HOR:RECOrdlength"], "is_query": false},
                {"legacy": ":CH?:IMPedance", "argument_map": {"MEG": ":CH?:TERMination 1E6", "FIFty": ":CH?:TERMination 50"}},
                {"legacy": ":DISplay:SHOWREmote", "skip": true},
                {"legacy": ":ACQ:MODe", "argument_map": {"NORMALSAMPLE": ":ACQ:MODe SAMPLE"}}
            ]
    
    Returns:
        Complete XML file content ready to save as a Compatibility File
    """
    try:
        specs = json.loads(translations)
    except json.JSONDecodeError as e:
        return f"**Error:** Invalid JSON in translations parameter: {e}\n\nMake sure to pass a valid JSON array."
    
    if not isinstance(specs, list):
        return "**Error:** translations must be a JSON array of translation objects."
    
    # Build XML tree
    # We'll group commands by their top-level keyword to create a proper tree
    keyword_tree = {}
    
    for spec in specs:
        legacy = spec.get('legacy', '').strip().lstrip(':')
        if not legacy:
            continue
        
        # Parse legacy command into keyword path
        keywords = legacy.replace(':', ' ').split()
        if not keywords:
            continue
        
        # Store spec at the leaf position
        node = keyword_tree
        for kw in keywords[:-1]:
            if kw not in node:
                node[kw] = {'_children': {}}
            if '_children' not in node[kw]:
                node[kw]['_children'] = {}
            node = node[kw]['_children']
        
        leaf_kw = keywords[-1]
        if leaf_kw not in node:
            node[leaf_kw] = {'_children': {}}
        node[leaf_kw]['_spec'] = spec
    
    def build_xml_node(name, node_data, indent=1):
        """Recursively build XML keyword nodes."""
        lines = []
        tab = '\t' * indent
        spec = node_data.get('_spec')
        children = node_data.get('_children', {})
        
        # Build keyword attributes
        attrs = f'name="{name}"'
        
        has_suffix = '?' in name or name.upper().startswith('CH') and len(name) <= 4
        if has_suffix and '?' not in name:
            # Might need specialSuffix
            pass
        
        if spec:
            is_cmd = spec.get('is_command', True)
            is_qry = spec.get('is_query', True)
            skip = spec.get('skip', False)
            arg_map = spec.get('argument_map')
            modern = spec.get('modern', '')
            notes = spec.get('notes', '')
            
            attrs += ' leaf="1"'
            if is_cmd:
                attrs += ' command="1"'
            if is_qry:
                attrs += ' query="1"'
            if arg_map:
                attrs += ' argument="1"'
            
            # Opening tag
            if notes:
                lines.append(f'{tab}<!-- {notes} -->')
            lines.append(f'{tab}<keyword {attrs}>')
            
            if skip:
                # No-op translation
                lines.append(f'{tab}\t<translation header="&#10;" addedArgument="1"/>')
            elif arg_map:
                # Argument-dependent translations
                entries = list(arg_map.items())
                for i, (legacy_arg, modern_cmd) in enumerate(entries):
                    is_last = (i == len(entries) - 1)
                    modern_cmd = modern_cmd.strip()
                    if not modern_cmd.startswith(':'):
                        modern_cmd = ':' + modern_cmd
                    
                    t_attrs = f'header="{modern_cmd}"'
                    t_attrs += ' addedArgument="1"'
                    t_attrs += f' sensitiveArgument="{legacy_arg}"'
                    if i == 0:
                        t_attrs += ' sendInQuery="1"'
                    else:
                        t_attrs += ' sendInQuery="0"'
                    
                    lines.append(f'{tab}\t<translation {t_attrs}/>')
            elif isinstance(modern, list):
                # One-to-many translation
                for i, mod_cmd in enumerate(modern):
                    is_last = (i == len(modern) - 1)
                    mod_cmd = mod_cmd.strip()
                    if not mod_cmd.startswith(':') and not mod_cmd.startswith('*'):
                        mod_cmd = ':' + mod_cmd
                    
                    # Check if the modern command has a baked-in argument (e.g., ":HOR:MODE MANUAL")
                    has_baked_arg = ' ' in mod_cmd
                    
                    t_attrs = f'header="{mod_cmd}"'
                    if has_baked_arg:
                        t_attrs += ' addedArgument="1"'
                    if not is_last:
                        # Intermediate: reuse suffix if present, don't send in query
                        if '?' in name or has_suffix:
                            t_attrs += ' reuseSuffix="1"'
                        t_attrs += ' sendInQuery="0"'
                    
                    lines.append(f'{tab}\t<translation {t_attrs}/>')
            else:
                # Simple one-to-one
                mod_cmd = modern.strip() if modern else ''
                if mod_cmd and not mod_cmd.startswith(':') and not mod_cmd.startswith('*'):
                    mod_cmd = ':' + mod_cmd
                
                if mod_cmd:
                    has_baked_arg = ' ' in mod_cmd
                    t_attrs = f'header="{mod_cmd}"'
                    if has_baked_arg:
                        t_attrs += ' addedArgument="1"'
                    if '?' in name:
                        t_attrs += ' reuseSuffix="1"'
                    lines.append(f'{tab}\t<translation {t_attrs}/>')
            
            # Add child keywords if any
            for child_name, child_data in children.items():
                lines.extend(build_xml_node(child_name, child_data, indent + 1))
            
            lines.append(f'{tab}</keyword>')
        else:
            # Intermediate node (not a leaf)
            if '?' in name:
                attrs += ' specialSuffix="1"'
            lines.append(f'{tab}<keyword {attrs}>')
            for child_name, child_data in children.items():
                lines.extend(build_xml_node(child_name, child_data, indent + 1))
            lines.append(f'{tab}</keyword>')
        
        return lines
    
    # Generate XML
    xml_lines = [
        "<?xml version='1.0' encoding='utf-8'?>",
        f"<!-- PI Translator Compatibility File",
        f"     Source: {source_instrument}",
        f"     Target: {target_instrument}",
        f"     Generated by Tektronix MCP Server",
        f"     ",
        f"     Enable with: COMPatibility:ENABLE 1",
        f"     Verify with: BATman \"v1.0\" then *ESR? (should return 0)",
        f"-->",
        "",
        "<translations version='0.5'>",
        "",
    ]
    
    # Add debug entry
    xml_lines.append('\t<!-- Debug: verify file loaded -->')
    xml_lines.append('\t<keyword name="BATman" leaf="1" command="1" query="1">')
    xml_lines.append('\t\t<translation header="callouts:callout1:text"/>')
    xml_lines.append('\t</keyword>')
    xml_lines.append('')
    
    # Add all translations grouped by top-level keyword
    for top_name, top_data in keyword_tree.items():
        xml_lines.extend(build_xml_node(top_name, top_data, 1))
        xml_lines.append('')
    
    xml_lines.append("</translations>")
    
    xml_content = '\n'.join(xml_lines)
    
    output = f"## Generated PI Translator File: {source_instrument} → {target_instrument}\n\n"
    output += f"**Translations:** {len(specs)} command mappings\n\n"
    output += "```xml\n"
    output += xml_content
    output += "\n```\n\n"
    output += f"""### Deployment Instructions

1. Save as `Compatibility_{source_instrument}_to_{target_instrument}.xml`
2. Copy to the scope:
   - **Linux:** `C:/PICompatibility/`
   - **Windows:** `C:\\Users\\Public\\Tektronix\\TekScope\\PICompatibility\\`
3. Enable via UI: **Utility → User Preferences → Other → Programmatic Interface Backward Compatibility → On**
4. Or via SCPI: `COMPatibility:ENABLE 1`
5. Load your file via the **Load** button in User Preferences
6. **Verify:** Send `BATman "v1.0"` then `*ESR?` — should return 0

### Validation
Run `tek_validate_pi_xml` with this XML content to check for common issues.
"""
    
    return output


@mcp.tool()
@with_flush
def tek_validate_pi_xml(xml_content: str) -> str:
    """Validate a PI Translator XML Compatibility File for common errors.
    
    Checks for:
    - Valid XML syntax
    - Required attributes on leaf keywords
    - Missing countOfArguments when reuseArgument is used
    - UPPERlower format issues
    - Missing translations on leaf nodes
    - sendInQuery issues in one-to-many translations
    
    Args:
        xml_content: The XML content of the Compatibility File (paste directly)
    
    Returns:
        Validation report with errors, warnings, and suggestions
    """
    errors = []
    warnings = []
    info = []
    
    # 1. Check XML syntax
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return f"""## PI Translator XML Validation: ❌ FAILED

**XML Parse Error:** {e}

The XML is not well-formed. Common causes:
- Unclosed tags (missing `</keyword>`)
- Unescaped special characters (use `&amp;` for &, `&lt;` for <, `&#10;` for linefeed)
- Mismatched quotes in attributes
- Missing closing `</translations>` tag

Fix the XML syntax and try again."""
    
    if root.tag != 'translations':
        errors.append("Root element should be `<translations>`, found `<{root.tag}>`")
    
    # 2. Recursive validation of keyword tree
    translation_count = 0
    leaf_count = 0
    
    def validate_keyword(elem, path=""):
        nonlocal translation_count, leaf_count
        
        name = elem.get('name', '(unnamed)')
        current_path = f"{path}:{name}" if path else name
        is_leaf = elem.get('leaf') == '1'
        is_cmd = elem.get('command') == '1'
        is_qry = elem.get('query') == '1'
        has_argument = elem.get('argument') == '1'
        
        # Check name format (should have some uppercase)
        if name != '?' and not name.startswith('*') and not name.startswith('&#'):
            has_upper = any(c.isupper() for c in name)
            if not has_upper and len(name) > 1:
                warnings.append(f"`{current_path}`: keyword name `{name}` has no uppercase chars. Use UPPERlower format (e.g., `HORizontal`)")
        
        if is_leaf:
            leaf_count += 1
            translations = elem.findall('translation')
            child_keywords = elem.findall('keyword')
            
            # Leaf must have at least one translation
            if not translations and not child_keywords:
                errors.append(f"`{current_path}`: leaf keyword has NO translation entries")
            
            # If leaf has neither command="1" nor query="1", it won't do anything
            if not is_cmd and not is_qry:
                warnings.append(f"`{current_path}`: leaf has neither command=\"1\" nor query=\"1\" — won't respond to commands or queries")
            
            # Validate translations
            has_sensitive = False
            query_senders = 0
            
            for i, trans in enumerate(translations):
                translation_count += 1
                header = trans.get('header', '')
                
                if not header:
                    errors.append(f"`{current_path}` translation #{i+1}: missing `header` attribute")
                    continue
                
                # Check reuseArgument requires countOfArguments
                reuse_arg = trans.get('reuseArgument') == '1'
                count_args = trans.get('countOfArguments')
                if reuse_arg and not count_args:
                    errors.append(f"`{current_path}` translation #{i+1}: `reuseArgument=\"1\"` REQUIRES `countOfArguments` attribute!")
                
                # Check sendInQuery tracking
                send_in_query = trans.get('sendInQuery', '1')
                if send_in_query != '0':
                    query_senders += 1
                
                # Check sensitiveArgument
                if trans.get('sensitiveArgument'):
                    has_sensitive = True
                
                # Check header format
                if header != '&#10;' and not header.startswith(':') and not header.startswith('*') and not header.startswith('callout'):
                    warnings.append(f"`{current_path}` translation #{i+1}: header `{header}` doesn't start with colon. Recommended: `:{header}`")
            
            # Multiple translations sending in query = potential issue
            if len(translations) > 1 and query_senders > 1 and is_qry:
                warnings.append(f"`{current_path}`: {query_senders} translations send in query mode. Usually only 1 should have `sendInQuery=\"1\"`, others `sendInQuery=\"0\"`")
            
            # argument="1" but no sensitiveArgument translations
            if has_argument and not has_sensitive:
                info.append(f"`{current_path}`: has `argument=\"1\"` but no `sensitiveArgument` translations. Is `reuseArgument` or `addedArgument` being used instead?")
        
        else:
            # Non-leaf: should have child keywords
            children = elem.findall('keyword')
            translations = elem.findall('translation')
            if not children and not translations:
                warnings.append(f"`{current_path}`: non-leaf keyword with no children or translations. Orphaned node?")
        
        # Recurse into children
        for child in elem.findall('keyword'):
            validate_keyword(child, current_path)
    
    for child in root.findall('keyword'):
        validate_keyword(child)
    
    # Build report
    status = "✅ PASSED" if not errors else "❌ ISSUES FOUND"
    
    output = f"## PI Translator XML Validation: {status}\n\n"
    output += f"**Summary:** {leaf_count} leaf commands, {translation_count} translations\n\n"
    
    if errors:
        output += f"### ❌ Errors ({len(errors)})\n\n"
        for e in errors:
            output += f"- {e}\n"
        output += "\n"
    
    if warnings:
        output += f"### ⚠️ Warnings ({len(warnings)})\n\n"
        for w in warnings:
            output += f"- {w}\n"
        output += "\n"
    
    if info:
        output += f"### ℹ️ Info ({len(info)})\n\n"
        for i in info:
            output += f"- {i}\n"
        output += "\n"
    
    if not errors and not warnings:
        output += "**No issues found!** The XML structure looks correct.\n\n"
    
    output += """### Deployment Testing Checklist
1. Copy file to scope's PICompatibility directory
2. Enable PI Translator: `COMPatibility:ENABLE 1`
3. Load your file via Utility → User Preferences → Other → Load
4. Send `BATman "test"` then `*ESR?` → should return 0
5. Test each translated command and verify with `*ESR?` after each
6. Compare query responses between legacy and modern scope
"""
    
    return output
