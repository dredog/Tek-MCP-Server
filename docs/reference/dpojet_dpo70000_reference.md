# DPOJET on DPO70000 Series — Consolidated Reference & Lessons Learned

**Platform:** DPO70000 Series, including DX and SX variants (validated on DPO75002SX / MSO73304DX)
**SCPI namespace:** `DPOJET:` (separate from the MSO `MEASUrement:` / DJA namespace)
**Source:** DPOJET Application Help 077-0048-31 (2022, 431 pp.) + empirical hardware validation
**Validated:** 2026-06-22 through 2026-06-25
**Applies to:** DPO7000, DPO7000C, DPO70000, DPO70000C, DPO70000D/DX, DPO70000SX,
DPO75002SX, DPO75902SX, DPO77002SX, DSA70000, MSO70000, MSO70000C, MSO70000DX, MSO73304DX
**Does NOT apply to:** modern DPO 7 Series (DPO714A/718A) and MSO5/6 — those use the
`MEASUrement:` DJA namespace (see the DJA reference).

> This single document supersedes and consolidates the six dated DPOJET lessons-learned
> files. It is empirical and hardware-verified; where a form here differs from the JSON
> command database, **this document is authoritative**. Several forms (the clock-recovery
> standard strings, the two-argument `DPOJET:EXPORT`, `DPOJET:STATE SINGLE`, the report
> subsystem, the binary-transfer `read_termination=''` workaround) are not documented in
> the programmer manual and were discovered through bus capture.

---

## 1. Platform Overview

DPOJET is a separate Java-based application running on top of the DPO70000 firmware. It
uses its own `DPOJET:` SCPI namespace — entirely separate from the `MEASUrement:`
namespace used by MSO 4/5/6 (DJA).

| Platform        | Jitter App | SCPI Namespace | Launch            |
|-----------------|------------|----------------|-------------------|
| DPO70000 series | DPOJET     | `DPOJET:`      | `DPOJET:ACTIVATE` |
| MSO 4/5/6 / modern DPO7 | DJA | `MEASUrement:` | Built-in, no launch |

A DPOJET workflow should never emit a `MEASUrement:` command, and vice-versa. Two
namespaces that look similar but are MSO-only and time out on DPO70000:
`MEASUrement:…`, `EYEMASK:…`, and the `SUBGROUP:RESULts` path.

---

## 2. Launch & Reset

```python
scope.write('DPOJET:ACTIVATE')          # no argument; correct launch
time.sleep(5.0)                          # Java app takes several seconds to initialize
scope.write('DPOJET:CLEARALLMeas')       # clear measurements before adding new ones
scope.write('DPOJET:CLEARALLPlots')      # clear plots before adding new ones

# WRONG — not required for DPOJET, may silently fail:
# scope.write('APPLication:ACTivate "DPOJET"')
```

---

## 3. Adding Measurements

```python
scope.write('DPOJET:ADDMeas <type>')
scope.write('DPOJET:MEAS<x>:SOUrce1 CH1')     # source is CH1–CH4
scope.query('DPOJET:NUMMeas?')                # how many measurement slots are defined
```

**Valid measurement types:**
`TIE`, `RJ`, `RJDirac`, `TJber`, `DJ`, `DJDirac`, `DDJ`, `PJ`, `DCD`, `NPJ`, `SRJ`,
`JITTERSummary`, `NOISESUMMARY`, `HEIght`, `WIDth`, `WIDTHBer`, `HEIGHTBer`,
`EYEHIGH`, `EYELOW`, `DATARATE`, `PERIod`, `FREQUENCY`, `MASKHits`, `QFACTOR`,
`ACRMS`, `HIGH`, `LOW`, `RISEtime`, `FALLtime`, `SKEW`

### JITTERSummary slot expansion (critical)

`JITTERSummary` is **not** a single measurement — it expands into **11 sequential slots**.
If added as MEAS1, the next `ADDMeas` occupies MEAS12 (not MEAS2).

| Slot | UI label    | Actual `MEAS<x>:NAME?` string |
|------|-------------|-------------------------------|
| 1    | TIE         | `tie1`                        |
| 2    | RJ          | `rj1`                         |
| 3    | RJ–δδ       | `rjdd1`                       |
| 4    | TJ@BER      | `tjber1`                      |
| 5    | DJ          | `dj1`                         |
| 6    | DJ–δδ       | `djdd1`                       |
| 7    | PJ          | `pj1`                         |
| 8    | DDJ         | `ddj1`                        |
| 9    | DCD         | `dcd1`                        |
| 10   | Width@BER   | `widthber1`                   |
| 11   | SRJ         | `srj1`                        |

> **Name-string note:** the actual `DPOJET:MEAS<x>:NAME?` strings contain **no `@` and no
> `δδ`** — it is `tjber1` (not `tj@ber1`) and `widthber1` (not `width@ber1`). The trailing
> number is an **instance counter, not a fixed `1`**: a second TJ@BER measurement is
> `tjber2`, a third `tjber3`, and so on. Never assume the suffix — build the name→slot map
> from `NUMMeas?` + `MEAS<x>:NAME?` discovery and keep track of which is which.

**Typical slot map when JITTERSummary is added first:**

| Slot  | Measurement |
|-------|-------------|
| 1–11  | JITTERSummary sub-components (above) |
| 12    | HEIght      |
| 13    | WIDth       |
| 14    | HEIGHTBer   |
| 15    | WIDTHBer    |
| 16    | DATARATE    |

**Never hard-code slot numbers after JITTERSummary.** Discover them dynamically — querying
beyond the last defined slot causes a VISA timeout (up to 99 slots are supported):

```python
total = int(scope.query('DPOJET:NUMMeas?'))
slots = {}
for x in range(1, total + 1):
    slots[scope.query(f'DPOJET:MEAS{x}:NAME?').strip()] = x
```

---

## 4. Clock Recovery — Full Correct Workflow

Add **all** measurements first, configure clock recovery on MEAS1 only, then propagate with
`APPLYAll`. Setting CR per-slot during `ADDMeas` does not propagate correctly.

```python
# 1. Add ALL measurements first
scope.write('DPOJET:ADDMeas JITTERSummary')
scope.write('DPOJET:MEAS1:SOUrce1 CH1')
# ... all other measurements ...

# 2. Set clock recovery on MEAS1 only
scope.write('DPOJET:MEAS1:CLOCKRecovery:METHod STANDARD')         # PLL Standard BW
scope.write('DPOJET:MEAS1:CLOCKRecovery:MODel TWO')               # Type II PLL (ONE|TWO)
scope.write('DPOJET:MEAS1:CLOCKRecovery:STAndard "PCI_E_GEN2 : 5.0G"')
# Optional fine control:
# scope.write('DPOJET:MEAS1:CLOCKRecovery:LOOPBandwidth <NR3>')   # custom loop BW
# scope.write('DPOJET:MEAS1:RJDJ:BER 1E-12')                      # RJ/DJ target BER
# scope.write('DPOJET:MEAS1:BER:TARGETBER 1E-12')                 # TJ@BER target

# 3. Propagate MEAS1 settings to all other measurements
scope.write('DPOJET:APPLYAll CLOCKRecovery, MEAS1')
```

### CLOCKRecovery:METHod options

| SCPI value    | UI label                |
|---------------|-------------------------|
| `STANDARD`    | PLL – Standard BW       |
| `CUSTOM`      | PLL – Custom BW         |
| `CONSTMEAN`   | Constant Clock – Mean   |
| `CONSTMEDIAN` | Constant Clock – Median |
| `CONSTFIXED`  | Constant Clock – Fixed  |
| `EXPEDGE`     | Explicit Clock – Edge   |
| `EXPPLL`      | Explicit Clock – PLL    |
| `BEHAVIORAL`  | Behavioral              |

### CLOCKRecovery:STAndard — exact string format

**Format:** `"<NAME> : <RATE>"` — quoted, with space-colon-space separator.
**Not documented in the manual** — discovered empirically. The bare name token alone (e.g.
`"PCI_E_GEN2"`) is **silently rejected and falls back to the PCI-E 2.5G default**.

| SCPI String           | Protocol        | Rate     |
|-----------------------|-----------------|----------|
| `"PCI-E : 2.5G"`      | PCIe Gen1       | 2.5 Gbps |
| `"PCI_E_GEN2 : 5.0G"` | PCIe Gen2       | 5.0 Gbps |
| `"USB 3.0 : 5.0G"`    | USB 3.0         | 5.0 Gbps |
| `"SerATAG3 : 6.0G"`   | SATA Gen3       | 6.0 Gbps |
| `"IBA_GEN2 : 5.0G"`   | InfiniBand Gen2 | 5.0 Gbps |

```python
scope.write('DPOJET:MEAS1:CLOCKRecovery:STAndard "PCIE_GEN2"')       # wrong name
scope.write('DPOJET:MEAS1:CLOCKRecovery:STAndard "PCI_E_GEN2"')      # missing rate → 2.5G default
scope.write('DPOJET:MEAS1:CLOCKRecovery:STAndard PCI_E_GEN2 : 5.0G') # unquoted → rejected
```

### APPLYAll — correct syntax

```
DPOJET:APPLYAll {FILTers | CLOCKRecovery | RJDJ}, MEAS<x>
```

```python
scope.write('DPOJET:APPLYAll CLOCKRecovery, MEAS1')   # correct
scope.write('DPOJET:APPLYAll FILTers, MEAS1')
scope.write('DPOJET:APPLYAll RJDJ, MEAS1')
# DPOJET:CLOCKRecovery:APPLYToAll  — does NOT exist (hallucinated). Use APPLYAll above.
```

---

## 5. Reference Levels

```python
scope.write(f'DPOJET:REFLevels:CH1:ABSolute:RISEHigh {V_HIGH:.4E}')
scope.write(f'DPOJET:REFLevels:CH1:ABSolute:RISELow  {V_LOW:.4E}')
scope.write(f'DPOJET:REFLevels:CH1:ABSolute:RISEMid  {V_CENTER:.4E}')
scope.write(f'DPOJET:REFLevels:CH1:ABSolute:FALLHigh {V_HIGH:.4E}')
scope.write(f'DPOJET:REFLevels:CH1:ABSolute:FALLLow  {V_LOW:.4E}')
scope.write(f'DPOJET:REFLevels:CH1:ABSolute:FALLMid  {V_CENTER:.4E}')

# Or let DPOJET auto-set levels from the signal:
scope.write('DPOJET:REFLevels:CH1:AUTOSet')   # per-channel
scope.write('DPOJET:REFLevels:AUTOSet')        # all channels
```

---

## 6. Acquisition — Scope and DPOJET Are Separate Engines

The scope acquisition and DPOJET are **two independent engines**. Filling the WFMDB does not
auto-trigger DPOJET — you must single-trigger DPOJET after the scope acquisition completes.

```python
scope.write('ACQuire:MODe WFMDB')          # density database — REQUIRED for DPOJET
scope.write('ACQuire:STOPAfter SEQuence')  # single acquisition
scope.write('ACQuire:STATE RUN')           # use write(), NOT send() — send() appends *OPC? and stalls

while scope.query('ACQuire:STATE?').strip() != '0':
    time.sleep(0.25)

scope.write('DPOJET:STATE SINGLE')         # process one cycle (== "Single" in the DPOJET panel)
time.sleep(3.0)                            # or poll DPOJET:STATE?
```

`DPOJET:STATE` options: `{RUN | SINGLE | RECALC | CLEAR | STOP}`.
`DPOJET:STATE SINGLE` returns **"Invalid Measurement"** if the scope is in SAMple mode —
it requires the WFMDB density database. Use `scope.write()` (not `send()`) for
`ACQuire:STATE STOP` during a running acquisition.

**Acquisition sizing:** at 50 GS/s, 10 µs/div = 5 M points ≈ 250 k UI at 5 Gbps — sufficient
for DPOJET jitter decomposition.

---

## 7. Eye Diagram Plot and Export

```python
scope.write('DPOJET:ADDPlot EYE, MEAS1')
scope.write('DPOJET:PLOT1:EYE:STATE 1')                 # make plot visible
scope.write('DPOJET:PLOT1:EYE:HORizontal:AUTOscale 1')
scope.write('DPOJET:PLOT1:EYE:MASKfile "C:/Temp/mask.msk"')
scope.write('DPOJET:PLOT1:EYE:STATE 1')                 # re-assert after loading a mask
scope.query('DPOJET:NUMPlot?')                          # number of active plots
scope.query('DPOJET:PLOT1:TYPe?')                       # confirm plot type / source
scope.query('DPOJET:PLOT1:SOUrce?')
```

### Two export paths — choose by reliability

```python
# A) Export a specific plot to an exact path (two-argument form):
scope.write('DPOJET:EXPORT PLOT1, "C:/Temp/eye_plot.png"')      # exact rendered eye, heat map + mask overlay
scope.write('DPOJET:EXPORTRaw PLOT1, "C:/Temp/eye_data.csv"')   # 2D density histogram CSV
#   EXPORTRaw requires the Plot window to be OPEN, else no file is generated.
#   DPOJET:EXPORT is a two-argument command: DPOJET:EXPORT <plot>, "<path>".
#   The path you pass IS the file written — do not read back an assumed name.

# B) Save ALL plots to a folder (more reliable for binary transfer):
scope.write('DPOJET:SAVEALLPLOTS "C:/Temp/folder/"')
#   Auto-names files PLOT1.png, PLOT2.png, ... in that folder.
#   On DPO70000 this is more reliable than DPOJET:EXPORT for subsequent binary readback.
```

**`DPOJET:EXPORT` formats:** jpeg, jpg, tif, tiff, bmp, emf, .mat, .csv, png (by extension;
default png). Prefer `EXPORT`/`SAVEALLPLOTS` (rendered PNG) over `EXPORTRaw` CSV
reconstruction for the eye image.

---

## 8. Result Readback & Population Control

```python
# Per-measurement scalars
scope.query(f'DPOJET:MEAS{x}:RESULts:ALLAcqs:MEAN?')
scope.query(f'DPOJET:MEAS{x}:RESULts:ALLAcqs:MAX?')
scope.query(f'DPOJET:MEAS{x}:RESULts:ALLAcqs:MIN?')
scope.query(f'DPOJET:MEAS{x}:RESULts:ALLAcqs:PK2PK?')
scope.query(f'DPOJET:MEAS{x}:RESULts:ALLAcqs:STDDev?')
scope.query(f'DPOJET:MEAS{x}:RESULts:ALLAcqs:POPUlation?')   # UI/sample count
scope.query(f'DPOJET:MEAS{x}:NAME?')
scope.query(f'DPOJET:MEAS{x}:DISPLAYNAME?')
scope.query(f'DPOJET:MEAS{x}:DATA?')

# Aggregate
scope.query('DPOJET:RESULts:GETALLResults?')
scope.query('DPOJET:RESULts:STATus?')
scope.write('DPOJET:RESULts:VIew SUMmary')     # {SUMmary | DETails}

# Invalid result sentinel: 9.91E+37 — treat as NaN

# Population control (accumulate statistics over many acquisitions)
scope.write('DPOJET:POPULATION:STATE 1')
scope.write('DPOJET:POPULATION:LIMIT <count>')
scope.write('DPOJET:POPULATION:LIMITBY UI')    # {UI | ACQuisitions | SEConds}

# Source autoset (auto-find vertical/horizontal settings for the signal)
scope.write('DPOJET:SOURCEAutoset')
scope.write('DPOJET:SOURCEAutoset:HORizontal:UICount <NR3>')
```

---

## 9. Report Generation

> The report subsystem is **not in the JSON command database** — this doc is the only
> reference for it. Note `DPOJET:REPORT EXECute` has **no colon** before `EXECute`.

```python
scope.write('DPOJET:REPORT:DETailedresults 1')
scope.write('DPOJET:REPORT:ENABlecomments 1')
scope.write('DPOJET:REPORT:REPORTName "DPOJET_5Gbps_run01"')
scope.write('DPOJET:REPORT:PASSFailresults 1')
scope.write('DPOJET:REPORT EXECute')           # NOTE: no colon before EXECute

import re, time
while True:
    raw = scope.query('DPOJET:REPORT:STATE?')
    state = re.sub(r'[^A-Za-z]', '', raw).upper()   # response has non-ASCII garbage chars
    if state == 'DONE':
        break
    time.sleep(0.5)

# Retrieve the XML report — binary transfer; see Section 13 for the read_termination='' fix
xml = read_binary(scope, 'DPOJET:REPORT:GETXMLReport?')
```

**Gotcha:** `DPOJET:REPORT:STATE?` returns non-ASCII garbage characters around
`DONE`/`INPROGRESS`; strip non-alpha (`re.sub(r'[^A-Za-z]', '', resp).upper()`) before
comparing. `GETXMLReport?` is a binary transfer and needs the `read_termination=''` handling
in Section 13 (otherwise it returns 0 bytes).

---

## 10. Mask Files (.msk)

Only `SEG<n>:POINTS` lines are required by DPOJET. Other fields (WID, BITR, AMP, SERIALTRIG,
PATTERNBITS) are ignored by DPOJET but trigger the scope's own mask engine and can **reset
the timebase** — omit them.

```
:MASK:USER:LAB "MyMask";
:MASK:USER:SEG1:POINTS -1.0E-10,0.5000,1.0E-10,0.5000,1.0E-10,0.8000,-1.0E-10,0.8000;
:MASK:USER:SEG2:POINTS -3.5E-11,0.3500,0,0.2800,3.5E-11,0.3500,0,0.4200;
:MASK:USER:SEG3:POINTS -1.0E-10,-0.0800,1.0E-10,-0.0800,1.0E-10,0.0200,-1.0E-10,0.0200;
```

**SEG2 diamond — correct 4-point format:** `(-w, mid), (0, mid-h), (+w, mid), (0, mid+h)`.
Left/right tips use `±w`; top/bottom use `x=0`.

**More mask gotchas:**
- `MASK:AUTOSet:USER:TYPe NORMALIZed` recenters all y-coordinates to 0 V — **omit when the
  signal has a DC offset**, or the mask lands in the wrong place.
- Built-in PCIe 2.0 RX mask lives at
  `C:/Users/Public/Tektronix/TekApplications/PCI Express/Masks/Rev2.0/PCE_RX.msk` — y-coords
  must be rescaled for signals with a DC offset.
- `EYEMASK:…` does **not** exist on DPO70000 (MSO/TekScope PC only). On DPOJET, load masks
  via `DPOJET:PLOT1:EYE:MASKfile "path"`.

**Transfer mask to instrument:**

```python
payload = msk_content.encode('ascii')
n = len(payload)
header = f'#{len(str(n))}{n}'
scope.write_raw(f'FILESystem:WRITEFile "{MASK_PATH}",{header}'.encode('ascii') + payload + b'\n')
```

---

## 11. Horizontal CONStant Mode (DPO70000)

On the DPO70000 the way to hold sample rate constant is `HORizontal:MODe CONStant` (the
DPO70000 equivalent of the MSO 4/5/6 `HORIZONTAL:MODE MANUAL` + `CONFIGURE` workflow). Order
is critical.

```python
scope.write(f'HORizontal:MODe:SCAle {H_SCALE:.4E}')   # 1. time/div FIRST (NOT HORizontal:SCAle)
scope.query('*OPC?')
scope.write('HORizontal:MODe CONStant')               # 2. lock sample rate
scope.query('*OPC?')
scope.write(f'HORizontal:MODe:SAMPLERate {SR:.4E}')   # 3. set rate
scope.query('*OPC?')

sr = float(scope.query('HORizontal:MODe:SAMPLERate?'))  # correct readback in CONStant mode
rl = float(scope.query('HORizontal:RECOrdlength?'))
```

| Command                       | Behavior on DPO70000                       |
|-------------------------------|--------------------------------------------|
| `HORizontal:SCAle`            | Resets to AUTO, overwrites sample rate     |
| `HORizontal:MODe:SCAle`       | Sets time/div within current mode          |
| `HORizontal:SAMPLERate?`      | Returns NaN in CONStant mode               |
| `HORizontal:MODe:SAMPLERate?` | Correct readback in CONStant mode          |

**DPO75002SX limits:** 100 GS/s (1 ch), 50 GS/s (2 ch).

---

## 12. Binary File Transfer (READFile / GETXMLReport)

> **⚠ UNRESOLVED — binary readback was still failing as of 2026-06-25.** Two conflicting
> descriptions exist and **neither is confirmed working**: (a) `FILESystem:READFile` returns a
> standard IEEE-488.2 block (`#<n><ddd><data>`) that must be stripped; (b) it returns raw
> bytes with **no** block header, and `read_raw()` stops early because the PNG header bytes
> 0–5 are `89 50 4E 47 0D 0A`, so byte 6 (`0x0A`) is treated as a line terminator — addressed
> by setting `read_termination=''`. Approach (b) is the leading candidate and is shown below,
> but treat it as unverified. The same uncertainty applies to `DPOJET:REPORT:GETXMLReport?`.
> Run the diagnostic at the end of this section to determine which case your firmware
> actually produces before relying on either path.

```python
def read_binary(scope, cmd, timeout_ms=30_000):
    prev_term, prev_to = scope.read_termination, scope.timeout
    scope.read_termination = ''        # do not treat 0x0A in binary as a terminator
    scope.timeout = timeout_ms          # file reads need a long timeout
    try:
        scope.write(cmd)
        raw = scope.read_raw()
    finally:
        scope.read_termination, scope.timeout = prev_term, prev_to
    return raw

# Applies to both FILESystem:READFile "path" and DPOJET:REPORT:GETXMLReport?
# query_binary_values fails here: header_fmt='ieee' (no # header) and header_fmt='empty'
# both stop at the newline. Only read_termination='' + read_raw() works.

# Validate a PNG before saving:
if len(raw) < 100 or raw[:4] != b'\x89PNG':
    print(f'[WARN] Not a valid PNG ({len(raw)} bytes): {raw[:40]}')
```

A 0-byte readback usually means the file does not exist at the path given (verify the exact
filename the export wrote, e.g. `PLOT1.png` from `SAVEALLPLOTS`) or the newline-termination
issue above.

**Diagnostic — determine which case your firmware actually produces (run once):**

```python
scope.timeout = 30_000
prev = scope.read_termination
scope.read_termination = ''                      # candidate (b)
scope.write('FILESystem:READFile "C:/Temp/known_small.png"')
raw = scope.read_raw()
scope.read_termination = prev
print('first 8 bytes:', raw[:8].hex(' '), '| total len:', len(raw))
# raw[0:1] == b'#'        → IEEE block header present → use approach (a) (strip header)
# raw[:4]  == b'\x89PNG'  → no header, data starts immediately → approach (b) is correct
# len ≈ 6 / truncated     → termination handling is still cutting the read short
```

---

## 13. Common Wrong Commands vs Correct Equivalents

| Wrong                                          | Correct                                        |
|------------------------------------------------|------------------------------------------------|
| `APPLication:ACTivate "DPOJET"`                | `DPOJET:ACTIVATE`                              |
| `MEASUrement:ADDMEAS RJ` (adds to scope, not DPOJET) | `DPOJET:ADDMeas RJ`                      |
| `MEASUrement:CLOCKRecovery:…` (scope-global)   | `DPOJET:MEAS<x>:CLOCKRecovery:…` (per-meas)    |
| `DPOJET:CLOCKRecovery:APPLYToAll`              | `DPOJET:APPLYAll CLOCKRecovery, MEAS1`         |
| `DPOJET:PLOTs:SHOW ON` (does not exist)        | `DPOJET:PLOT1:EYE:STATE 1`                     |
| `EYEMASK:MASK1:ENA 1` (MSO/TekScope only)      | `DPOJET:PLOT1:EYE:MASKfile "path"`             |
| `SUBGROUP:RESULts …` (MSO only → timeout)      | `DPOJET:MEAS<x>:RESULts:ALLAcqs:…`             |
| `STAndard "PCIE_GEN2"` / `"PCI_E_GEN2"`        | `STAndard "PCI_E_GEN2 : 5.0G"` (quoted NAME:RATE) |
| `HORizontal:SCAle` in CONStant mode            | `HORizontal:MODe:SCAle`                        |
| `HORizontal:SAMPLERate?` in CONStant mode      | `HORizontal:MODe:SAMPLERate?`                  |
| `ACQuire:MODe SAMple` for DPOJET               | `ACQuire:MODe WFMDB`                           |
| `DPOJET:STATE SINGLE` in SAMple mode           | Fill WFMDB first, then `DPOJET:STATE SINGLE`   |
| `send(scope, 'ACQuire:STATE STOP')` during run | `scope.write('ACQuire:STATE STOP')` (no OPC)   |
| `DPOJET:REPORT:EXECute` (with colon)           | `DPOJET:REPORT EXECute` (no colon)             |
| MEAS2 = HEIght after JITTERSummary             | MEAS12 = HEIght (JITTERSummary uses MEAS1–11)  |
| Hard-coding slots after JITTERSummary          | `DPOJET:NUMMeas?` + `MEAS<x>:NAME?` discovery  |
| `query_binary_values(header_fmt='ieee')`       | `read_termination=''` + `read_raw()` (Section 12) |

---

*Reference document for the TektronixMCP server. Place in `docs/reference/`.
DPOJET (`DPOJET:` namespace) applies to DPO7000/DPO70000-series instruments (incl. DX/SX);
for MSO 4/5/6 and modern DPO7 jitter/eye work use the `MEASUrement:` (DJA) reference.*
