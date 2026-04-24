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
    
    #expected_scope = "TCPIP0::169.254.48.68::inst0::INSTR"
    #expected_scope = "TCPIP0::169.254.8.46::inst0::INSTR"
    #expected_scope = "TCPIP0::169.254.48.58::INSTR"
    expected_scope = "TCPIP::192.168.1.145::INSTR"
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
#print("\nThis program uses the internal AFG to generate a Gaussian pulse,")
#print("then sets up the scope to measure max, min, and pulse width.\n")
#print("For this to work, you need a BNC cable to the AFG out on the back tlooped around to CH5.")
print("For this, test program, I configured an AWG70000 to output a 10 ns pulse width")
print("1 ns rise and fall times and a swing from 0 to 250 mV into channel 5, repeating every 1 us.")
print("There is commented out code for setting up the internal function generator but some scales may need to change.")

max_FWHM = 99.0
min_FWHM = 0.0
count_FWHM = 0.0
sum_FWHM = 0.0
avg_FWHM = 0.0

scope.write(':FAC')
time.sleep(1)

#Turn the PI Translator On or off
#scope.write(':Compatibility:ENABLE 1')
#scope.write(':Compatibility:ENABLE 0')

startTime=time.perf_counter()
#scope.write(':TURNCHannels ON')
#print("I used the made up command 'TURNCHannels ON' to turn on channels 1, 2, 3, and 4.\n")
#print("After 3 seconds, I turn channels 3 & 4 off with the normal SEL:CH# OFF commands.\n")
#time.sleep(3)
scope.write(':HEADER OFF')
scope.write(':SEL:CH5 ON')
scope.write(':SEL:CH1 OFF')
#scope.write(':callouts:callout1:text " "')
#print("If the PI Translator is off, you would only see channel 1 on now.")
#print("If the PI Translator is on, you should have seen channels 1-4 on for 3 seconds, and now only channels 1 and 2.\n")
#input("Press Enter to continue.\n\n")

scope.write(':AFG:FUNC GAUSSIAN')
scope.write(':AFG:FREQuency 1000000')
scope.write(':AFG:AMPLitude 0.5')
scope.write(':AFG:OUTP:LOA:IMPED FIFty')
scope.write(':AFG:OUTP:MOD CONT')
scope.write(':AFG:OUTP:STATE ON')
print("AFG output has been set to 10 MHz Gaussian with an amplitude of 500 mVp-p\n")
input("Press Enter to continue.\n\n")

scope.write(':CH5:SCA 50e-3')
#scope.write(':CH1:IMP FIFty')
scope.write(':CH5:TERMination 50')
scope.write(':CH5:COUP DC')
scope.write(':CH5:OFFS 0.150000')

scope.write(':HOR:SCA 5E-9')
scope.write(':HOR:POS 30.000000')
scope.write(':TRIG:A:MOD NORM')
scope.write(':TRIG:A:TYP EDGE')
scope.write(':TRIG:A:EDGE:SOU CH5')
scope.write(':TRIG:A:EDGE:COUP DC')
scope.write(':TRIG:A:EDGE:SLO RIS')
scope.write(':TRIG:A:LEV:CH5 .10000')
scope.write(':ACQ:MODE HIR')
scope.write(':ACQ:STOPA SEQ')
scope.write(':ACQ:STATE ON')
print("Verify Settings: 5ns/div, 50 mV/div, single acq mode, trigger on CH5 rising 100 mV.\n")
#input("Press Enter to continue.\n\n")


scope.write(':MEASU:MEAS1:TYP MAXIMUM')
scope.write(':MEASU:MEAS1:STATE ON')
scope.write(':MEASU:MEAS1:SOURCE CH5')
scope.write(':MEASU:MEAS2:TYP MINIMUM')
scope.write(':MEASU:MEAS2:SOURCE CH5')
scope.write(':MEASU:MEAS3:TYP PWIDTH')
scope.write(':MEASU:MEAS3:LABEL "Full Width Half Maximum"')
scope.write(':MEASU:MEAS3:SOURCE CH5')
scope.write(':MEASU:MEAS3:DISPLAYSTAT:ENABLE ON')
scope.write(':MEASU:MEAS3:POPULATION:LIMIT:STATE ON')
scope.write(':MEASU:MEAS3:POPULATION:LIMIT:VALUE 10000000')
scope.write(':MEASU:MEAS3:GLOBALREF 1')
scope.write(':MEASU:REFLEVELS:TYPE GLOBAL')
scope.write(':MEASU:REFLEVELS:BASETop MINMAX')
#input("Are measurements set up correctly. Press Enter to continue.\n\n")

for i in range(100):
    scope.write(':ACQ:STATE ON')
    scope.query('*OPC?')
    #time.sleep(0.1)
    current_FWHM=scope.query(":MEASU:MEAS3:VAL?")
    sum_FWHM = sum_FWHM + float(current_FWHM)
    if float(current_FWHM) < float(max_FWHM):
        max_FWHM = current_FWHM
    if current_FWHM > max_FWHM:
        min_FWHM = current_FWHM
    if count_FWHM == 0:
        print("Printing only the first set of results. All acquisitions will be used for final max/min/mean.")
        print(scope.query(":MEASU:MEAS1:TYPE?") + ": " + scope.query(":MEASU:MEAS1:VAL?"))
        print(scope.query(":MEASU:MEAS2:TYPE?") + ": " + scope.query(":MEASU:MEAS2:VAL?")+"\n")
        print("Half maximum voltage: ")
        print((float(scope.query(":MEASU:MEAS1:VAL?"))+float(scope.query(":MEASU:MEAS2:VAL?")))/2)
        print("Full Width Half Maximum: ")
        print(scope.query(":MEASU:MEAS3:VAL?"))
    count_FWHM = count_FWHM + 1

print("\n")
print("Maximum FWHM: " + str(max_FWHM))
print("Maximum FWHM: " + str(min_FWHM))
avg_FWHM = sum_FWHM/count_FWHM
print("Number of Measurements: " + str(count_FWHM))
print("Average FWHM: " + str(avg_FWHM))

scope.write(':AFG:OUTP:STATE OFF')


