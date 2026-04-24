#!/usr/bin/env python3
"""
generate_usage_boosts.py — Mine Python examples for SCPI command frequency
==========================================================================
Scans all Python files in docs/python_examples/ and PTA/test_suites/,
extracts SCPI commands from scope.write() / scope.query() / inst.write()
calls, counts frequency, and generates the _USAGE_BOOSTS dict for
tektronix_mcp_server.py.

Usage:
    cd <your tektronix_mcp_server directory>
    python generate_usage_boosts.py

    Or specify paths:
    python generate_usage_boosts.py --docs docs/python_examples --pta PTA/test_suites

Output:
    Prints the _USAGE_BOOSTS dict ready to paste into tektronix_mcp_server.py,
    and saves it to usage_boosts_generated.py.
"""

import argparse
import re
from collections import Counter
from pathlib import Path


def extract_scpi_commands(filepath: Path) -> list[str]:
    """Extract SCPI commands from Python write/query calls in a file."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    commands = []

    # Match patterns like:
    #   scope.write("CH1:SCAle 0.5")
    #   scope.query("CH1:SCAle?")
    #   inst.scope_write("MEASUrement:DELETEALL")
    #   scope.write('ACQuire:STOPAfter SEQuence')
    #   scope.write(f"CH{ch}:SCAle {scale}")
    #   self.inst.scope_write(f"DISplay:WAVEView1:CH{ch}:STATE ON")
    patterns = [
        # Standard pyvisa: scope.write("...") / scope.query("...")
        r'''\.(?:write|query)\s*\(\s*(?:f?)(["'])(.*?)\1''',
        # PTA style: self.inst.scope_write("...") / scope_write("...")
        r'''scope_(?:write|query)\s*\(\s*(?:f?)(["'])(.*?)\1''',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            raw = match.group(2)
            # Extract just the SCPI command (before the first space = value)
            # Handle f-strings: "CH{ch}:SCAle {scale}" -> extract the SCPI path
            scpi_part = raw.split(" ")[0].split("\t")[0].strip()
            if not scpi_part:
                continue
            # Skip non-SCPI strings (must contain letters and either : or *)
            if not re.match(r'^[*A-Za-z]', scpi_part):
                continue
            if ':' not in scpi_part and not scpi_part.startswith('*'):
                # Single segment with no colon — only keep if it's a known
                # IEEE command or looks like a SCPI mnemonic
                if not re.match(r'^\*[A-Z]{2,}', scpi_part) and \
                   not re.match(r'^[A-Z]{3,}$', scpi_part, re.IGNORECASE):
                    continue

            commands.append(scpi_part)

    return commands


def normalize_scpi(scpi: str) -> str:
    """Normalize a SCPI command for counting.
    
    - Uppercase
    - Strip query suffix ?
    - Replace instance numbers with <x>: CH1 -> CH<x>, MEAS1 -> MEAS<x>
    - Replace f-string variables: CH{ch} -> CH<x>
    - Strip trailing values/arguments
    """
    s = scpi.upper().rstrip("?").strip()
    # Replace f-string placeholders: {ch}, {channel}, {meas}, etc.
    s = re.sub(r'\{[a-zA-Z_]+\}', '<x>', s)
    # Replace instance numbers: CH1, MEAS2, B1, SEARCH1, PLOT1, etc.
    # But NOT in values like "25E6" or hex "0xFF"
    s = re.sub(r'(?<=[A-Z])(\d+)(?=[:?]|$)', '<x>', s)
    # Remove trailing spaces/values that slipped through
    s = s.split(" ")[0]
    return s


def main():
    parser = argparse.ArgumentParser(description="Mine Python examples for SCPI usage frequency")
    parser.add_argument("--docs", default="docs/python_examples",
                        help="Path to Python examples directory")
    parser.add_argument("--pta", default="PTA/test_suites",
                        help="Path to PTA test suites directory")
    parser.add_argument("--extra", nargs="*", default=[],
                        help="Additional directories to scan")
    parser.add_argument("--also-md", action="store_true",
                        help="Also scan .md files for SCPI in code blocks")
    args = parser.parse_args()

    all_dirs = [args.docs, args.pta] + args.extra
    
    # Also scan docs/*.md and PTA/lessons_learned/*.md for SCPI in code blocks
    md_dirs = ["docs", "PTA/lessons_learned"]
    
    all_commands = []
    files_scanned = 0

    # Scan Python files
    for dir_path in all_dirs:
        p = Path(dir_path)
        if not p.exists():
            print(f"  Skipping {dir_path} (not found)")
            continue
        for pyfile in sorted(p.rglob("*.py")):
            cmds = extract_scpi_commands(pyfile)
            if cmds:
                all_commands.extend(cmds)
                files_scanned += 1
                print(f"  {pyfile.name}: {len(cmds)} SCPI commands")

    # Optionally scan markdown files for code blocks
    if args.also_md:
        for dir_path in md_dirs:
            p = Path(dir_path)
            if not p.exists():
                continue
            for mdfile in sorted(p.rglob("*.md")):
                cmds = extract_scpi_commands(mdfile)
                if cmds:
                    all_commands.extend(cmds)
                    files_scanned += 1
                    print(f"  {mdfile.name}: {len(cmds)} SCPI commands (from code blocks)")

    if not all_commands:
        print("\nNo SCPI commands found. Check paths and try again.")
        print(f"  Searched: {all_dirs}")
        return

    # Normalize and count
    normalized = [normalize_scpi(c) for c in all_commands]
    counter = Counter(normalized)
    
    # Sort by frequency descending
    sorted_cmds = counter.most_common()
    
    print(f"\n{'='*70}")
    print(f"  SCPI Command Frequency Analysis")
    print(f"  Files scanned: {files_scanned}")
    print(f"  Total SCPI calls: {len(all_commands)}")
    print(f"  Unique commands: {len(counter)}")
    print(f"{'='*70}")
    
    # Tier the boosts:
    #   5+ occurrences -> boost 50 (heavily used in examples)
    #   2-4 occurrences -> boost 25 (moderately used)
    #   1 occurrence -> boost 10 (at least one verified example exists)
    
    print(f"\n--- Commands used 5+ times (boost 50) ---")
    tier1 = [(cmd, count) for cmd, count in sorted_cmds if count >= 5]
    for cmd, count in tier1:
        print(f"  {count:>4d}x  {cmd}")
    
    print(f"\n--- Commands used 2-4 times (boost 25) ---")
    tier2 = [(cmd, count) for cmd, count in sorted_cmds if 2 <= count < 5]
    for cmd, count in tier2:
        print(f"  {count:>4d}x  {cmd}")
    
    print(f"\n--- Commands used 1 time (boost 10) ---")
    tier3 = [(cmd, count) for cmd, count in sorted_cmds if count == 1]
    for cmd, count in tier3[:30]:
        print(f"  {count:>4d}x  {cmd}")
    if len(tier3) > 30:
        print(f"  ... and {len(tier3) - 30} more")

    # Generate the Python dict
    print(f"\n{'='*70}")
    print("  GENERATED CODE — paste into tektronix_mcp_server.py")
    print(f"{'='*70}\n")
    
    output_lines = []
    output_lines.append("# Auto-generated from Python examples and PTA test suites.")
    output_lines.append("# Commands found in real automation scripts get a relevance boost")
    output_lines.append("# so they rank higher in keyword search results.")
    output_lines.append(f"# Source: {files_scanned} Python files, {len(all_commands)} total SCPI calls")
    output_lines.append(f"# Unique commands: {len(counter)}")
    output_lines.append("")
    output_lines.append("_USAGE_BOOSTS: dict[str, int] = {")
    
    for cmd, count in sorted_cmds:
        if count >= 5:
            boost = 50
        elif count >= 2:
            boost = 25
        else:
            boost = 10
        output_lines.append(f'    "{cmd}": {boost},  # {count}x in examples')
    
    output_lines.append("}")
    
    code = "\n".join(output_lines)
    print(code)
    
    # Save to file
    outfile = Path("usage_boosts_generated.py")
    outfile.write_text(code, encoding="utf-8")
    print(f"\n  Saved to: {outfile}")
    
    # Also generate the integration snippet
    print(f"\n{'='*70}")
    print("  INTEGRATION — add this to search_commands() scoring loop")
    print(f"{'='*70}\n")
    print("""
# Add this right after computing 'score' for each command, before 'if score > 0':

            # Usage boost: commands found in real Python examples rank higher
            scpi_normalized = re.sub(r'(?<=[A-Z])\\d+', '<x>', scpi.upper().rstrip('?'))
            scpi_normalized = scpi_normalized.replace('<x>', '').replace('<X>', '')
            usage_boost = 0
            for usage_key, usage_val in _USAGE_BOOSTS.items():
                usage_clean = usage_key.replace('<x>', '').replace('<X>', '')
                if scpi_normalized.startswith(usage_clean) or usage_clean.startswith(scpi_normalized):
                    usage_boost = max(usage_boost, usage_val)
            score += usage_boost
""")


if __name__ == "__main__":
    main()
