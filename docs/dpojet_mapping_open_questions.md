# DPOJET → MSO 4/5/6 Migration: Open Questions

These items need scope verification or domain expertise to finalize the mapping in `dpojet_commands.json`.

---

## 1. DPOJET:DIRacmodel — Concept Change

- **Legacy:** `ON | OFF` (enable/disable Dirac model)
- **Modern:** `MEASUrement:DIRacmodel` → `PCIExpress | FIBREchannel` (select model variant)
- **Question:** Legacy is a toggle, modern is a model selector. Is there a separate enable/disable on MSO, or did the concept fundamentally change to "which Dirac model" rather than "use Dirac model yes/no"?

## 2. DPOJET:MEAS\<x\>:BITCfgmethod — Different Concepts?

- **Legacy:** `AUTO | MANUAL` (automatic vs manual bit configuration)
- **Modern:** `MEASUrement:MEAS<x>:BITCfgmode` → `MEAN | MODE` (statistical method for bit measurement)
- **Question:** These appear to be different things entirely. Should the legacy AUTO/MANUAL map to `PATTERNDETECTION` (AUTO/MANUAL) or `BITAbsolute` instead? Or is BITCfgmode genuinely the replacement with a redefined purpose?

## 3. Filter SPEC — Shape vs Order Paradigm

- **Legacy:** `DPOJET:MEAS<x>:FILTers:HIGHPass:SPEC` / `LOWPass:SPEC` → `BRICKWALL | GAUSSIAN`
- **Modern:** Same command path → `NONE | FIRST | SECOND | THIRD` (filter order)
- **Question:** Legacy specifies filter shape (brickwall vs gaussian). Modern specifies filter order (1st/2nd/3rd). Is there a separate filter shape setting elsewhere on MSO 4/5/6, or is this truly a paradigm shift where filter shape is no longer user-selectable?

## 4. CLOCKRecovery:NOMINALOFFset — Numeric to Enum

- **Legacy:** `<NR3>` numeric value, with sub-commands `AUTO?`, `MANual`, `Recalctype`, `SELECTIONtype`
- **Modern:** `MEASUrement:MEAS<x>:CLOCKRecovery:NOMINALOFFset` → `AUTO | MANUAL` (enum selector only)
- **Question:** Legacy allowed setting an actual numeric offset value via the `:MANual` sub-command. Modern only has AUTO/MANUAL selector. Where does the actual numeric offset value get set on MSO 4/5/6 when MANUAL mode is selected?

## 5. PhaseNoise HIGHLimit / LOWLimit — Inferred Mapping

- **Legacy:** `DPOJET:MEAS<x>:PHASENoise:HIGHLimit` and `PHASENoise:LOWLimit`
- **Modern (proposed):** `MEASUrement:MEAS<x>:EDGES:UPPERFREQuency` and `EDGES:LOWERFREQuency`
- **Question:** This mapping is inferred from command names and the fact that phase noise frequency limits would logically map to upper/lower frequency bounds. Needs scope verification that these are the same concept (integration frequency range for phase noise measurement).

## 6. Missing DDR Measurement Types

The following DPOJET DDR measurement types are **not present** in the modern `MEASUrement:ADDMEAS` option list:

| Legacy Type | Notes |
|---|---|
| `DDRTDQSQ` | tDQSQ-Diff measurement |
| `DDRTDQSS` | tDQSS measurement |
| `DDRTHZDQ` | tHZDQ measurement |
| `DDRTLZDQ` | tLZDQ measurement |
| `DDRVID` | VID(ac) — note DDR3VIX→DDRVIXAC exists |
| `DDRSETUPSE` | Single-ended DDR setup |
| `DDRHOLDSE` | Single-ended DDR hold |

**Question:** Are these available under different names, behind a specific DDR option license, or handled by TekExpress DDR compliance application? The differential variants (DDRSETUPDIFF, DDRHOLDDIFF) do exist.

## 7. PCIe / USB / GDDR5 Compliance Measurements (~30 types)

All of the following are flagged as "requires TekExpress" since they don't appear in the modern ADDMEAS list:

- **PCIe (13):** PCIETXDIFFPP, PCIETX, PCIETXFALL, PCIETXRISE, PCIETMINPULSE, PCIEDEEMPH, PCIEUI, PCIEMEDMXJITTER, PCIERFMISMCH, PCIEMAXMINRATIO, PCIESSCPROFILE, PCIESSCFREQDEV, PCIEACCOMMONMODE
- **USB (10):** USBVTXDIFFPP, USBTCDRSLEW, USBTMINPULSETJ, USBTMINPULSEDJ, USBSSCMODRATE, USBSSCFREQDEVMAX, USBSSCFREQDEVMIN, USBSSCPROFILE, USBUI, USBACCOMMONMODE
- **GDDR5 (3):** GDDR5TBURSTCMD, GDDR5TCKSRE, GDDR5TCKSRX
- **Transmitter (8):** TTXDDJ, TTXUTJ, TTXUDJDD, TTXUPWTJ, TTXUPWDJDD, VTXEQNO, VTXEIEOS, PS21TX

**Question:** Is the TekExpress assumption correct for all of these? Are any available natively with the DJA option on MSO 4/5/6?

---

## Additional Minor Uncertainties

- `DPOJET:HALTFreerunonlimfail` — may map to ACTONEVent or pass/fail system
- `DPOJET:SEQUencing:STATE` — may map to ACQuire:SEQuence
- `DPOJET:MEAS<x>:DDR:MPERCycle` / `NPERCycle` — may map to TCKAVG or similar
- `DPOJET:MEAS<x>:MEASStart` — may map to GATing:STARTtime
- `DPOJET:QUALIFY:GATE` (BETWEEN/OUTSIDE) — unclear modern equivalent

---

*Generated 2025-02-17 from dpojet_commands.json v2.0 cross-referenced against mso_2_4_5_6_7_commands.json*
