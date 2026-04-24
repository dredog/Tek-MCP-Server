# Lessons Learned: AWG Marker Configuration — Complete Reference (AWG70000 and AWG5200)

**Date:** 2026-04-15 09:29  
**Test Name:** AWG Marker Configuration — Complete Reference (AWG70000 and AWG5200)

## Summary
Complete reference for configuring and writing marker outputs on AWG70000 and AWG5200 series via SCPI. Covers DAC resolution setup (required before markers fire), instrument-specific bit-to-BNC mapping (reversed between families), the async DATA/marker race condition, wfmx file format vs SCPI bit conventions, and cross-platform compatibility strategy. Developed and empirically validated during Link-16 frequency-hopping waveform work (AWG70002B, 51 hops, 65000 samples @ 5 GS/s).

## Instruments Used
AWG70002B, AWG5200, MSO58 oscilloscope

## Key SCPI Commands
─── DAC RESOLUTION (must set BEFORE loading waveforms) ───────────────────────
SOURce1:DAC:RESolution <n>   — channel 1 only
SOURce2:DAC:RESolution <n>   — channel 2 only
DAC:RESolution <n>           — all channels at once
SOURce1:DAC:RESolution?      — query current setting

AWG70000 series values:
  10 = 10-bit analog, markers DISABLED (default)
   9 =  9-bit analog + 1 marker  (M1 enabled)
   8 =  8-bit analog + 2 markers (M1 + M2 enabled)

AWG5200 series values:
  16 = 16-bit analog, markers DISABLED (default)
  15 = 15-bit analog + 1 marker
  14 = 14-bit analog + 2 markers
  13 = 13-bit analog + 3 markers
  12 = 12-bit analog + 4 markers

UI equivalent: Setup → Channel → Resolution (bits)

─── MARKER DATA WRITE ────────────────────────────────────────────────────────
WLISt:WAVeform:MARKer:DATA "<name>",<start>,<n_samp>,<IEEE_block>
  — write_raw() + b"\n" terminator REQUIRED (same as DATA write)
  — chunk size 1 MB recommended for large waveforms

─── BIT-TO-MARKER MAPPING (SCPI convention) ──────────────────────────────────
AWG70000 series:    bit 6 (0x40) = M1 BNC,  bit 7 (0x80) = M2 BNC
AWG5200 series:     bit 7 (0x80) = M1 BNC,  bit 6 (0x40) = M2 BNC
wfmx FILE format:   bit 0 (0x01) = M1,       bit 1 (0x02) = M2  (different from both)
Universal safe:     0xFF — fires ALL markers on any platform

─── WAVEFORM DATA WRITE (for context — same chunked pattern) ─────────────────
WLISt:WAVeform:DATA "<name>",<start>,<n_samp>,<IEEE_block>
  — float32 little-endian samples, clipped to ±1.0
  — write_raw() + b"\n" CRITICAL — omitting causes AWG to hang

## Gotchas / Problems Encountered
1. DAC RESOLUTION NOT SET — most common "markers not working" cause
   If SOURce:DAC:RESolution is left at default (10 on AWG70k, 16 on AWG5200),
   marker data is silently IGNORED — no output on any marker BNC. The M2 LED
   on the instrument front panel will not illuminate. Must set resolution first,
   then load/assign waveforms.

2. BIT MAPPING IS REVERSED BETWEEN FAMILIES
   AWG70000: 0x40 = M1, 0x80 = M2
   AWG5200:  0x80 = M1, 0x40 = M2
   Code written for one platform will silently drive the WRONG BNC on the other.
   Using 0xFF sidesteps the issue entirely.

3. ASYNC DATA WRITE RACE CONDITION — markers get zeroed
   WLISt:WAVeform:DATA is asynchronous — write_raw() returns when bytes are
   delivered over TCP, but the AWG DMA-writes to waveform memory afterward.
   If WLISt:WAVeform:MARKer:DATA arrives before DMA completes, the DATA write
   finishes last and ZEROES the marker bytes. Markers vanish with no error.
   Fix: sleep after DATA write before sending marker write.

4. DO NOT USE inst.query() FOR BINARY RESPONSES
   query() reads until \n terminator. IEEE block responses for float32 data
   can contain 0x0A bytes inside the payload, causing early termination and
   leaving garbage in the VISA buffer that corrupts subsequent commands.
   Always use inst.read_raw() for binary block responses.

5. wfmx FILE FORMAT vs SCPI — different bit positions for same marker
   wfmx uses bit 0 (0x01) for M1; SCPI uses bit 6 or bit 7 depending on platform.
   Must convert when reading from file and writing via SCPI.

6. RESIZE REQUIRES DELETE + NEW BEFORE DATA WRITE
   If waveform length changes, must delete slot and create new one:
     WLISt:WAVeform:DELete "<name>"
     WLISt:WAVeform:NEW "<name>",<n_samp>,REAL
   Then write DATA, then markers.

7. CHANGING DAC RESOLUTION REQUIRES WAVEFORM RELOAD
   Waveforms already in the list must be reassigned/reloaded after changing
   DAC resolution — the instrument re-interprets bit allocation on load.

## Solutions
1. ALWAYS SET DAC RESOLUTION FIRST, THEN LOAD WAVEFORMS:
   AWG70000 — 2 markers:  inst.write("DAC:RESolution 8")
   AWG5200  — 2 markers:  inst.write("DAC:RESolution 14")
   Branch by IDN if script must run on both:
     idn = inst.query("*IDN?")
     res = 8 if "AWG70" in idn else 14
     inst.write(f"DAC:RESolution {res}")

2. CROSS-PLATFORM MARKER BYTE: Use 0xFF for HIGH samples
   Fires all markers on both families. Acceptable when only M1 is in use
   (M2 firing into nothing causes no harm). If M1/M2 isolation is needed:
     AWG70000: HIGH=0x40 (M1 only) or 0x80 (M2 only) or 0xC0 (both)
     AWG5200:  HIGH=0x80 (M1 only) or 0x40 (M2 only) or 0xC0 (both)

3. ASYNC RACE CONDITION FIX — sleep between DATA and MARKer writes:
     data_mb = (n_samp * 4) / 1e6
     time.sleep(max(0.75, data_mb * 0.6))
   Do NOT use binary query as sync barrier (0x0A in float data corrupts VISA buffer).

4. CHUNKED WRITE PATTERN (both DATA and MARKer):
     raw = samples.tobytes()   # or markers.tobytes()
     sent = 0; s_off = 0
     while sent < len(raw):
         chunk = raw[sent : sent + CHUNK_SIZE]
         n_ch  = len(chunk) // 4   # for DATA (samples); len(chunk) for MARKer
         cmd   = f'WLISt:WAVeform:DATA "{name}",{s_off},{n_ch},'.encode()
         inst.write_raw(cmd + ieee_block(chunk) + b"\n")
         sent += len(chunk); s_off += n_ch

5. wfmx FILE → SCPI CONVERSION for AWG70000:
     mk_scpi = ((markers_from_file & 0x01) * 0x40).astype(np.uint8)
   For AWG5200:
     mk_scpi = ((markers_from_file & 0x01) * 0x80).astype(np.uint8)
   Or use 0xFF universally.

## Measurement Tips
Debug setup that definitively confirmed bit mapping:
  Assign 6 distinct marker bytes to 6 different hop frequencies, zero all others:
    freq_1002: 0x01   freq_1113: 0x02   freq_1137: 0x03
    freq_1161: 0x80   freq_1185: 0x40   freq_969:  0xC0
  Connect scope Ch A to M1 BNC, Ch B to M2 BNC.
  Trigger on RF channel. Use 100 µs/div timebase for Link-16 hop rate (~26 kHz).
  Observe which scope channel fires on each hop frequency to map bits to BNCs.
  SpectrumView on the scope identifies which frequency is currently playing.

## Additional Notes
DESIGN DECISION: link16_adjust_lead_fast.py uses 0xFF for all HIGH marker samples
rather than instrument-specific values. This is intentional — only M1 is connected
in the current Link-16 demo setup. M2 firing into an open BNC causes no issues.
If M1/M2 isolation becomes required in a future application, use the
instrument-specific values documented in the solutions section above.

SCPI DB NOTE: SOURce:DAC:RESolution is not present in the local MCP SCPI database
for either AWG70000 or AWG5200. It was identified from the user manual and confirmed
working via UI observation. Probe on live instrument to verify exact syntax before
depending on it in production scripts.

---
*Generated by Tek MCP Server v1.3.5*
