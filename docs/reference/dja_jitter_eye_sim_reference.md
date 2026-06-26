# DJA — Jitter, Eye, SIM & Mask on MSO5/6, DPO7 & TekScope PC

**Platform:** TekScope PC, MSO5 Series, MSO6 Series, modern DPO7 Series
**SCPI namespace:** `MEASUrement:` (DJA), `SIM:`, `EYEMASK:` / `MASK:`
**Source:** FAE field knowledge + PI Command Logger / .set reverse engineering (verified May 2026)
**Does NOT apply to:** legacy DPO7000/70000 series — those use the `DPOJET:` namespace and
SDLA Visualizer (see the DPOJET DPO70000 reference). This document is the modern counterpart.

> Empirical, hardware-verified (MSO68B FW 2.24.4 / TekScope PC v2.19.88). Several SIM and
> EYEMASK commands are **undocumented** — not in the programmer manual. Where a form here
> differs from the JSON command database, this document is authoritative for the modern
> Jitter & Eye Analysis path.

---

## 1. Platform, License & Probe Matrix

| Platform     | Max BW          | Jitter/Eye App           | SIM            |
|--------------|-----------------|--------------------------|----------------|
| TekScope PC  | software-defined| Jitter & Eye Analysis    | SIM app        |
| MSO5 Series  | 2 GHz           | Jitter & Eye Analysis    | SIM app        |
| MSO6 Series  | 8 GHz (6B: 10)  | Jitter & Eye Analysis    | SIM app        |
| DPO7 Series  | 33 GHz          | DPOJET (legacy)          | SDLA (legacy)  |

**Licenses** (`*OPT?` to verify installed): Jitter/Eye/TIE → `#-DJA`; SIM de-embed/add →
`#-SIM`; SIM + Tx/Rx equalization (CTLE/DFE/FFE) → `#-SIMA`; mask/limit → `#-MTM`.
DJA is included in MSO5/6 Automotive, Aerospace, Signal Integrity, Standards Compliance, and
Ultimate Pro bundles; MTM only in Signal Integrity, Aerospace, and Ultimate. If a license is
missing, measurements are unavailable or run in demo/trial mode.

**Probes:** MSO5/6 → TDP7700 TriMode (TDP7704/06/08/10 = 4/6/8/10 GHz). DPO7 → P7700
TriMode (P7713/16/20). Rule of thumb: probe BW ≥ 3× data rate for NRZ (pass the 3rd harmonic);
for compliance follow the standard's probe-BW requirement.

---

## 2. Clock Recovery

**Order matters — set `METHod` before `STAndard`.**

```
MEASUrement:CLOCKRecovery:METHod PLL          # ALWAYS first
MEASUrement:CLOCKRecovery:STAndard <preset>   # then the standard preset
```

| Method          | When to use                                            |
|-----------------|--------------------------------------------------------|
| `PLL`           | Standard for data signals; mimics a receiver CDR       |
| `CONSTANTCLOCK` | Clocks of known exact frequency; source characterization |
| `EXPLICITCLOCK` | A separate reference-clock channel is available        |

**Always use `PLL` for data signals.** Constant clock misattributes low-frequency phase
wander to RJ and inflates it badly (e.g. 7.4 ps vs 2.7 ps rms on the same 8 Gbps PRBS9
waveform). Do **not** set `CLOCKRecovery:MODel TYPE2` with a standard preset — the preset
already configures PLL type, loop BW, and JTF BW. Only set `MODel`/`LOOPBandwidth`/
`JTFBandwidth` when using `CUSTom`.

> **Contrast with DPOJET:** DJA uses **bare unquoted preset tokens** (`PCIE_GEN3`). DPOJET
> uses a **quoted `"NAME : RATE"`** string (`"PCI_E_GEN2 : 5.0G"`). Don't cross them.

### Standard presets (token → rate)

`ENET100` 125 Mb/s · `ENET1000` 1.25 Gb/s · `FW1394BS400B/800B/1600B` 491.5 M/983 M/1.966 G ·
`FBD1/2/3` 3.2/4.0/4.8 G · `FC133/266/531/1063/2125/4250/8500` · `IBA2500` 2.5 G ·
`IBA_GEN2` 5.0 G · `OC1/3/12/48` 51.8 M/155 M/622 M/2.488 G ·
`PCIE_GEN1/GEN2/GEN3` 2.5/5.0/8.0 G · `RIO125/250/3125` ·
`SAS15/3/6/12_NOSSC` and `_SSC` (1.5/3.0/6.0/12.0 G) ·
`SATA_GEN1/GEN2/GEN3` 1.5/3.0/6.0 G · `USB3` 5.0 G · `XAUI` 3.125 G/lane ·
`XAUI_GEN2` 6.25 G/lane · `CUSTom` (set `LOOPBandwidth` + `JTFBandwidth` manually).

No exact match → use the closest data-rate preset (e.g. generic 8 Gbps PRBS → `PCIE_GEN3`).
SSC variants set loop BW to track (or not track) spread-spectrum per the compliance spec.

---

## 3. Measurement Setup

```python
# 1. Clock recovery FIRST (global)
MEASUrement:CLOCKRecovery:METHod PLL
MEASUrement:CLOCKRecovery:STAndard PCIE_GEN3

# 2. Jitter Summary
MEASUrement:ADDMEAS JITTERSUMMARY
MEASUrement:MEAS1:SOUrce1 <CH<x>|REF<x>|MATH<x>>
MEASUrement:MEAS1:JITTERSummary:RJ 1
MEASUrement:MEAS1:JITTERSummary:DJ 1
MEASUrement:MEAS1:JITTERSummary:DDJ 1
MEASUrement:MEAS1:JITTERSummary:NPJ 1
MEASUrement:MEAS1:JITTERSummary:TJBER 1
MEASUrement:MEAS1:JITTERSummary:EYEWIDTHBER 1

# 3. Eye Height / Width (measured and @BER)
MEASUrement:ADDMEAS HEIGHT        # eye height (measured)
MEASUrement:ADDMEAS WIDTH         # eye width  (measured)
MEASUrement:ADDMEAS HEIGHTBER     # eye height @ BER (extrapolated, default 1e-12)
MEASUrement:ADDMEAS WIDTHBER      # eye width  @ BER (= UI − TJ@BER)
MEASUrement:MEAS<x>:SOUrce1 <CH<x>|REF<x>|MATH<x>>
```

### Querying Jitter Summary results (the SUBGROUP path)

**JITTERSUMMARY is not a scalar.** The standard results path returns `9.91E+37` (invalid).
Use the **SUBGROUP** path with string component keys — and **no `@` in the keys**:

```python
MEASUrement:MEAS1:SUBGROUP:RESUlts:CURRentacq:MEAN? "RJ"
MEASUrement:MEAS1:SUBGROUP:RESUlts:CURRentacq:MEAN? "DJ"
MEASUrement:MEAS1:SUBGROUP:RESUlts:CURRentacq:MEAN? "DDJ"
MEASUrement:MEAS1:SUBGROUP:RESUlts:CURRentacq:MEAN? "ISI"
MEASUrement:MEAS1:SUBGROUP:RESUlts:CURRentacq:MEAN? "NPJ"
MEASUrement:MEAS1:SUBGROUP:RESUlts:CURRentacq:MEAN? "TJBER"        # NOT "TJ@BER"
MEASUrement:MEAS1:SUBGROUP:RESUlts:CURRentacq:MEAN? "EyeWidthBER"  # NOT "EyeWidth@BER"
```

- `"TJ@BER"` / `"EyeWidth@BER"` (with `@`) return `9.91E+37`.
- `MEASUrement:MEAS1:JITTERSummary:DJ?` returns the **enable flag (0/1)**, not the value.
- For RJ/DJ/TIE as separate scalar badges, add them individually
  (`ADDMEAS RJ` → `MEAS<x>:RESUlts:CURRentacq:MEAN?`); the SUBGROUP path is only needed for
  JITTERSUMMARY.

> **Contrast with DPOJET:** the `SUBGROUP:RESULts` path is **MSO/DJA-only** and times out on
> DPO70000. DPOJET reads results via `DPOJET:MEAS<x>:RESULts:ALLAcqs:MEAN?`.

### HEIGHT vs HEIGHT@BER

`HEIGHT`/`WIDTH` = actual opening from the accumulated waveform DB → debug/characterization.
`HEIGHTBER`/`WIDTHBER` = extrapolated to target BER via the dual-Dirac model → compliance and
link-margin ("will it work?"). `HEIGHTBER`/`WIDTHBER` return `9.91E+37` if insufficient UIs
were accumulated.

---

## 4. Acquisition — Offline vs Live

**TekScope PC offline (no scope attached):** the `ACQuire` group does **not** apply.
Results compute automatically from a loaded REF waveform. Do not issue `ACQuire:STATE RUN`
or `ACQuire:STOPAfter`.

```python
# REF1:FILEPath "C:\path\to\waveform.wfm"   (or File > Recall > Reference Waveform)
MEASUrement:CLOCKRecovery:METHod PLL
MEASUrement:CLOCKRecovery:STAndard PCIE_GEN3
MEASUrement:ADDMEAS JITTERSUMMARY
MEASUrement:MEAS1:SOUrce1 REF1
```

**Live scope:** confirm the DUT/channels are active *before* triggering (a stopped or missing
signal yields `9.91E+37` everywhere).

```python
ACQuire:STOPAfter SEQuence
ACQuire:STATE RUN
*OPC?
MEASUrement:MEAS1:SUBGROUP:RESUlts:CURRentacq:MEAN? "RJ"
```

### UI / record-length requirements

| Analysis                | Minimum UIs |
|-------------------------|-------------|
| Eye diagram (visual)    | ~1,000      |
| RJ / DJ decomposition   | ~10,000     |
| TJ@BER-12 extrapolation | ~50,000+    |
| HEIGHTBER / WIDTHBER    | ~50,000+    |

Aim for **30,000 UI minimum** for eye/jitter work. Use **MANual** horizontal mode — AUTO
ignores record length and sample rate:

```python
HORizontal:MODE MANual
HORizontal:MODE:SAMPLERate 25E9          # always max sample rate
HORizontal:MODE:RECOrdlength 100000      # per data rate (table below)
```

| Data rate | UI     | 30k-UI time | Record length |
|-----------|--------|-------------|---------------|
| 1.25 Gbps | 800 ps | 24 µs       | 600,000       |
| 2.5 Gbps  | 400 ps | 12 µs       | 300,000       |
| 5.0 Gbps  | 200 ps | 6 µs        | 150,000       |
| 8.0 Gbps  | 125 ps | 3.75 µs     | 100,000       |
| 10 Gbps   | 100 ps | 3 µs        | 75,000        |
| 12.5 Gbps | 80 ps  | 2.4 µs      | 60,000        |

Harmonic check: NRZ fundamental = bitr/2; required SR ≥ 3 × (bitr/2). At 8 Gbps:
3 × 4 GHz = 12 GHz → 25 GS/s (12.5 GHz Nyquist).

---

## 5. Jitter Taxonomy (interpretation)

```
TJ (Total Jitter)
├── RJ  — random, Gaussian, unbounded (σ). Sources: oscillator phase noise, thermal.
│        TJ contribution = 2 × Q(BER) × RJσ
└── DJ  — deterministic, bounded, identifiable cause
    ├── DDJ/ISI — data-pattern-dependent; bandwidth-limitation signature
    ├── DCD     — duty-cycle distortion; threshold offset / driver asymmetry
    ├── PJ      — periodic; supply, SSC, or clock crosstalk (peaks in TIE spectrum)
    └── NPJ     — bounded uncorrelated; asynchronous crosstalk (raised TIE-spectrum floor)
```

Dual-Dirac: `TJ@BER = DJ + 2 × Q(BER) × RJσ`; the BER-vs-timing curve is the **bathtub**.
`Eye Width@BER = UI − TJ@BER`. Quick diagnostics: high DDJ/ISI + low RJ → channel BW limit
(consider SIM de-embed); high PJ with TIE-spectrum peaks → supply/SSC/clock crosstalk; high
DCD → threshold offset / Tx asymmetry; all `9.91E+37` → invalid setup (source, CR, license,
or UI count).

---

## 6. SIM — Signal Integrity Modeling (`SIM:` namespace)

SIM computes a Thevenin equivalent from the physical model (what you measured, including
fixtures/cables/probes), then applies the simulation model to produce a corrected waveform on
a MATH channel. **De-embed** removes things that are *not* the DUT (e.g. a 1 m coax to the
scope); **embed** adds things that *are* part of the DUT path to simulate a point you can't
probe. Equalization (CTLE/DFE/FFE) needs `#-SIMA`. (SDLA is the legacy DPO7000/70000 tool —
do not use it on modern platforms.)

> **SIM SCPI is undocumented and only partially reliable.** It is dependable for creating
> instances, setting sources, loading a saved JSON/.set, triggering calc, and querying — but
> **not** for building S-parameter block topology from scratch. Recommended workflow: build
> SIM once in the GUI, **Save As > Setup (.set)**, then automate by recalling that .set.

```python
# Reliable SIM SCPI
SIM:LIST?                                 # "NONE" | "SIM1" | "SIM1,SIM2"
SIM:ADDNEW "sim1"
SIM:DELete "SIM1"
SIM:SIM1:SOURCE1 <CH1-CH8|REF1-REF8>
SIM:SIM1:SOURCE2 <CH1-CH8|REF1-REF8>      # 4-port / dual
SIM:SIM1:LOAD "filename.json"             # short: LOA
SIM:SIM1:ISSIMCALCULATED?                 # UNINITIALIZED | TOCALCULATE | DONE
SIM:SIM1:ISSIMCALCULATED DONE             # execute (short: ISS DON)
MATH:MATH1:CREATOR?                       # "sim1simtp1" = de-embedded; "sim1phytp1" = raw physical

# Option A — recall a full saved .set (RECOMMENDED; restores complete topology)
RECAll:SESsion "C:/Users/Public/Tektronix/TekScope/my_sim.set"

# Option B — transfer JSON + load (source + calc only; no block topology rendering)
HORizontal:MODE MANual                    # SIM needs ≥50k pts; MANual before RECOrdlength
HORizontal:MODE:SAMPLERate 25E9
HORizontal:MODE:RECOrdlength 100000
FILESystem:WRITEFile "C:/Users/Public/Tektronix/TekScope/sim1.json",#NN<json-bytes>
SIM:ADDNEW "sim1"
SIM:SIM1:SOURCE1 CH1
SIM:SIM1:LOAD "sim1.json"
SIM:SIM1:ISSIMCALCULATED DONE
MATH:MATH1:CREATOR?                       # verify → "sim1simtp1"
```

S-parameter files: `.s2p` (2-port) / `.s4p` (4-port) Touchstone. TekScope ships examples at
`C:/Users/Public/Tektronix/TekScope/Applications/SIM/Example S-parameters/`. The .set file is
a **ZIP** containing `sim1Current.json` + referenced S-param files + `*_lrn.set` (full scope
state). In the JSON, the `s2pfile1` field accepts a relative filename (co-located, as in the
.set zip) or an absolute path. To chain a second S-param block, add it to the `blocks` array
and insert its ID into the `connections` string
(`"Block1-Block2-Block6-Block5-Block3-Block4"`).

```python
def sim_writefile_cmd(dest_path, sim_dict):
    """IEEE 488.2 block-format FILESystem:WRITEFile command for a SIM JSON dict."""
    import json
    b = json.dumps(sim_dict, separators=(',', ':')).encode('utf-8')
    header = f'#{len(str(len(b)))}{len(b)}'
    return f'FILESystem:WRITEFile "{dest_path}",{header}{b.decode("utf-8")}'
```

---

## 7. Mask & Limit Testing (`EYEMASK:` namespace, `#-MTM`)

Two **separate** mask command groups — using the wrong one is a common mistake:

| Group           | Controls                                   | Use for |
|-----------------|--------------------------------------------|---------|
| `MASK:MASK<x>`  | mask on the **waveform view**              | traditional raw-waveform mask |
| `EYEMASK:MASK<x>` | mask on the **Jitter & Eye eye-diagram plot** | HSS eye pass/fail (use this) |

**Loading a mask: the file loads via the `EYEMASK:MASK<x>:MASK "path"` property, not a
`RECAll`.** Send each command individually (batched semicolons get split in `RESULTO`):

```python
FILESystem:WRITEFile "C:/Users/Public/Tektronix/TekScope/my_mask.msk",#NN<data>
EYEMASK:MASK1:ENA 1
EYEMASK:MASK1:MASK "C:/path/mask.msk"      # .msk or .xml accepted
EYEMASK:MASK1:EMTY 0                        # mark populated (required)
MAINW:RESULTO "1;meas1;mask1;wvmask1"       # wire into results panel
MAINW:RRBI "mask1"                          # refresh badge
EYEMASK:MASK1:MASK?                         # verify load ("" = rejected)
EYEMASK:MASK1:COUNT:HITS?                   # total hits
EYEMASK:MASK1:TESt:STATUS?                  # PASS | FAIL | OFF
EYEMASK:MASK1:TESt:SAMple:THReshold <N>     # 0 = any hit fails
EYEMASK:MASK1:CREATor?                      # owning plot, e.g. "plot1"

# WRONG — these do NOT load the file:
# RECAll:EYEMASK "path",MASK1   (silently rejected)
# EYEMASK:MASK1:RECAll "path"   (silently rejected)
# EYEMASK:MASK1:ENAbled ON      (use ENA, not ENAbled)
```

**Built-in library** (check before building from scratch):
`C:/Users/Public/Tektronix/TekScope/Masks/` — e.g. `PCE_Rev3.msk` (PCIe Gen3 8.0 G TX),
`PCE_Rev20_RX.msk` (PCIe Gen2 5.0 G RX), plus Display Port, Ethernet, Fibre Channel, SAS,
SATA, InfiniBand, Serial RapidIO, FB-DIMM, 1394b, OBSAI folders. Point
`EYEMASK:MASK1:MASK` at any of them.

### .msk file format

A TekScope mask is a **single-line, semicolon-delimited SCPI string**. Required keys include
`:MASK:USER:WID <UI seconds>`, `:MASK:USER:BITR <bps>`, `:MASK:USER:VSCA/VPOS/VOFFS`,
`:MASK:USER:SEG1/2/3:POINTS <X,Y pairs in seconds,volts>`, and
`:MASK:AUTOSET:STANDARD <name|NONe>`. SEG1/SEG3 are full-UI-width rectangles (4 points);
SEG2 is a diamond/hexagon (4–8 points) — more points = tighter eye shape. Points are **actual
seconds and volts** (not normalized), vertices listed counterclockwise.

> Mask gotcha shared with DPOJET: fields like WID/BITR/AMP/SERIALTRIG/PATTERNBITS can reset
> the scope timebase, and `:MASK:AUTOSET:USER:TYP NORMALIZed` recenters all Y-coords to 0 V —
> omit it when the signal has a DC offset.

### Combined SIM + mask + jitter (the high-value workflow)

```python
# de-embed on MATH1 (SIM) → eye mask on MATH1 (MTM) → jitter summary on MATH1 (DJA)
EYEMASK:MASK1:ENA 1
EYEMASK:MASK1:MASK "C:/Users/Public/Tektronix/TekScope/Masks/PCE_Rev3.msk"
EYEMASK:MASK1:EMTY 0
MAINW:RESULTO "1;meas1;mask1;wvmask1"
MAINW:RRBI "mask1"
MEASUrement:CLOCKRecovery:METHod PLL
MEASUrement:CLOCKRecovery:STAndard PCIE_GEN3
MEASUrement:ADDMEAS JITTERSUMMARY
MEASUrement:MEAS1:SOUrce1 MATH1            # the de-embedded waveform
```

---

## 8. Known Gotchas (verified May 2026)

1. JITTERSUMMARY needs `SUBGROUP:RESUlts:CURRentacq:MEAN? "<component>"`; the standard
   `RESUlts:ALLAcqs:MEAN?` returns `9.91E+37`.
2. `@` in string keys (`"TJ@BER"`) returns `9.91E+37`; use `"TJBER"`, `"EyeWidthBER"`.
3. `JITTERSummary:DJ?` returns the enable flag (0/1), not the value.
4. Clock recovery: `METHod PLL` must precede `STAndard`, or the preset may not apply.
5. Do not set `CLOCKRecovery:MODel TYPE2` with a standard preset — it's set automatically.
6. TekScope PC offline: `ACQuire` commands do not apply.
7. Constant clock inflates RJ; always use PLL for data signals.
8. SIM needs ≥50k points; `HORizontal:MODE` must be `MANual` before `RECOrdlength` is
   accepted (AUTO silently ignores it).
9. SIM SCPI is undocumented; use PI Command Logger to discover commands the GUI emits.
10. SIM S-param blocks don't render when built via JSON/SCPI alone — set topology up in the
    GUI, then save and reload the `.set`.
11. After `ISSIMCALCULATED DONE`, confirm `MATH:MATH1:CREATOR?` = `"sim1simtp1"`; empty means
    SIM did not compute.
12. The SIM `.set` is a ZIP (`sim1Current.json` + S-param files + `_lrn.set`).

---

*Reference document for the TektronixMCP server. Place in `docs/reference/`.
DJA (`MEASUrement:`/`SIM:`/`EYEMASK:`) applies to MSO5/6, modern DPO7, and TekScope PC;
for legacy DPO7000/70000 jitter/eye use the DPOJET DPO70000 reference (`DPOJET:` namespace).*
