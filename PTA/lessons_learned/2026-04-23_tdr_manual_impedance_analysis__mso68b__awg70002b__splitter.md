# Lessons Learned: TDR Manual Impedance Analysis — MSO68B + AWG70002B + Splitter

**Date:** 2026-04-23 17:04  
**Test Name:** TDR Manual Impedance Analysis — MSO68B + AWG70002B + Splitter

## Summary
Complete TDR impedance analysis using an external fast-edge source (AWG70002B or DPO7 fast edge), 18 GHz resistive splitter, and MSO68B oscilloscope. Manual Math formula replaces built-in TDR measurement when using an external AWG. Python script (tdr_analysis.py) automates full setup, acquisition, impedance calculation, feature detection, segment classification, and plotting with distance axis.

## Instruments Used
MSO68B (C031797, fw 2.10.5), DPO714AX, AWG70002B, Mini-Circuits ZFRSC-183-S+ 18 GHz 2-way splitter

## Key SCPI Commands

SETUP SEQUENCE (order matters):
  *RST                                          — always start here; known state
  CH1:TERmination 50                            — RST defaults to 1MΩ; MUST set 50Ω before TDR
  DISplay:WAVEView1:CH1:STATE ON                — RST may leave channel hidden
  MEASUrement:MEAS1:TYPe TDR
  MEASUrement:MEAS1:SOUrce1 CH1
  MEASUrement:MEAS1:STATE ON
  MEASUrement:MEAS1:TDRPREset EXECute           — async; sleep(8) mandatory after
  [verify HORizontal:SCAle? — if >200ns/div, TDRPREset found no signal; force 10ns/div]
  CH1:BANdwidth:FILTer:OPTIMIZation FLAT
  CH1:BANdwidth <limit>                         — apply AFTER preset (preset resets to full BW)
  HORizontal:MODe MANual
  HORizontal:RECOrdlength 20000
  ACQuire:MODe AVErage
  ACQuire:NUMAVg 64
  ACQuire:STOPAfter SEQuence
  ACQuire:SEQuence:MODe NUMACQs
  ACQuire:SEQuence:NUMSEQuence 64
  ACQuire:STATE RUN                             — fire; poll ACQuire:STATE? until "0"
  ACQuire:SEQuence:CURrent?                     — progress counter during averaging
  MATH:MATH1:TYPe ADVanced
  MATH:MATH1:DEFine "50*(Ch1-Vb)/((2*Vm-Vb)-Ch1)"
  DISplay:WAVEView1:MATH:MATH1:VERTical:SCAle 10       — 10 Ω/div
  DISplay:WAVEView1:MATH:MATH1:VERTical:POSition -3.5  — range ~-15 to +85 Ω

IMPEDANCE FORMULA:
  Z = Z0*(Ch1 - V_baseline) / ((2*V_matched - V_baseline) - Ch1)
  where V_baseline = Ch1 before step, V_matched = Ch1 after step with all-50Ω cables

WAVEFORM FETCH:
  DATa:SOUrce CH1 / DATa:ENCdg RIBinary / DATa:WIDth 2
  WFMOutpre:XINcr? XZEro? PT_Off? YMUlt? YOFf? YZEro?  — preamble
  CURVE?  — 16-bit binary, parse IEEE 488.2 #Ncount header


## Gotchas / Problems Encountered

1. AUTOSet EXECute returns 40 µs/div with TDR fast-edge signal — useless, never use for TDR
2. TDRPREset EXECute is asynchronous — *OPC? returns immediately but preset keeps running; sleep(8) mandatory
3. TDRPREset always resets CH1:BANdwidth to full — BW limit must be set AFTER the sleep(8)
4. *RST sets CH1:TERmination to 1 MΩ — must set 50Ω explicitly after every reset
5. HORizontal:MODe MANual required before changing RECOrdlength on MSO68B
6. Built-in TDR measurement (MEASUrement:MEAS1) returns 9.91E+37 "Invalid input" with external AWG — expected; manual Math formula is the solution
7. MEASUrement:MEAS1:TDR:* sub-commands (EQUAlize, STEPdetect, SIGnaltype) all time out — never query
8. MATH:MATH1:DEFine? also times out on DPO714AX under some conditions
9. Linearised Z formula 50*(1+rho) is wrong at mismatch; exact formula 50*(1+rho)/(1-rho) required
10. Calibration values (V_baseline, V_matched) are instrument+splitter specific — DPO714AX: -2.79mV/-304.7mV; MSO68B+AWG70002B: -4.6mV/-126.0mV; never share between setups
11. Connector spikes between 75Ω cables can momentarily hit 110-120Ω — HIGH_Z_THRESH must be 120+ Ω; add 8cm sustain requirement before calling anything "open end"
12. SHORT_SEG_CM minimum should be 8cm (~3 inches) — no real patch cable is shorter; 4cm lets 1.7" connectors slip through as "cables"
13. Near-trigger region (< 5cm from trigger) is always a connector/adapter, never a cable segment
14. At low BW (200MHz, 1GHz), broad-step window must scale with resolution: window = 3× resolution distance; fixed 4cm window is too small at 1GHz (res=3.7cm) and misses gradual 75Ω transitions


## Solutions

1. Replace AUTOSet with TDRPREset EXECute + sleep(8); sanity-check H scale after (>200ns/div = bad, force 10ns/div)
2. Always do *RST first for known state, then explicitly set CH1:TERmination 50
3. Apply BW limit and record length changes only after the TDRPREset sleep
4. Use manual Math formula Z=Z0*(V-Vb)/(2Vm-Vb-V) — equivalent to exact Heaviside formula; verify with MATH:MATH1:DEFine? readback
5. Calibrate by connecting all-50Ω cables; measure V_baseline (pre-step flat) and V_matched (post-step flat) from Ch1 waveform
6. Two-pass feature detection: (a) sharp derivative pass for fast transitions, (b) broad sliding-median pass with BW-adaptive window for gradual BW-limited transitions
7. High-Z detection requires sustain: Z must stay above threshold for 8+ cm continuously before classifying as open end
8. Auto-scale loop: after acquisition check Math1 tail (last 10%) for Z > 80Ω; if not seen, double H scale and re-acquire (up to 6 iterations)
9. Single-sequence acquisition: ACQuire:STOPAfter SEQuence + NUMSEQuence 64; poll STATE? until "0" — never guess with sleep()


## Measurement Tips

Distance formula: d = (t_roundtrip / 2) × VP × c. VP=0.70 for PTFE coax, 0.66 solid PE, 0.78 foam PE.
Splitter loss: -3dB per port, -6dB round-trip. Calibration absorbs this automatically.
BW simulation: CH1:BANdwidth 1E9 + FLAT filter simulates 1GHz scope on MSO68B. Useful for predicting what a 4/5 Series would see on same DUT.
System rise time: t_sys = sqrt(t_pulse^2 + t_scope^2). Distance resolution = t_sys/2 × VP × c.
At 1GHz BW, resolution ~3.7cm. At 200MHz, ~18.4cm — cables shorter than settle zone are not reliably measured.
Segment classification rules: near trigger (<5cm) = connector; length <8cm = connector or glitch; length ≥8cm = cable. Glitch = short segment sandwiched between two cables.


## Additional Notes

Final script: tdr_analysis.py (v8+) — self-contained, interactive prompts for IP/cal profile/BW limit.
Outputs: waveform PNG + separate table PNG (table never overlaps waveform). Z axis auto-scales from data percentiles.
Calibration profiles stored as named dicts — add new entry per instrument/splitter combination.
Standard cable length snap: 12", 18", 24", 36", 40", 1m, 2m, 3m, 6ft within ±12%.
BW-adaptive parameters computed in compute_bw_params(): settle zone, step separation, broad window, short-seg threshold all scale from 0.35/BW rise time.
Keysight DCA-X (N1055A) has built-in step generator in the module — no splitter needed, cleaner architecture. Keysight VNA+S93011B option gives TDR via inverse FFT up to 67GHz. R&S RTP-B7 pulse source is built into scope rear panel — no external AWG needed. Megger/AEMC standalone TDRs: 2-3ns pulse, ~20-30cm resolution, find opens/shorts only — completely different use case from impedance characterization.


---
*Generated by Tek MCP Server v1.4.1*
