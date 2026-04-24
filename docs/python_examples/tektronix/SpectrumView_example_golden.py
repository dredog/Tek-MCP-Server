# SpectrumView_example_refined.py
import time
import pyvisa as visa

def open_scope(resource="TCPIP::169.254.10.36::INSTR"):
    rm = visa.ResourceManager()
    while True:
        try:
            print("Connecting to", resource)
            inst = rm.open_resource(resource)
            inst.timeout = 20000
            inst.write_termination = '\n'
            inst.read_termination = '\n'
            print("IDN:", inst.query("*IDN?").strip())
            return inst
        except visa.VisaIOError as e:
            print("Connect failed:", e)
            time.sleep(1)

scope = open_scope()

print("For this, connect an antenna to CH4 (FM broadcast).")
print("We will look at the power of nearby FM radio stations.")

# Clear & default safely
scope.write("*CLS")
scope.write(":FAC")
scope.query("*OPC?")

# UI/basic setup
scope.write(":HEADER OFF")
scope.write(":SEL:CH4 ON")              # set (query with :SEL:CH4?)
scope.write(":SEL:CH1 OFF")
scope.write(":CH4:SCA 0.25")
scope.write(":HOR:SCA 1e-6")
scope.write(":TRIG:A:TYPE EDGE")
scope.write(":TRIG:A:EDGE:SOURCE CH4")
scope.write("TRIG:A:LEVel:CH4 0.5")     # level is channel-associated (query with TRIG:A:LEVel:CH4?)

# --- Spectrum View setup (Programmer Manual Table 2-46) ---
scope.write(":CH4:SV:STATE ON")                     # set; query with :CH4:SV:STATE?
scope.write(":CH4:SV:CENTERFrequency 98e6")         # set (Hz); query with :CH4:SV:CENTERFrequency?
scope.write("SV:SPAN 20e6")                         # set global span; query with SV:SPAN?

# RF Average trace display and averaging count
scope.write("SV:CH4:SELect:RF_AVErage ON")          # set; query ...:RF_AVErage?
scope.write("SV:CH4:RF_AVErage:NUMAVg 128")         # set; query ...:NUMAVg?

# Max hold display
scope.write("SV:CH4:SELect:RF_MAXHold ON")          # set; query ...:RF_MAXHold?

# Markers & peak table
scope.write("SV:MARKER:PEAK:STATE ON")              # set; query ...:STATE?
scope.write("SV:MARKER:PEAK:THReshold -60")         # set; query ...:THReshold?
scope.write('PEAKSTABle:ADDNew "Table1"')           # set; list with PEAKSTABle:LIST?

# Start acquisition and allow data to accumulate
scope.write(":ACQ:STATE ON")                        # set; query :ACQ:STATE?
time.sleep(2.0)

# Optional confirms
print("SV CH4 state:", scope.query(":CH4:SV:STATE?").strip())
print("Center (Hz) :", scope.query(":CH4:SV:CENTERFrequency?").strip())
print("Span (Hz)   :", scope.query("SV:SPAN?").strip())

# --- List detected FM peaks (query-only) ---
# SV:MARKER:PEAKS:FREQuency?  -> peak frequencies (Hz)
# SV:MARKER:PEAKS:AMPLITUDE? -> peak amplitudes (dB or SV:UNIts)
freqs_raw = scope.query("SV:MARKER:PEAKS:FREQuency?").strip()
amps_raw  = scope.query("SV:MARKER:PEAKS:AMPLITUDE?").strip()

def parse_csv(s):
    return [x for x in s.replace('\n','').split(',') if x] if s else []

freqs = parse_csv(freqs_raw)
amps  = parse_csv(amps_raw)

print("\nDetected peaks:")
for i, (f, a) in enumerate(zip(freqs, amps), 1):
    try:
        f_mhz = float(f) / 1e6
        print(f"  {i:2d}) {f_mhz:8.3f} MHz  |  {a} (units per SV:UNIts)")
    except ValueError:
        print(f"  {i:2d}) {f} Hz | {a}")

# Extra SV queries (query-only)
print("Start freq (Hz):", scope.query(":CH4:SV:STARTFrequency?").strip())
print("Stop  freq (Hz):", scope.query(":CH4:SV:STOPFrequency?").strip())
print("Span>BW?       :", scope.query(":CH4:SV:SPANABovebw?").strip())
print("Span<0Hz?      :", scope.query(":CH4:SV:SPANBELowdc?").strip())
