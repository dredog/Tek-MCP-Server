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
    expected_scope = "TCPIP::192.168.0.14::INSTR"
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
        scope.timeout = 10000
        scope.write_termination = '\n'
        scope.read_termination = '\n'
#        id = str(scope.query("*IDN?"))
#        print(id)

        
        return scope
    except visa.VisaIOError as e:
    
        print("Error occurred.. ", e)
        scope.close()
        return initialize_scope()


scope = initialize_scope()
print("\nThis program uses the internal AFG to generate a 24 kHz sine wave,")
print("then sets up the scope to measure freq on channel 1 with gating from 80-120ms\n")


#scope.write(':FAC')
time.sleep(1)

startTime=time.perf_counter()
scope.write(':HEADER OFF')
scope.write(':SEL:CH1 ON')
#scope.write(':callouts:callout1:text " "')
#print("If the PI Translator is off, you would only see channel 1 on now.")
#print("If the PI Translator is on, you should have seen channels 1-4 on for 3 seconds, and now only channels 1 and 2.\n")
#input("Press Enter to continue.\n\n")

scope.write(':AFG:FUNC SQUare')
scope.write(':AFG:FREQuency 24000')
scope.write(':AFG:AMPLitude 1.0')
scope.write(':AFG:OUTP:LOA:IMPED FIFty')
scope.write(':AFG:OUTP:MOD CONT')
scope.write(':AFG:OUTP:STATE ON')
print("AFG output has been set to 24 kHz square wave 500 mVp-p\n")
input("Press Enter to continue.\n\n")

scope.write(':CH1:SCA 0.1300000')
scope.write(':CH1:POS 0.000000')
#scope.write(':CH1:IMP FIFty')
scope.write(':CH1:TERMination 50')
scope.write(':CH1:COUP DC')
scope.write(':CH1:OFFS 0.000000')
#input("Press Enter to continue.\n\n")

scope.write(':HOR:MAI:SCA 20E-3')
scope.write(':HOR:TRIG:POS 10.000000')
scope.write(':TRIG:MAI:MOD NORM')
scope.write(':TRIG:MAI:TYP EDGE')
scope.write(':TRIG:MAI:EDGE:SOU CH1')
scope.write(':TRIG:MAI:EDGE:SLO RIS')
scope.write(':TRIG:MAI:LEV .050000')
# Single acquisition
scope.write(':ACQ:STOPA SEQ')
scope.write(':ACQ:STATE ON')

scope.write(':ACQ:MODE HIR')
#scope.write(':MEASU:MEAS1:TYP DEL')

#Setup measurement and cursors
scope.write(':MEASU:MEAS1:TYP FREQUENCY')
scope.write(':MEASU:MEAS1:STATE ON')
scope.write(':MEASU:MEAS1:SOURCE1 CH1')
scope.write(':MEASU:GATING CURSor')
scope.write(':DISplay:WAVEView1:CURSOR:CURSOR1:FUNCTION VBArs')
scope.write(':DISplay:WAVEView1:CURSOR:CURSOR2:FUNCTION VBArs')
scope.write(':DISplay:WAVEView1:CURSOR:CURSOR1:SCREEN:AXPOS 80e-3')
scope.write(':DISplay:WAVEView1:CURSOR:CURSOR2:SCREEN:AXPOS 120e-3')
scope.write(':HOR:POS 10.000000')

# loop 960 times to get the frequency measurements
while i < 10:
    scope.write(':ACQ:STATE ON')
    time.sleep(0.05)
    result = result + scope.query('MEASU:MEAS1:val?')
    i = i + 1

print("Number of acquisitions: " + str(i))
print("Average frequency: " + str(result/i))
    
scope.write(':AFG:OUTP:STATE OFF')


