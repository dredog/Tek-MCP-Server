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
    print("Available resources:", res)
    
    #expected_scope = "TCPIP0::169.254.48.68::inst0::INSTR"
    #expected_scope = "TCPIP0::169.254.8.46::inst0::INSTR"
    #expected_scope = "TCPIP0::169.254.48.58::inst0::INSTR"
    expected_scope = "TCPIP::169.254.11.68::INSTR"
    #expected_scope = "TCPIP0::169.254.48.24::inst0::INSTR"
    #expected_scope = "USB::0x0699::0x0527::C034952::INSTR"
    #expected_scope = "GPIB0::4::INSTR"
    #expected_scope = "GPIB0::11::INSTR"
    
    # Check if expected scope is in the list
    if expected_scope not in res:
        print(f"Warning: Expected scope '{expected_scope}' not found in available resources.")
        print("Attempting to connect anyway (resource string might still work)...")
    else:
        print("Expected scope found in list")
    
    try:
        print("Attempting to connect to scope...")
        scope = rm.open_resource(expected_scope)
        print("Connected to " + str(scope))
        scope.timeout = 20000
        scope.write_termination = '\n'
        scope.read_termination = '\n'
        scope.write(":SEL:CH3 ON")
        time.sleep(3)
        scope.write(":SEL:CH3 OFF")
        time.sleep(3)
        scope.write(":SEL:CH4 ON")
        id = str(scope.query("*IDN?"))
        print(f"Scope ID: {id}")
        return scope
    except visa.VisaIOError as e:
        print(f"Error occurred: {e}")
        print("Failed to connect to oscilloscope. Please check:")
        print("1. The IP address is correct")
        print("2. The oscilloscope is powered on and connected to the network")
        print("3. The VISA resource string format is correct")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


scope = initialize_scope()
if scope is None:
    print("Failed to initialize oscilloscope. Exiting.")
    exit(1)

#print("\nThis program uses the internal AFG to generate a Gaussian pulse,")
#print("then sets up the scope to measure max, min, and pulse width.\n")
#print("For this to work, you need a BNC cable to the AFG out on the back tlooped around to CH5.")
print("For this, test program, I configure the SPI bus to work with the SPI bus on MDO demo board 1")
print("Please connect CH3_D4 to SPI_SS, CH3_D5 to SPI_MOSI, and CH3_D6 to SPI_CLK..")

scope.write(':FAC')
time.sleep(1)

startTime=time.perf_counter()
#scope.write(':TURNCHannels ON')
#print("I used the made up command 'TURNCHannels ON' to turn on channels 1, 2, 3, and 4.\n")
#print("After 3 seconds, I turn channels 3 & 4 off with the normal SEL:CH# OFF commands.\n")
#time.sleep(3)
scope.write(':HEADER OFF')
scope.write(':SEL:CH1 OFF')
scope.write(':CH3:STATE ON')
input("Press Enter to continue.\n\n")

scope.write(':HOR:SCA 10E-6')
scope.write(':HOR:POS 70.000000')

scope.write(':BUS:B1:TYPE SPI')
scope.write(':BUS:B1:SPI:NUMber:INPUTS 1')
scope.write(':BUS:B1:SPI:SELect:SOUrce CH3_D4')
scope.write(':BUS:B1:SPI:DATA:SOUrce CH3_D5')
scope.write(':BUS:B1:SPI:CLOCK:SOURCE CH3_D6')
scope.write(':BUS:B1:SPI:CLOCK:THRESHOLD 1.5')
scope.write(':BUS:B1:SPI:DATA:THRESHOLD 1.5')
scope.write(':BUS:B1:SPI:SELect:THRESHOLD 1.5')


scope.write(':TRIG:A:MOD NORM')
scope.write(':TRIG:A:TYP BUS')
scope.write(':TRIG:A:BUS:B1:SPI:CONDITION DATA')
hex_value = input("Enter the hex value of the data you want to trigger on.  ")
decimal_value = int(hex_value, 16)
binary_value = format(decimal_value, '08b')
scope.write(f':TRIG:A:BUS:B1:SPI:DATA:VALUE "{binary_value}"')

time.sleep(0.5)

scope.write(':ACQ:STATE OFF')
scope.write(':ACQ:STOPA SEQ')
scope.write(':ACQ:STATE ON')
#print("Verify Settings: 5ns/div, 50 mV/div, single acq mode, trigger on CH5 rising 100 mV.\n")
input("Press Enter to continue.\n\n")



