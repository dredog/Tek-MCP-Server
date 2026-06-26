# TDR Reference Guide — Tektronix Oscilloscopes
**Source documents:** TDR Datasheet 61W-74085-0 (Jul 2024) | Basic TDR Z Line setup guide (AE internal) | TDR lessons learned 2026-04-21/23  
**Applies to:** MSO 4/5/6 Series B (Options 4-TDR / 5-TDR / 6-TDR), DPO 7 Series, DPO70000 Series with TCS70902

---

## 1. What Is TDR and When To Use It

Time Domain Reflectometry (TDR) launches a fast step edge down a transmission line and measures the reflected voltage vs. time to characterize impedance. Use cases:

- Verify characteristic impedance of PCB traces, cables, and connectors
- Measure trace length, cable length, and signal propagation delay
- Locate opens, shorts, capacitive and inductive discontinuities
- Identify cable crimping defects and connector launch integrity
- Determine PCB dielectric constants
- Low-cost alternative to VNA for 50Ω interconnect work

---

## 2. Instrument Options and Licensing

### Option TDR — MSO 4/5/6 Series B (Built-in TDR with Picotest J2154A)

| Option | Instruments | Bandwidth Available |
|--------|------------|-------------------|
| **4-TDR** | MSO44B, MSO46B | 200 MHz, 350 MHz, 500 MHz, 1 GHz, 1.5 GHz |
| **5-TDR** | MSO54B, MSO56B, MSO58B, MSO58LP | 350 MHz, 500 MHz, 1 GHz, 2 GHz |
| **6-TDR** | MSO64B, MSO66B, MSO68B | 1 GHz, 2.5 GHz, 4 GHz, 6 GHz, 8 GHz, 10 GHz |

**Max TDR system bandwidth on 6-TDR: 7.5 GHz**

Purchase options: new instrument option (4-TDR / 5-TDR / 6-TDR), product upgrade (SUP4/5/6-TDR), or floating license (SUP4/5/6-TDR-FL).

Included in bundles: PRO-POWER and ULTIMATE bundles for each Series.

### External AWG + Manual Math (No TDR License Required)

When using an external AWG (AWG70002B, AWG5200 etc.) as the step source:
- Built-in TDR measurement (`MEASUrement:MEAS1:TYPe TDR`) returns `9.91E+37` ("Invalid input") — expected behavior. The built-in TDR needs the scope's own fast edge for internal calibration.
- Solution: use manual Math formula (see Section 6). This works on ANY MSO 4/5/6/7 or DPO 7/70000 without a TDR license.

---

## 3. System Risetime and Distance Resolution

### Formula (RSS — Root Sum of Squares)

```
t_sys = sqrt(t_scope² + t_pulse² + t_probe²)
```

Where:
- `t_scope = 350 ps / BW_GHz` — scope bandwidth contribution
- `t_pulse` — 10–90% rise time of the step source
- `t_probe` — 10–90% rise time of the probe or tip

### Distance Resolution

```
time_resolution = t_sys / 2          (÷2 for round-trip)
distance_resolution = (t_sys / 2) × VP × 0.3 mm/ps
```

Where VP = velocity of propagation (ratio of signal speed to speed of light).

### Reference: Common Source Rise Times

| Source | Rise Time |
|--------|-----------|
| AWG70000 Series (all models) | ~100 ps |
| AWG5200 Series (all models) | ~100 ps |
| DPO 7 Series built-in fast edge | ~90 ps (**DPO7 only — not MSO4/5/6**) |
| DPO70000 Series built-in fast edge | ~200 ps (**DPO70000 only — not MSO4/5/6**) |
| TCS70902 sampling module | ~10 ps |
| Picotest J2154A | ~34 ps |

**Note:** MSO 4/5/6 Series do NOT have a built-in fast-edge step generator. A Picotest J2154A or external AWG is required for TDR on MSO 4/5/6.

### Reference: Common Probe Rise Times

| Probe | Rise Time |
|-------|-----------|
| SMA direct (no probe) | 0 ps |
| GigaProbe DVT40 | 4.5 ps |
| Picotest P2105A TDR probe | 21.8 ps |
| GigaProbe DVT30 | 27 ps |

### Reference: Velocity of Propagation

| Dielectric / Cable Type | VP |
|------------------------|----|
| PTFE coax | 0.70 |
| Foam PE coax | 0.78 |
| Solid PE coax / RG-58 | 0.66 |
| FR4 microstrip | 0.60 |
| FR4 stripline | 0.52 |

### Example System Performance Table

| Scope BW | Source | Probe | t_sys | Time Res | Distance Res (VP=0.70) |
|----------|--------|-------|-------|----------|------------------------|
| 10 GHz (MSO6B) | J2154A (34 ps) | P2105A (21.8 ps) | ~56.9 ps | ~28.4 ps | ~6.0 mm |
| 25 GHz (DPO7) | TCS70902 (10 ps) | DVT40 (4.5 ps) | ~22.8 ps | ~11.4 ps | ~2.4 mm |
| 25 GHz (DPO7) | TCS70902 (10 ps) | DVT30 (27 ps) | ~35.1 ps | ~17.5 ps | ~3.7 mm |
| 8 GHz (MSO68B) | AWG70002B (100 ps) | SMA direct | ~106 ps | ~53 ps | ~11 mm |
| 1 GHz (any MSO6) | AWG70002B (100 ps) | SMA direct | ~354 ps | ~177 ps | ~37 mm |

**Interactive calculator:** `docs/reference/tdr_resolution_calculator_v3.html` (open in browser — covers all MSO4/5/6/DPO7/DPO70000 bandwidth options).

---

## 4. TDR Setup — Hardware Required

### Option A: MSO 4/5/6 B with Built-in TDR Option

Required:
- MSO 4/5/6 Series B with Option 4/5/6-TDR installed
- **Picotest J2154A** differential TDR pulse generator (USB-C powered)
- SMA cables (matched pair for differential; single for single-ended)
- Optional probes: Picotest P2103A (differential) or P2105A (single-ended)

Single-Ended connections: J2154A ports 3 → scope Ch1, port 4 → DUT  
Differential connections: ports 1+3 → scope Ch1+Ch2, ports 2+4 → DUT

### Option B: DPO 7 Series / DPO70000 Series with TCS70902

Required:
- DPO 7 Series or DPO70000 Series oscilloscope
- **TCS70902** SignalCorrect module (fast step generator, ~10 ps rise time)
- 3-port resistive power splitter (e.g., Mini-Circuits ZFRSC-183-S+, DC–18 GHz, $118)
- High-quality short SMA cable (included with TCS70902)

**Note:** DPO 7 and DPO70000 Series have their own built-in fast-edge step output (90 ps and 200 ps respectively) for use without TCS70902, but TCS70902 gives ~10 ps and dramatically better resolution.

Connection: TCS70902 step output → splitter port 1 → scope Ch1; splitter port 2 → DUT.

### Option C: External AWG on MSO 4/5/6 (Manual Math — No TDR License)

Required:
- MSO 4/5/6 oscilloscope (any BW)
- AWG70002B (or AWG5200) set to output a fast single-ended step (~100 ps)
- 3-port resistive power splitter (Mini-Circuits ZFRSC-183-S+ recommended)

Connection: AWG output → splitter → scope Ch1 + DUT. This is the setup validated with MSO68B + AWG70002B in the lessons-learned files.

---

## 5. TDRPREset SCPI Sequence (MSO 4/5/6 Built-in TDR)

**When using the built-in TDR option (4/5/6-TDR), use this sequence:**

```python
scope.write("*RST")
scope.write("CH1:TERmination 50")                      # RST defaults to 1MΩ — MUST set 50Ω
scope.write("DISplay:WAVEView1:CH1:STATE ON")           # RST may hide channel
scope.write("MEASUrement:MEAS1:TYPe TDR")
scope.write("MEASUrement:MEAS1:SOUrce1 CH1")
scope.write("MEASUrement:MEAS1:STATE ON")
scope.write("MEASUrement:MEAS1:TDRPREset EXECute")     # ASYNC — MUST sleep after
import time; time.sleep(8)                              # Mandatory — preset keeps running

# Verify H scale — if >200 ns/div, no signal found; force 10 ns/div
h_scale = float(scope.query("HORizontal:SCAle?"))
if h_scale > 200e-9:
    scope.write("HORizontal:SCAle 10E-9")

# Apply BW limit AFTER the sleep (TDRPREset always resets BW to full)
scope.write("CH1:BANdwidth:FILTer:OPTIMIZation FLAT")  # FLAT for impedance accuracy
scope.write("CH1:BANdwidth 1E9")                        # Optional BW limit (simulate 4/5-series)

# Increase record length for smoother impedance derivative
scope.write("HORizontal:MODe MANual")
scope.write("HORizontal:RECOrdlength 20000")            # 2.3 ps/pt vs 20 ps/pt at preset default
```

**What TDRPREset does:** Sets H scale 4.5597 ns/div, H position 10%, record 2280 pts (20 ps/pt), ACQ AVE/20, full BW, trigger −62 mV FALL on Ch1. Matches exactly what the TDR Preset button does in the UI.

**Critical gotchas:**
- `TDRPREset EXECute` is asynchronous — `*OPC?` returns immediately but preset keeps running. Always `sleep(8)`.
- `*RST` sets `CH1:TERmination` to 1 MΩ — set 50 Ω explicitly after every reset.
- `HORizontal:MODe MANual` is required before changing RECOrdlength on MSO68B.
- **Do NOT use `AUTOSet EXECute` for TDR** — returns 40 µs/div with a TDR fast-edge signal. Use `TDRPREset` instead.
- `MEASUrement:MEAS1:TDR:*` sub-commands (`EQUAlize`, `STEPdetect`, `SIGnaltype`) time out — never query them.

---

## 6. Manual Math Formula TDR (External AWG / No TDR License)

When using external AWG or when built-in TDR returns `9.91E+37`:

### Impedance Formula

```
Z = Z0 × (Ch1 - V_baseline) / ((2 × V_matched - V_baseline) - Ch1)
```

SCPI math definition:
```
MATH:MATH1:TYPe ADVanced
MATH:MATH1:DEFine "50*(Ch1-Vb)/((2*Vm-Vb)-Ch1)"
```

Where:
- `V_baseline` = Ch1 voltage before the step (pre-step flat region) — instrument+splitter specific, recalibrate for each setup
- `V_matched` = Ch1 voltage after the step with all-50 Ω cables on DUT (post-step flat, matched load)
- `Z0` = 50 Ω (reference impedance)

**⚠ CRITICAL:** Use the exact formula — NOT the linearised `Z = 50×(1+ρ)` approximation. That formula is only valid near 50 Ω. At significant mismatch it is wrong.

### Rho (Reflection Coefficient) — DPO70000 / TCS70902 Method

```python
# Alternative two-Math-channel approach (DPO 7 Series / DPO70000 style):
# Math3 = ρ = (2 × Ch1 / V_step) - 1
# Math2 = Z = 50 × (1 + Math3) / (1 - Math3)
scope.write('MATH:MATH3:TYPe ADVanced')
scope.write(f'MATH:MATH3:DEFine "(2*Ch1/{v_step})-1"')
scope.write('MATH:MATH2:TYPe ADVanced')
scope.write('MATH:MATH2:DEFine "50*(1+Math3)/(1-Math3)"')
```

Where `V_step` = measured pulse amplitude (example: 194.9 mV from TCS70902, 121 mV from AWG70002B + 18 GHz splitter).

### Calibration Values (Instrument + Splitter Specific — Do Not Share Between Setups)

| Setup | V_baseline | V_matched | V_inc (=Vm−Vb) |
|-------|-----------|-----------|----------------|
| DPO714AX + 18 GHz splitter + fast edge | −2.79 mV | −304.7 mV | ~302 mV |
| MSO68B + AWG70002B + 18 GHz splitter | −4.6 mV | −126.0 mV | ~121 mV |

Calibration procedure: connect all-50 Ω cables on DUT port; read V_baseline from Ch1 pre-step flat; read V_matched from Ch1 post-step flat.

### Math Display Setup

```
DISplay:WAVEView1:MATH:MATH1:VERTical:SCAle 10       # 10 Ω/div
DISplay:WAVEView1:MATH:MATH1:VERTical:POSition -3.5  # range approx -15 to +85 Ω
```

---

## 7. Waveform Acquisition for Impedance Analysis

```python
# Averaging sequence — reliable polling method
scope.write("ACQuire:MODe AVErage")
scope.write("ACQuire:NUMAVg 64")
scope.write("ACQuire:STOPAfter SEQuence")
scope.write("ACQuire:SEQuence:MODe NUMACQs")
scope.write("ACQuire:SEQuence:NUMSEQuence 64")
scope.write("ACQuire:STATE RUN")

# Poll until complete — never guess with sleep()
while scope.query("ACQuire:STATE?").strip() != "0":
    progress = scope.query("ACQuire:SEQuence:CURrent?")
    time.sleep(0.5)
```

---

## 8. Waveform Transfer

```python
scope.write("DATa:SOUrce CH1")
scope.write("DATa:ENCdg RIBinary")
scope.write("DATa:WIDth 2")

# Preamble — required to convert raw ADC counts to volts and seconds
x_incr = float(scope.query("WFMOutpre:XINcr?"))
x_zero = float(scope.query("WFMOutpre:XZEro?"))
pt_off = int(scope.query("WFMOutpre:PT_Off?"))
y_mult = float(scope.query("WFMOutpre:YMUlt?"))
y_off  = float(scope.query("WFMOutpre:YOFf?"))
y_zero = float(scope.query("WFMOutpre:YZEro?"))

raw = scope.query_binary_values("CURVE?", datatype='h', is_big_endian=True)
time_axis   = [(i - pt_off) * x_incr + x_zero for i in range(len(raw))]
voltage_ch1 = [(v - y_off) * y_mult + y_zero for v in raw]
```

---

## 9. Distance Axis and Impedance Calculation

```python
VP = 0.70   # PTFE coax; 0.66 solid PE, 0.78 foam PE
C  = 0.3    # mm per ps (speed of light)

# Distance from trigger (round-trip divided by 2)
distance_mm = [(t_s * 1e12 / 2) * VP * C for t_s in time_axis]

# Impedance from raw Ch1 voltage (manual math formula)
def voltage_to_z(v, v_b, v_m, z0=50.0):
    denom = (2*v_m - v_b) - v
    if abs(denom) < 1e-9: return float('inf')
    return z0 * (v - v_b) / denom

z_trace = [voltage_to_z(v, v_baseline, v_matched) for v in voltage_ch1]
```

---

## 10. Feature Detection — Classification Rules

These thresholds were developed and verified with the MSO68B + AWG70002B setup:

| Region | Classification Rule |
|--------|-------------------|
| < 5 cm from trigger | Always a connector/adapter — never a cable segment |
| Z between 45–55 Ω | 50 Ω cable or matched trace |
| Z ~ 75 Ω (sustained ≥ 8 cm) | 75 Ω cable |
| Z spike 110–120 Ω briefly | Connector between cables — add 8 cm sustain before calling "open" |
| Z sustained ≥ 120 Ω for ≥ 8 cm | Open end |
| Segment length < 8 cm | Connector, adapter, or glitch — not a cable |
| Segment length ≥ 8 cm | Cable segment |

**BW-adaptive parameters:** At 1 GHz BW, resolution ≈ 37 mm; step separation window must be ≥ 3× resolution distance. Fixed 4 cm windows are too small at 1 GHz BW.

**Standard cable length snap values (±12%):** 12", 18", 24", 36", 40", 1 m, 2 m, 3 m, 6 ft.

---

## 11. Bandwidth Filter Shape — FLAT vs. STEP

| Setting | Command | Use When |
|---------|---------|----------|
| FLAT | `CH1:BANdwidth:FILTer:OPTIMIZation FLAT` | Impedance characterization — best accuracy on Z value |
| STEP | `CH1:BANdwidth:FILTer:OPTIMIZation STEP` | Rise-time measurement on connectors — better edge fidelity |

Apply BW limit **after** TDRPREset sleep:
```
CH1:BANdwidth:FILTer:OPTIMIZation FLAT
CH1:BANdwidth 1E9    # simulate 1 GHz system on MSO68B
```

---

## 12. Hardware Notes and Third-Party Accessories

### Power Splitters
- **Mini-Circuits ZFRSC-183-S+**: DC–18 GHz 2-way resistive splitter, $118 — the FAE-validated option
- 3 dB per port loss, 6 dB round-trip loss; calibration absorbs this automatically when V_baseline/V_matched are measured with the splitter in place

### TDR Probes (Tektronix does not manufacture TDR probes)
- **Picotest P2103A** — differential TDR probe, 50 & 100 mil pitch, bundled with J2154A kits
- **Picotest P2105A** — single-ended TDR probe, 21.8 ps rise time
- **GigaProbe DVT40** — 40 GHz, 4.5 ps rise time — for DPO7/TCS70902 systems
- **GigaProbe DVT30** — 20 GHz, 27 ps rise time

### Step Generators (Third-Party)
- **Voltative** (voltative.com): 20 ps and 30 ps pulsers, ~$200
- **Leo Bodnar LBE-1321**: 30 ps pulser (~$60 from England)
- **Picotest J2154A**: 34 ps, purpose-built for MSO4/5/6 TDR option

### Competitive TDR Approaches (for customer comparison context)
- **Keysight DCA-X N1055A**: built-in step generator in module — no splitter needed
- **Keysight VNA + S93011B**: TDR via inverse FFT to 67 GHz
- **R&S RTP-B7**: pulse source built into scope rear panel — no external AWG needed
- **Megger/AEMC standalone TDRs**: 2–3 ns pulse, ~20–30 cm resolution — finds opens/shorts only, completely different use case from impedance characterization

---

## 13. Key SCPI Quick Reference for TDR

```
# Core setup
*RST
CH1:TERmination 50                              # MUST — RST defaults to 1 MΩ
DISplay:WAVEView1:CH1:STATE ON
MEASUrement:MEAS1:TYPe TDR
MEASUrement:MEAS1:SOUrce1 CH1
MEASUrement:MEAS1:STATE ON
MEASUrement:MEAS1:TDRPREset EXECute            # then sleep(8) — async!

# BW (apply after TDRPREset sleep)
CH1:BANdwidth:FILTer:OPTIMIZation FLAT
CH1:BANdwidth 1E9

# Horizontal (manual mode for record length control)
HORizontal:MODe MANual
HORizontal:RECOrdlength 20000

# Manual Math impedance
MATH:MATH1:TYPe ADVanced
MATH:MATH1:DEFine "50*(Ch1-Vb)/((2*Vm-Vb)-Ch1)"

# DO NOT USE for TDR:
#   AUTOSet EXECute              — returns 40 µs/div, useless
#   MEASUrement:MEAS1:TDR:*?    — times out
#   MATH:MATH1:DEFine?          — may time out on DPO714AX
```

---

## 14. Related Files

| File | Location | Purpose |
|------|----------|---------|
| `tdr_resolution_calculator_v3.html` | `docs/reference/` | Interactive risetime/resolution calculator — open in browser |
| `TDR_Datasheet_EN_US_61W-74085-0.pdf` | `docs/reference/` | Ordering info, option details, licensing (4/5/6-TDR) |
| `Basic_TDR_Z_line_with_TCS70902_and_DPO70000_or_DPO_7_Series.docx` | `docs/reference/` | DPO7/DPO70000 + TCS70902 setup guide (AE internal) |
| `2026-04-21_tdr_manual_math_formula__external_awg_stimulus_on_mso68b.md` | `PTA/lessons_learned/` | Math formula derivation, calibration values |
| `2026-04-21_tdr_setup_sequence__mso68b_with_external_awg70002b.md` | `PTA/lessons_learned/` | TDRPREset sequence, timing, gotchas |
| `2026-04-23_tdr_manual_impedance_analysis__mso68b__awg70002b__splitter.md` | `PTA/lessons_learned/` | Full analysis workflow, feature detection, Python script |
