# Legacy to Modern SCPI Command Migration Guide

## Overview

This guide helps you migrate automation code from legacy Tektronix oscilloscopes to modern instruments:

**Legacy Instruments** (source code):
- TDS Series (TDS754, TDS784, TDS7xx4, etc.) - oldest generation
- MSO/DPO 5000/5000B Series
- DPO 7000/7000C Series  
- MSO/DPO 70000 Series (70000B/C/D/DX/SX)
- DSA 70000 Series
- MSO 4/5/6 Series (earlier firmware)

**Modern Instruments** (target):
- DPO 7 Series (DPO714A, DPO714AX, DPO718A, DPO718AX)
- MSO 4/5/6 Series (current firmware)
- MSO 2 Series
- MSO58LP, LPD64

## Migration Approaches

There are two ways to migrate legacy automation code:

| Approach | Best For | Pros | Cons |
|----------|----------|------|------|
| **Code Updates** | New projects, maintainable code | Cleaner, faster, fewer failure points | Requires code access and testing |
| **PI Translator** | Locked-down systems, quick fixes | No code changes needed | Adds complexity, slight performance hit |

**Code updates are nearly always the better solution** because they have fewer points of potential failure, run faster, and are generally cleaner. However, the PI Translator is valuable when:

- You lack tools, resources, or authorization to modify code
- Aerospace/defense test systems with 20-30 year software approval cycles
- Quick proof-of-concept before full migration
- Only a few commands need translation

---

## Part 1: Built-in Backwards Compatibility

The DPO 7 Series and modern MSO oscilloscopes have **implicit backwards compatibility**. Many legacy commands are automatically translated by the instrument firmware. Your existing code may work without modification!

However, for best results and future maintainability, we recommend updating to modern command syntax.

---

## Part 2: Code-Based Migration

### Major Structural Changes

#### 1. Display Namespace Reorganization

The biggest change is that many display-related settings moved into the \`DISplay:WAVEView<n>\` namespace:

| What Changed | Legacy | Modern |
|-------------|--------|--------|
| Math position | \`:MATH:MATH1:POSITION\` | \`:DISplay:WAVEView1:MATH:MATH1:VERTical:POSition\` |
| Math scale | \`:MATH:MATH1:SCAle\` | \`:DISplay:WAVEView1:MATH:MATH1:VERTical:SCAle\` |
| Reference position | \`:REF:REF1:POSITION\` | \`:DISplay:WAVEView1:REF:REF1:VERTical:POSition\` |
| Cursor commands | \`:CURSor:*\` | \`:DISplay:WAVEView1:CURSor:CURSOR:*\` |
| Zoom commands | \`:ZOOm:*\` | \`:DISplay:WAVEView1:ZOOM:ZOOM1:*\` |

**Note**: \`WAVEView1\` is the default view. Use \`WAVEView2\`, etc. for multi-view setups.

#### 2. Waveform State Moved to GLObal

Turning waveforms on/off now uses \`DISplay:GLObal\`:

| Legacy | Modern |
|--------|--------|
| \`:CH1:STATE ON\` | \`:DISplay:GLObal:CH1:STATE ON\` |
| \`:MATH:MATH1:STATE ON\` | \`:DISplay:GLObal:MATH1:STATE ON\` |
| \`:REF:REF1:STATE ON\` | \`:DISplay:GLObal:REF1:STATE ON\` |
| \`:BUS:B1:STATE ON\` | \`:DISplay:GLObal:B1:STATE ON\` |

#### 3. Simplified Horizontal Commands

Many horizontal commands were simplified by removing intermediate nodes:

| Legacy | Modern |
|--------|--------|
| \`:HORizontal:MODe:SCAle\` | \`:HORizontal:SCAle\` |
| \`:HORizontal:MAIn:POSition\` | \`:HORizontal:POSition\` |
| \`:HORizontal:DELay:POSition\` | \`:HORizontal:POSition\` |
| \`:HORizontal:MODe:SAMPLERate\` | \`:HORizontal:SAMPLERate\` |
| \`:HORizontal:MODe:RECOrdlength\` | \`:HORizontal:RECOrdlength\` |
| \`:HORizontal:ACQLENGTH\` | \`:HORizontal:RECOrdlength\` |
| \`:CH1:VOLTS\` | \`:CH1:SCAle\` |

#### 4. DPOJET Commands Moved to Standard Namespaces

DPOJET jitter analysis commands moved to \`MEASUrement\` and \`PLOT\`:

| Legacy | Modern |
|--------|--------|
| \`:DPOJET:GATing\` | \`:MEASUrement:MEAS1:GATing\` |
| \`:DPOJET:DIRacmodel\` | \`:MEASUrement:DIRacmodel\` |
| \`:DPOJET:JITTermodel\` | \`:MEASUrement:JITTermodel\` |
| \`:DPOJET:MINBUJUI\` | \`:MEASUrement:MINUI\` |
| \`:DPOJET:PLOT1:SPECtrum:*\` | \`:PLOT:PLOT1:SPECtrum:*\` |

#### 5. Bus Command Standardization

Serial bus commands were standardized with consistent naming:

| Bus | Legacy | Modern |
|-----|--------|--------|
| I2C | \`:BUS:B1:I2C:SCLk:SOUrce\` | \`:BUS:B1:I2C:CLOCk:SOUrce\` |
| I3C | \`:BUS:B1:I3C:SDAta:SOUrce\` | \`:BUS:B1:I3C:DATa:SOUrce\` |
| SPI | \`:BUS:B1:SPI:SCLk:SOUrce\` | \`:BUS:B1:SPI:CLOCk:SOUrce\` |
| SPI | \`:BUS:B1:SPI:MOSi:INPut\` | \`:BUS:B1:SPI:DATa:SOUrce\` |
| SPI | \`:BUS:B1:SPI:SS:SOUrce\` | \`:BUS:B1:SPI:SELect:SOUrce\` |
| USB | \`:BUS:B1:USB:SOUrce:DIFFerential\` | \`:BUS:B1:USB:SOUrce\` |

#### 6. Trigger Command Changes

| Legacy | Modern |
|--------|--------|
| \`:TRIGger:A:PULse:WIDth:WHEn\` | \`:TRIGger:A:PULSEWidth:WHEn\` |
| \`:TRIGger:A:PULse:RUNT:WHEn\` | \`:TRIGger:A:RUNT:WHEn\` |
| \`:TRIGger:A:RISEFall:SOUrce\` | \`:TRIGger:A:TRANsition:SOUrce\` |
| \`:TRIGger:A:WINdow:POLarity\` | \`:TRIGger:A:WINdow:CROSSIng\` |

#### 7. Vertical/Probe Commands

| Legacy (TDS/DPO7000) | Modern |
|---------------------|--------|
| \`:CH1:IMPedance MEG\` | \`:CH1:TERMination 1E6\` |
| \`:CH1:IMPedance FIFty\` | \`:CH1:TERMination 50\` |
| \`:CH1:PROBE?\` | \`:CH1:PROBEFunc:EXTAtten?\` |
| \`:CH1:BANdwidth TWO\` | \`:CH1:BANdwidth 250E6\` |

---

## Part 3: PI Translator (Hardware-Based Translation)

### What is the PI Translator?

The PI Translator is a feature built into modern Tektronix oscilloscopes (firmware v1.30+) that intercepts incoming SCPI commands and translates them to modern equivalents before processing. It acts as a "dictionary" between legacy and modern command sets.

```
Host Application → VISA → [PI Translator] → Command Processor
                           ↑
                    Intercepts & translates
                    legacy commands
```

### Supported Oscilloscopes

- 2 Series MSO
- 4 Series MSO  
- 5 Series MSO / 5 Series B MSO
- 6 Series MSO / 6 Series B MSO
- MSO58LP
- LPD64

### Enabling the PI Translator

**Method 1: Via Scope UI**
1. Tap **Utility** menu
2. Select **User Preferences → Other**
3. Enable **"Programmatic Interface Backward Compatibility"**
4. Use **Load** button to select a custom Compatibility File

**Method 2: Via SCPI Command**
\`\`\`
COMPatibility:ENABLE 1
\`\`\`

### Compatibility File Locations

| Operating System | Default Path |
|-----------------|--------------|
| Embedded Linux | \`C:/PICompatibility/Compatibility.xml\` |
| Windows | \`C:\\Users\\Public\\Tektronix\\TekScope\\PICompatibility\\Compatibility.xml\` |

### Creating Custom Translations

The PI Translator uses XML files to define command mappings. We recommend:
1. Copy the default \`Compatibility.xml\` to a new file
2. Add your custom translations
3. Load the new file via the scope UI

**Recommended editor**: Notepad++ (free, open-source)

### XML Structure Overview

\`\`\`xml
<?xml version='1.0' encoding='utf-8'?>
<translations version='0.5'>
    
    <!-- Simple one-to-one translation -->
    <keyword name="HARDCOPY" leaf="1" command="1">
        <keyword name='FILENAME' leaf="1" command="1" query="1">
            <translation header=':SAVe:IMAGe:FULLPath'/>
        </keyword>
    </keyword>
    
</translations>
\`\`\`

### Keyword Attributes

| Attribute | Description |
|-----------|-------------|
| \`name\` | Keyword name in UPPERlower format (uppercase = short form) |
| \`leaf="1"\` | This is the end of a command (has translation) |
| \`command="1"\` | Valid as a set command |
| \`query="1"\` | Valid as a query (?) |
| \`argument="1"\` | Translation depends on the argument value |
| \`specialSuffix="1"\` | Suffix (like channel number) affects translation |

### Translation Attributes

| Attribute | Description |
|-----------|-------------|
| \`header\` | The modern command to substitute |
| \`addedArgument="1"\` | Header includes a fixed argument |
| \`sensitiveArgument="VAL"\` | Use this translation when argument matches |
| \`reuseSuffix="1"\` | Preserve suffix for next translation |
| \`reuseArgument="1"\` | Preserve argument for next translation |
| \`countOfArguments="1"\` | Number of arguments to preserve |
| \`sendInQuery="0"\` | Don't send this in query form |
| \`delyDuration="100"\` | Add delay (ms) after command |

### Translation Examples

#### Example 1: Simple One-to-One
\`\`\`xml
<!-- HOR:TRIG:POS → HOR:POS -->
<keyword name="HORizontal">
    <keyword name="TRIGger">
        <keyword name="POSition" leaf="1" command="1" query="1">
            <translation header=":HORizontal:POSition"/>
        </keyword>
    </keyword>
</keyword>
\`\`\`

#### Example 2: One-to-Many (Single command triggers multiple)
\`\`\`xml
<!-- HOR:RECORDLENGTH → set manual mode, then set record length -->
<keyword name="HORizontal">
    <keyword name="RECOrdlength" leaf="1" command="1" argument="1" query="1">
        <translation header=":HORizontal:MODE MANUAL" addedArgument="1"/>
        <translation header=":HORizontal:RECOrdlength"/>
    </keyword>
</keyword>
\`\`\`

#### Example 3: Argument-Dependent Translation
\`\`\`xml
<!-- CH1:IMPedance MEG → CH1:TERMination 1E6 -->
<!-- CH1:IMPedance FIFty → CH1:TERMination 50 -->
<keyword name='CH1' specialSuffix='1'>
    <keyword name="IMPedance" leaf="1" command="1" query="1" argument="1">
        <translation header=":CH1:TERMination 1E6" addedArgument='1' 
                     sensitiveArgument="MEG" sendInQuery="1"/>
        <translation header=":CH1:TERMination 50" addedArgument='1' 
                     sensitiveArgument="FIFty" sendInQuery="0"/>
    </keyword>
</keyword>
\`\`\`

#### Example 4: Global Setting to Per-Channel
\`\`\`xml
<!-- Legacy: TRIGGER:A:LEVEL 0.5 (sets all channels) -->
<!-- Modern: Must set each channel individually -->
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
\`\`\`

#### Example 5: Skip Unnecessary Commands
\`\`\`xml
<!-- DISplay:SHOWREmote no longer needed - send linefeed only -->
<keyword name='DISplay'>
    <keyword name='SHOWREmote' leaf="1" command="1" argument="1">
        <translation header="&#10;" addedArgument="1"/>
    </keyword>
</keyword>
\`\`\`

### Debugging PI Translator Files

Include debug commands to verify your file loads correctly:

\`\`\`xml
<!-- Send "BATman" to verify file is loaded - displays text on scope -->
<keyword name="BATman" leaf="1" command="1" query="1">
    <translation header='callouts:callout1:text'/>
</keyword>
\`\`\`

After loading your file, send:
\`\`\`
BATman "Hello World"
*ESR?
\`\`\`
If \`*ESR?\` returns 0 and you see the callout, your file loaded successfully.

### Real-World Examples

Two example PI Translator files are included in the reference folder:

| File | Source → Target | Use Case |
|------|-----------------|----------|
| \`Compatibility_TDS754_to_MSO54B.xml\` | TDS754 → MSO54B | Very old TDS scope migration |
| \`Compatibility_DPO7104C_to_MSO58B.xml\` | DPO7104C → MSO58B | Nvidia customer migration |

---

## Common Pitfalls

### 1. WAVEView Index
Modern commands often require specifying \`WAVEView1\`:
\`\`\`
# Wrong (may fail)
:DISplay:CURSor:STATE ON

# Correct
:DISplay:WAVEView1:CURSor:CURSOR:STATE ON
\`\`\`

### 2. GLObal vs WAVEView
- Use \`GLObal\` for turning waveforms on/off (visibility)
- Use \`WAVEView<n>\` for display properties (scale, position, cursors)

### 3. Horizontal Mode
Setting record length on modern scopes often requires manual mode:
\`\`\`
:HORizontal:MODe MANUAL
:HORizontal:RECOrdlength 10000000
\`\`\`

### 4. Argument Value Changes
Some arguments changed spelling:
| Legacy | Modern |
|--------|--------|
| \`STAYHigh\` | \`STAYSHigh\` |
| \`STAYLow\` | \`STAYSLow\` |
| \`NORMALSAMPLE\` | \`SAMPLE\` |

---

## Quick Reference Card

| Function | Modern Command |
|----------|---------------|
| Set timebase | \`:HORizontal:SCAle <NR3>\` |
| Set record length | \`:HORizontal:MODe MANUAL\` then \`:HORizontal:RECOrdlength <NR1>\` |
| Set sample rate | \`:HORizontal:SAMPLERate <NR3>\` |
| Set vertical scale | \`:CH1:SCAle <NR3>\` |
| Set termination | \`:CH1:TERMination {50|1E6}\` |
| Turn channel on | \`:DISplay:GLObal:CH1:STATE ON\` |
| Set cursor position | \`:DISplay:WAVEView1:CURSor:CURSOR:VBArs:APOSition <NR3>\` |
| Set math scale | \`:DISplay:WAVEView1:MATH:MATH1:VERTical:SCAle <NR3>\` |

---

## Resources

### Programmer Manuals
- [DPO 7 Series](https://www.tek.com/en/manual/7-series-dpo-programmer-manual-7-series-dpo)
- [MSO 4/5/6 Series](https://www.tek.com/en/manual/oscilloscope/4-5-6-series-mso-programmer-manual-5-series-mso-low-profile)
- [MSO/DPO 5000/7000/70000](https://www.tek.com/en/manual/oscilloscope/dpo70000sx-msodpo70000dx-msodpo70000c-dpo7000c-mso5000b-and-dpo5000b-series-programmer-manualmso5000)

### PI Translator Documentation
- PI Command Translator Technical Brief (48W-73775-1) - included in reference folder

### MCP Tools
- \`tek_legacy_command_lookup\` - Find modern equivalent of a legacy command
- \`tek_search_commands\` - Search for commands by keyword
- \`tek_comprehensive_search\` - Full documentation search

---

*Last updated: February 2025*
