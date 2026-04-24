# PI Translator XML Syntax Reference

## Overview

The PI (Programmatic Interface) Translator is built into modern Tektronix oscilloscopes 
(firmware v1.30+). It intercepts legacy SCPI commands and translates them to modern 
equivalents before processing. Translations are defined in XML Compatibility Files.

**Supported Oscilloscopes:**
- 2 Series MSO
- 4 Series MSO
- 5 Series MSO / 5 Series B MSO
- 6 Series MSO / 6 Series B MSO
- MSO58LP
- LPD64

## Migration Approaches

| Approach | Best For | Pros | Cons |
|----------|----------|------|------|
| **Code Updates** | New projects, maintainable code | Cleaner, faster, fewer failure points | Requires code access and testing |
| **PI Translator** | Locked-down systems, quick fixes | No code changes needed | Adds complexity, slight performance hit |

**Code updates are nearly always the better solution.** The PI Translator is valuable when:
- Aerospace/defense systems with 20-30 year software approval cycles
- No authorization to modify existing test code
- Quick proof-of-concept before full migration

## Enabling the PI Translator

### Via Scope UI
1. Tap **Utility** menu
2. Select **User Preferences → Other**
3. Enable **"Programmatic Interface Backward Compatibility"**
4. Use **Load** button to select a custom Compatibility File

### Via SCPI Command
```
COMPatibility:ENABLE 1
```

### File Locations
| OS | Default Path |
|----|-------------|
| Embedded Linux | `C:/PICompatibility/Compatibility.xml` |
| Windows | `C:\Users\Public\Tektronix\TekScope\PICompatibility\Compatibility.xml` |

---

## ⚠️ CRITICAL: Silent Failure

**The PI Translator has NO error reporting.** If there is a single XML syntax error anywhere in the file, the ENTIRE file silently fails — no commands are translated, no error is shown, and the toggle will still appear ON. This makes debugging very difficult without deliberate verification strategies (see the Debugging section below).

---

## XML File Structure

### Mandatory File Skeleton

Always use this exact structure:

```xml
<?xml version='1.0' encoding='utf-8'?>
<translations version='0.5'>
    <!-- keyword/translation entries go here -->
</translations>
```

### Critical Structure Rules

1. **Root element MUST be `<translations version='0.5'>`** — NOT `<compatibility>`. Using `<compatibility>` causes the PI Translator to silently reject the entire file. The Tech Brief PDF incorrectly references `<compatibility>` — the actual working files use `<translations version='0.5'>`. Discovered by comparing against working reference file `Compatibility_TDS754_to_MSO54B.xml`.

2. **The `<?xml version='1.0' encoding='utf-8'?>` declaration is required.** Do not omit it.

3. **Use single quotes for all attribute values.** The XML parser may accept double quotes, but single quotes match the reference format and are the safe choice.

4. **No non-ASCII characters anywhere in the file** — not even in XML comments. Em dashes, right arrows, curly quotes, and other non-ASCII characters cause the file to be silently rejected, even though Python's `xml.etree` will parse them without error. Keep all content pure ASCII.

### Minimal Working Example

```xml
<?xml version='1.0' encoding='utf-8'?>
<translations version='0.5'>
    <keyword name='BATman' leaf='1' command='1' query='1'>
        <translation header='callouts:callout1:text'/>
    </keyword>
    <keyword name='HORizontal'>
        <keyword name='RECOrdlength' leaf='1' command='1' query='1'>
            <translation header=':HORizontal:RECOrdlength'/>
        </keyword>
    </keyword>
</translations>
```

---

## Keyword Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `name` | **YES** | — | Keyword in UPPERlower format. Uppercase portion = valid short form. Use `?` as a wildcard for any trailing instance number (CH?, MEAS?, REF?). |
| `leaf` | No | 0 | Marks this keyword as a valid end-of-command node. Must have at least one `<translation>` child. |
| `command` | No | 0 | Accepts set commands (with argument). |
| `query` | No | 0 | Accepts query form (?). |
| `argument` | No | 0 | Translation behavior depends on argument value. Pair with `sensitiveArgument` on child translations. |
| `specialSuffix` | No | 0 | The matched suffix digit (from a specific named keyword like `CH4`) is available for substitution in translation headers. **NOT a wildcard** — see Instance-Numbered Keywords below. |

---

## Instance-Numbered Keywords: `?` vs `specialSuffix`

This is one of the most common sources of errors in generated PI Translator files.

### `?` in keyword name = wildcard (matches any instance number)

```xml
<keyword name='CH?'>     <!-- matches CH1, CH2, CH3, CH4, ... -->
<keyword name='MEAS?'>   <!-- matches MEAS1, MEAS2, MEAS3, ... -->
<keyword name='REF?'>    <!-- matches REF1, REF2, ... -->
<keyword name='MATH?'>   <!-- matches MATH1, MATH2, ... -->
<keyword name='CH?_D?'>  <!-- matches CH1_D0, CH1_D1, CH2_D0, ... -->
<keyword name='CH?_DALL'><!-- matches CH1_DALL, CH2_DALL, ... -->
<keyword name='DIGGRP?'> <!-- matches DIGGRP1 through DIGGRP8 -->
```

The `?` in the keyword name also passes the matched suffix through to translation headers that contain `?`:

```xml
<keyword name='MEAS?'>
    <keyword name='TYPe' leaf='1' command='1' query='1'>
        <translation header=':MEASUrement:MEAS?:TYPe'/>
        <!-- the ? in the header is replaced with the matched number, e.g. MEAS1 -> :MEASUrement:MEAS1:TYPe -->
    </keyword>
</keyword>
```

### `specialSuffix="1"` = specific instance, suffix available for reuse

`specialSuffix` is for targeting a **specific named instance** where the suffix digit needs to appear in the translation header. It is **not** a wildcard — it does not match CH1, CH2, etc. from a generic keyword.

```xml
<!-- CORRECT: specific instance CH4, suffix "4" available in translation header -->
<keyword name='CH4' specialSuffix='1'>
    <translation header=':CH4:BANdwidth'/>
</keyword>

<!-- WRONG: does NOT wildcard-match CH1, CH2, CH3, etc. -->
<keyword name='CH' specialSuffix='1'>   <!-- only matches literal "CH" -->
```

**Rule:** Use `?` in the keyword name for wildcards. Use `specialSuffix='1'` only when writing a translation for a specific instance where the suffix digit needs to appear in the translation header.

---

## Translation Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `header` | **YES** | — | Modern command to send. Use `?` where the suffix should be substituted. Lead with colon. |
| `addedArgument` | No | 0 | The header already includes its own argument. No additional argument is appended from the incoming command. |
| `sensitiveArgument` | No | — | Apply this translation ONLY when the incoming argument matches this value. A translation with no `sensitiveArgument` is the default/fallback and fires when no sensitive match is found. |
| `reuseSuffix` | No | 0 | Preserve the matched suffix for the NEXT translation in a one-to-many sequence. |
| `reuseArgument` | No | 0 | Preserve the incoming argument for the NEXT translation. **Must be paired with `countOfArguments`**. |
| `countOfArguments` | No | — | Number of arguments to preserve when using `reuseArgument`. Always set to `"1"` unless multiple arguments are being passed. |
| `sendInQuery` | No | 1 | Set to `0` to exclude this translation from the query form. In one-to-many sequences, only ONE translation should send in query mode. |
| `delyDuration` | No | — | Add a delay (ms) after sending this command. |

---

## Critical Rules

1. **Root element:** Must be `<translations version='0.5'>` — never `<compatibility>`
2. **XML declaration required:** `<?xml version='1.0' encoding='utf-8'?>` — with single quotes
3. **ASCII only:** No em dashes, arrows, curly quotes, or any non-ASCII in any part of the file
4. **UPPERlower format:** `HORizontal` means `HOR` is the valid short form
5. **`?` for wildcards:** Use in keyword name to match any suffix number — `CH?`, `MATH?`, `MEAS?`
6. **`specialSuffix` is NOT a wildcard:** It is only for specific named instances
7. **Header colon:** Translation headers should lead with a colon
8. **`reuseArgument` requires `countOfArguments`:** Always pair these — `countOfArguments="1"` in most cases
9. **`sendInQuery` in one-to-many:** Only ONE translation per leaf should have `sendInQuery` active
10. **`sensitiveArgument` fallback:** A translation with no `sensitiveArgument` = default; fires when no sensitive match is found
11. **`&#10;` for no-op:** XML newline character with `addedArgument="1"` silently skips a command
12. **Scatter debug keywords:** Place BATman, TURNChannels, and ROBIN at the beginning, middle, and end of the file to localize syntax errors

---

## Translation Patterns

### Pattern 1: Simple One-to-One

```xml
<keyword name='HORizontal'>
    <keyword name='TRIGger'>
        <keyword name='POSition' leaf='1' command='1' query='1'>
            <translation header=':HORizontal:POSition'/>
        </keyword>
    </keyword>
</keyword>
```

### Pattern 2: One-to-Many

One incoming command fires multiple modern commands in sequence. Only the last translation handles the query form.

```xml
<keyword name='HORizontal'>
    <keyword name='RECOrdlength' leaf='1' command='1' argument='1' query='1'>
        <translation header=':HORizontal:MODe MANUAL' addedArgument='1' sendInQuery='0'/>
        <translation header=':HORizontal:RECOrdlength'/>
    </keyword>
</keyword>
```

### Pattern 3: Argument-Dependent (sensitiveArgument + default fallback)

```xml
<keyword name='CH?' specialSuffix='1'>
    <keyword name='IMPedance' leaf='1' command='1' query='1' argument='1'>
        <translation header=':CH?:TERMination 1E6' addedArgument='1'
                     sensitiveArgument='MEG' sendInQuery='1'/>
        <translation header=':CH?:TERMination 50' addedArgument='1'
                     sensitiveArgument='FIFty' sendInQuery='0'/>
    </keyword>
</keyword>
```

### Pattern 4: One-to-Many with reuseArgument (broadcast argument to multiple targets)

Used when a single incoming argument (e.g., a voltage level or ON/OFF) must be forwarded to multiple modern commands. `reuseArgument="1"` and `countOfArguments="1"` must be paired on every translation except the last one.

```xml
<keyword name='TRIGger'>
    <keyword name='?'>
        <keyword name='LEVel' leaf='1' command='1' query='0'>
            <translation header=':trigger:?:level:ch1' reuseSuffix='1'
                         reuseArgument='1' countOfArguments='1'/>
            <translation header=':trigger:?:level:ch2' reuseSuffix='1'
                         reuseArgument='1' countOfArguments='1'/>
            <translation header=':trigger:?:level:ch3' reuseSuffix='1'
                         reuseArgument='1' countOfArguments='1'/>
            <translation header=':trigger:?:level:ch4'/>
        </keyword>
    </keyword>
</keyword>
```

### Pattern 5: Skip Command (No-op)

Silently absorbs a legacy command without sending anything to the scope.

```xml
<keyword name='DISplay'>
    <keyword name='SHOWREmote' leaf='1' command='1' argument='1'>
        <translation header='&#10;' addedArgument='1'/>
    </keyword>
</keyword>
```

### Pattern 6: Debug Verification Keywords (BATman / TURNChannels / ROBIN)

These are top-level keywords that do not interfere with real translations. Place them at the beginning, middle, and end of the file to localize syntax errors.

**BATman** (by Greg Richtenburg) — simplest file load check. Writes text to an on-screen callout:
```xml
<keyword name='BATman' leaf='1' command='1' query='1'>
    <translation header='callouts:callout1:text'/>
</keyword>
```
Send: `BATman "hello"` — if a callout appears, the file loaded and parsed correctly up to this point.

**TURNChannels** — tests one-to-many and reuseArgument:
```xml
<keyword name='TURNChannels' leaf='1' command='1' argument='1'>
    <translation header=':SEL:CH1' reuseArgument='1' countOfArguments='1'/>
    <translation header=':SEL:CH2' reuseArgument='1' countOfArguments='1'/>
    <translation header=':SEL:CH3' reuseArgument='1' countOfArguments='1'/>
    <translation header=':SEL:CH4' reuseArgument='1' countOfArguments='1'/>
    <translation header=':callouts:callout1:text "Channels 1-4 are ON"'
                 addedArgument='1' sensitiveArgument='ON'/>
</keyword>
```
Send: `TURNChannels ON` — turns on CH1-4 and shows a callout if reuseArgument is working.

**ROBIN** (by Andre Asbury) — tests sensitiveArgument routing and the default fallback:
```xml
<keyword name='ROBIN' leaf='1' command='1' query='1' argument='1'>
    <translation header='callouts:callout2:text "ThisIsRobin"'
                 addedArgument='1' sensitiveArgument='Andre'/>
    <translation header='callouts:callout2:text "ThisIsDefaultArg"'
                 addedArgument='1'/>
</keyword>
```
Send: `ROBIN Andre` → callout shows "ThisIsRobin". Send: `ROBIN anything_else` → callout shows "ThisIsDefaultArg".

---

## Debugging Strategy

Because the PI Translator provides no error output, use the following approach:

1. **Always include all three debug keywords** (BATman, TURNChannels, ROBIN) in every compatibility file as standard practice.

2. **Scatter them through the file:**
   - BATman near the top (after the root element opens) — verifies the file loaded at all
   - TURNChannels in the middle — verifies one-to-many and reuseArgument work
   - ROBIN near the bottom — verifies sensitiveArgument and default fallback work

3. **After every edit, send all three test commands and check for callouts:**
   ```
   BATman "hello"        -> callout1 should show "hello"
   TURNChannels ON       -> CH1-4 should turn on; callout1 shows "Channels 1-4 are ON"
   ROBIN Andre           -> callout2 shows "ThisIsRobin"
   ROBIN anything_else   -> callout2 shows "ThisIsDefaultArg"
   ```

4. **Follow each command with `*ESR?`** — a return value of 0 means no SCPI error.

5. **If a debug command fails after a file edit**, the syntax error is in the section added since the last passing test. Use XML block comments to bisect and isolate.

6. **Verify file structure first** — if BATman fails immediately after loading a new file, check the root element name (`<translations version='0.5'>`) and the XML declaration, and scan for any non-ASCII characters.

---

## Real-World Examples

Two reference files are provided:
- `Compatibility_DPO7104C_to_MSO58B.xml` — Nvidia customer migration (DPO7kC → MSO58B)
- `Compatibility_TDS754_to_MSO54B.xml` — Lockheed Martin migration (TDS754 → MSO54B)

The TDS754 file is the authoritative reference for correct file structure and attribute syntax. When in doubt, compare your generated file against it.

---

## MCP Server Tools

- `tek_pi_translator_reference()` — Returns this syntax reference
- `tek_extract_scpi_from_code(code)` — Extract SCPI commands from legacy code
- `tek_generate_pi_xml(source, target, translations)` — Generate XML from specifications
- `tek_validate_pi_xml(xml_content)` — Validate XML for common errors
- `tek_legacy_command_lookup(command)` — Look up modern equivalent of a legacy command
