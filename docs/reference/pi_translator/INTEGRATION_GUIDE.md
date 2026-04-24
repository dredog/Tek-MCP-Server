# PI Translator Tools — MCP Server Integration Guide

## What's Included

```
pi_translator_tools/
├── pi_translator_tools.py          # New MCP tools (insert into tektronix_mcp_server.py)
├── INTEGRATION_GUIDE.md            # This file
└── docs/
    └── reference/
        ├── legacy_to_modern_scpi_migration.md    # Migration guide (if not already present)
        └── pi_translator/
            ├── PI_TRANSLATOR_SYNTAX.md           # Syntax reference (indexed by tek_search_local_docs)
            └── examples/
                ├── Compatibility_DPO7104C_to_MSO58B.xml   # Nvidia customer example
                └── Compatibility_TDS754_to_MSO54B.xml     # Lockheed Martin example
```

## Integration Steps

### Step 1: Add Configuration Path

In `tektronix_mcp_server.py`, find the CONFIGURATION section (~line 218) and add:

```python
# After PTA_LESSONS_PATH line:
PI_TRANSLATOR_PATH = DOCS_REFERENCE_PATH / "pi_translator"  # PI Translator examples & reference
```

### Step 2: Add to Local Docs Search

In the `search_local_docs()` function (~line 1275), add these entries to the `search_specs` list:

```python
# PI Translator documentation and examples
(PI_TRANSLATOR_PATH, "**/*.md", "markdown", 0),
(PI_TRANSLATOR_PATH, "**/*.xml", "xml", 0),  # XML examples are searchable too
```

Note: You may also want to add `"xml"` as a file_type option in the search results display.

### Step 3: Add PI Translator Query Terms

In the `PTA_PLUGIN_QUERY_TERMS` list (~line 230), this is NOT needed. The PI Translator 
tools have their own detection and don't need to trigger the PTA plugin warning.

### Step 4: Insert the Tools

In `tektronix_mcp_server.py`, find the section just BEFORE `tek_status()` (~line 2865).
Insert the contents of `pi_translator_tools.py` there (everything between the 
`# =============================================================================` headers).

The three new tools are:
- `tek_pi_translator_reference()` — Syntax reference (no args)
- `tek_extract_scpi_from_code(code)` — Parse legacy code  
- `tek_generate_pi_xml(source, target, translations)` — Generate XML
- `tek_validate_pi_xml(xml_content)` — Validate XML

### Step 5: Update Status Tool

In `tek_status()`, add the PI Translator tools to the output. Add this section after 
the "Live Instrument Control" block:

```python
output += """
### PI Translator / Code Migration
- `tek_pi_translator_reference()` - XML syntax reference (**read first!**)
- `tek_extract_scpi_from_code(code)` - Extract SCPI commands from legacy code
- `tek_generate_pi_xml(source, target, translations)` - Generate XML file
- `tek_validate_pi_xml(xml_content)` - Validate XML for errors
- `tek_legacy_command_lookup(command)` - Find modern equivalent (existing tool)
"""
```

### Step 6: Update Server Version

Bump version string to `v1.2.0` (or `v1.1.1` if bundling with other changes):
- Line ~21: `Tektronix MCP Server v1.2.0`
- Line ~3203: startup banner
- Line ~2871: status tool header

### Step 7: Copy Docs Files

Copy the `docs/reference/` contents to your MCP server's docs directory:

```bash
# From the pi_translator_tools directory:
cp -r docs/reference/pi_translator /path/to/mcp_server/docs/reference/
cp docs/reference/legacy_to_modern_scpi_migration.md /path/to/mcp_server/docs/reference/
```

### Step 8: Test

1. Restart the MCP server
2. Call `tek_status()` — verify PI Translator tools appear
3. Call `tek_pi_translator_reference()` — verify syntax reference returns
4. Call `tek_search_local_docs("PI translator")` — verify docs are indexed
5. Test the full workflow:
   ```
   # Step 1: Extract commands from sample code
   tek_extract_scpi_from_code('scope.write(":HOR:TRIG:POS 50")\nscope.query(":CH1:IMPedance?")')
   
   # Step 2: Generate XML
   tek_generate_pi_xml("DPO7104C", "MSO58B", '[{"legacy":":HOR:TRIG:POS","modern":":HOR:POS"}]')
   
   # Step 3: Validate
   tek_validate_pi_xml('<translations version="0.5">...</translations>')
   ```

## Workflow: How These Tools Are Used Together

```
User provides legacy code
        │
        ▼
tek_extract_scpi_from_code(code)
        │ Returns categorized list of SCPI commands
        ▼
tek_legacy_command_lookup(command)  ←── For each command
tek_search_commands(keyword)       ←── Find modern syntax
        │ Claude determines: works as-is? needs XML? needs code change?
        ▼
tek_pi_translator_reference()      ←── Claude reads syntax rules
        │
        ▼
tek_generate_pi_xml(source, target, translations_json)
        │ Returns complete XML file
        ▼
tek_validate_pi_xml(xml_content)
        │ Returns validation report
        ▼
User gets: complete XML file + deployment instructions
```

## Tek PTA Note: Channel Naming

When listing channels in Tek PTA UI, always display as `CH1`, `CH2`, etc., 
not just `1` or `2`. The bare number is ambiguous — it could refer to a 
channel, math, reference, or bus.
