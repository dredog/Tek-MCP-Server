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
    
    expected_scope = "TCPIP::169.254.10.36::INSTR"

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
print("\nThis program uses the internal AFG to generate a 24 MHz square wave, take 100 measurements, report the statistics and pass fail status.")

scope.write(':FAC')
time.sleep(1)

startTime=time.perf_counter()
scope.write(':HEADER OFF')
scope.write(':SEL:CH2 ON')
scope.write(':SEL:CH1 OFF')

# Setup the function generator
scope.write(':AFG:FUNC SQUare')
scope.write(':AFG:FREQuency 24000000')
scope.write(':AFG:OUTP:LOA:IMPED FIFty')
scope.write(':AFG:AMPLitude 1.0')
scope.write(':AFG:OUTP:MOD CONT')
scope.write(':AFG:OUTP:STATE ON')
scope.query(':*OPC?')

# Setup CH2 scales
scope.write(':CH2:SCA 0.2500000')
scope.write(':CH2:POS 0.000000')
scope.write(':CH2:TERMination 50')
scope.write(':CH2:COUP DC')
scope.write(':CH2:OFFS 0.000000')
scope.query(':*OPC?')

scope.write(':HOR:SCA 20E-9')
scope.write(':HOR:TRIG:POS 10.000000')
scope.write(':TRIG:A:MOD NORM')
scope.write(':TRIG:A:TYP EDGE')
scope.write(':TRIG:A:EDGE:SOU CH2')
scope.write(':TRIG:A:EDGE:SLO RIS')
scope.write(':TRIG:A:LEV .10000')
scope.write(':ACQ:STATE OFF')
scope.write(':ACQ:STOPA RUNSTOP')

#Setup measurement and cursors
scope.write(':MEASU:MEAS1:TYP FREQUENCY')
scope.write(':MEASU:MEAS1:SOURCE1 CH2')
scope.write(':MEASU:MEAS1:POPULATION:LIMIT:STATE ON')
scope.write(':MEASU:MEAS1:POPULATION:LIMIT:VALUE 1000')

# Enable statistics on MEAS1
scope.write(':MEASUrement:MEAS1:DISPlaystat:ENABle ON')

# Turn on pass/fail for MEAS1
scope.write(':MEASUrement:MEAS1:PASSFAILENabled 1')
scope.write(':MEASUrement:MEAS1:PASSFAILWHEN OUTSIDErange')
scope.write(':MEASUrement:MEAS1:PASSFAILLOWlimit 23950000')
scope.write(':MEASUrement:MEAS1:PASSFAILHIGHlimit 24050000')
scope.query(':*OPC?')
scope.write(':ACQ:STATE ON')

# loop until we have reached the specified limit for measurement population
while int(scope.query(':MEASU:MEAS1:POPulation?')) < int(scope.query(':MEASU:MEAS1:POPULATION:LIMIT:VALUE?')):    
    time.sleep(0.05)

# Fetch and display statistics - mean and standard deviation
print("Number of acquisitions: " + scope.query(':MEASU:MEAS1:POPulation?'))
print("Average frequency: " + scope.query(':MEASU:MEAS1:RESults:ALLAcqs:MEAN?'))
print("Standard deviation: " + scope.query(':MEASU:MEAS1:RESults:ALLAcqs:STDDev?'))
print("# of Failures: " + scope.query('MEASUrement:MEAS1:FAILCount?'))
print("Pass/Fail Status: " + scope.query('MEASUrement:MEAS1:STATUS?'))

scope.write(':AFG:OUTP:STATE OFF')


