#import serial 
import threading
import logging 
import queue
from datetime import datetime
from os.path import exists
import pyvisa as visa
import time
import logging.handlers as handlers

def initialize_scope():
    rm = visa.ResourceManager()
    res = rm.list_resources()
    print(res)
    
    expected_scope = "TCPIP0::169.254.11.68::inst0::INSTR"
    #expected_scope = "TCPIP0::169.254.8.46::inst0::INSTR"
    #expected_scope = "TCPIP0::169.254.48.58::INSTR"
    #expected_scope = "TCPIP::192.168.1.145::INSTR"
    #expected_scope = "TCPIP0::169.254.48.24::inst0::INSTR"
    #expected_scope = "USB::0x0699::0x0527::C034952::INSTR"
    #expected_scope = "GPIB0::4::INSTR"
    #expected_scope = "GPIB0::11::INSTR"
    if expected_scope in res: 
        print("Expected scope in list")
    try:
        print("Attempting to connect to scope...")
        scope = rm.open_resource(expected_scope)
        print("Connected to " + str(scope))
        scope.timeout = 20000
        scope.write_termination = '\n'
        scope.read_termination = '\n'
        id = str(scope.query("*IDN?"))
        print(id)

        
        return scope
    except visa.VisaIOError as e:
    
        print("Error occurred.. ", e)
        scope.close()
        return initialize_scope()


scope = initialize_scope()
print("\nThis program uses the internal AFG to generate a 1 MHz square wave,")
print("then sets up the scope to measure freq and period on channel 1 and a delay between ch1 and ch2\n")
print("For this to work, you need a BNC cable to the AFG out on the back that needs to be split")
print("with the signal going to channels 1 and 2. Channel 2 needs to have an extra cable inthe path to simulate a delay.\n\n")

scope.write(':FAC')
scope.query("*OPC?")  # long feactory reset operation, wait for it to complete before proceeding

scope.write(':HEADER OFF')
scope.write(':SEL:CH1 ON')
scope.write(':SEL:CH2 ON')
scope.write(':SEL:CH3 OFF')
scope.write(':SEL:CH4 OFF')

# Setup the internal AFG to output a 10 MHz square wave with 1 V amplitude and 500 mV offset, into a 50 ohm cable.
# Note that you should set the impedance before the amplitude and offset because when you change the impedance, it changes the amplitude.
scope.write(':AFG:OUTP:LOA:IMPED FIFty')
scope.write(':AFG:FUNC SQUare')
scope.write(':AFG:FREQuency 10000000')
scope.write(':AFG:AMPLitude 1.0')
scope.write(':AFG:OFFSet 0.5')

# Turn on the AFG output to continuous mode.
scope.write(':AFG:OUTP:MOD CONT')
scope.write(':AFG:OUTP:STATE ON')
print("AFG output has been set to 10 MHz square wave 500 mVp-p\n")
input("Press Enter to continue.\n\n")

# Set CH1 vertical scale
scope.write(':CH1:SCA 0.1250000')
scope.write(':CH1:OFFS 0.500000')
scope.write(':CH1:POS 0.000000')
scope.write(':CH1:TERMination 50')
scope.write(':CH1:COUP DC')

# Set CH2 vertical scale
scope.write(':CH2:VOL 0.125000')
scope.write(':CH2:POS 0.000000')
scope.write(':CH2:TERMination 50')
scope.write(':CH2:OFFS 0.500000')
scope.write(':CH2:COUP DC')

# Set the horizontal scale
scope.write(':HOR:MAI MAI')
scope.write(':HOR:MAI:SCA 5E-8')
scope.write(':HOR:TRIG:POS 50.000000')

# Set to trigger on CH1 rising edge
scope.write(':TRIG:MAI:MOD NORM')
scope.write(':TRIG:MAI:TYP EDGE')
scope.write(':TRIG:MAI:EDGE:SOU CH1')
scope.write(':TRIG:MAI:EDGE:COUP DC')
scope.write(':TRIG:MAI:EDGE:SLO RIS')
scope.write(':TRIG:MAI:LEV .450000')
scope.write(':ACQ:STOPA SEQ')
scope.write(':ACQ:STATE ON')
scope.query("*OPC?") # *OPC? when we do a single acquisition to ensure waveform is captured before we do any measurements on it.

#Setup on-screen Delay measurement
scope.write(':MEASU:MEAS1:TYP DELAY')
scope.write(':MEASU:MEAS1:DEL:DIRE FORW')
scope.write(':MEASU:MEAS1:DEL:EDGE1 RIS')
scope.write(':MEASU:MEAS1:DEL:EDGE2 RIS')
scope.write(':MEASU:MEAS1:SOURCE1 CH1')
scope.write(':MEASU:MEAS1:SOURCE2 CH2')

# Same as the on-screen measurement but this is Immediate measurement type does not show on the screen (runs slightly faster).
scope.write(':MEASU:IMM:TYP DELAY')
scope.write(':MEASU:IMM:DEL:DIRE FORW')
scope.write(':MEASU:IMM:DEL:EDGE1 RIS')
scope.write(':MEASU:IMM:DEL:EDGE2 RIS')
scope.write(':MEASU:IMM:SOURCE1 CH1')
scope.write(':MEASU:IMM:SOURCE2 CH2')

# Move the trigger point to 10% (was 50%) and re-acquire
scope.write(':HOR:POS 10.000000')
scope.write(':ACQ:STATE ON')
scope.query("*OPC?")

# Fetch and display measurements on this console
print("MEASU:IMM:TYPE? " + scope.query(":MEASU:IMM:TYPE?"))
print("Delay measurement with default % levels")
print("Delay between ch1 and ch2: " + scope.query(":MEASU:IMM:VAL?") + "\n")

# Change reflevel for CH1 to an absolute number or 0.45, slightly below the default of 50% for rise time
print("\nChanging CH1 RefLevel to 0.45 on rising edge.")
print("This should increase the delay.")
time.sleep(2)
scope.write(':MEASU:MEAS1:REFL:METH ABS')
scope.write(':MEASU:CH1:REFL:METH ABS')
scope.write(':MEASU:REFL:TYPE PERSOURCE')
scope.write(':MEASU:CH1:REFL:ABS:TYPE UNIQUE')
scope.write(':MEASU:CH1:REFL:ABS:RISEMID .45')
scope.write(':MEASU:MEAS1:REFL:METH ABS')
scope.write(':MEASU:CH1:REFL:METH ABS')
scope.write(':MEASU:REFL:TYPE PERSOURCE')
scope.write(':MEASU:CH1:REFL:ABS:TYPE UNIQUE')
scope.write(':MEASU:CH1:REFL:ABS:RISEMID 0.45')
print("MEASU:IMM:TYPE? " + scope.query(":MEASU:IMM:TYPE?"))
print("Delay measurement after changing CH1 RefLevel to absolute with mid-voltage on rising edge to 0.45.")
print("Delay between ch1 and ch2: " + scope.query(":MEASU:IMM:VAL?") + "\n")

# Fetach and print CH2 Frequency measurement from the immediate measurement system (no on-scope-screen display)
scope.write(':MEASU:MEAS2:TYP FREQUENCY')
scope.write(':MEASU:IMM:TYP FREQUENCY')
scope.write(':MEASU:IMM:SOURCE CH2')
print("\nMEASU:IMM:TYPE? " + scope.query(":MEASU:IMM:TYPE?"))
print("Ch2 frequency: " + scope.query(":MEASU:IMM:VAL?") + "\n")

# Fetch and print CH2 Period measurement from the measurement badge
scope.write(':MEASU:MEAS3:TYP PERIOD'
scope.write(':MEASU:MEAS3:SOURCE CH2')
print("MEASU:MEAS3:TYPE? " + scope.query(":MEASU:MEAS3:TYPE?"))
print("Ch2 period: " + scope.query(":MEASU:MEAS2:VAL?") + "\n")

# Wait for the user to press enter to continue
input("Press Enter to continue.\n\n")

# Fetch and print CH2 High and low measurements
scope.write(':MEASU:IMM:TYP HIGH')
scope.write(':MEASU:IMM:SOURCE CH2')
print("MEASU:IMM:TYPE? " + scope.query(":MEASU:IMM:TYPE?"))
print("Ch2 High: " + scope.query(":MEASU:IMM:VAL?") + "\n")

scope.write(':MEASU:IMM:TYP LOW')
scope.write(':MEASU:IMM:SOURCE CH2')
print("MEASU:IMM:TYPE? " + scope.query(":MEASU:IMM:TYPE?"))
print("Ch2 Low: " + scope.query(":MEASU:IMM:VAL?") + "\n")

# Fetch and print the record length and sample rate used for these acquisitions
print("Record Length: " + scope.query(":HOR:MODE:RECO?"))
print("Sample Rate: " + scope.query(":HOR:MODE:SAMPLERATE?"))

# Turn the AFG output off
scope.write(':AFG:OUTP:STATE OFF')

# Close the scope connection
scope.close()

