# Title: TekHSI Waveform Receiver
# Author: David Wyban (david.wyban@tektronix.com)
# Company: Tektronix, Inc.
# Created:  2024-11-04
#
# Development Environment:
#    Python 3.12, PyVisa 1.14, NI-VISA 2024 Q1, Windows 10
#
# Compatible Instruments:
#   
#   4 Series B MSO
#   5 Series B MSO
#   6 Series B MSO
#   7 Series A(X) DPO
#   All instruments require firmware version 2.10.5 or later.
#
# Description:
#   This script will connect to the High-speed Interface of the scope at the configured IP address
#   and begin receiving all waveforms from that instrument and writing them to disk as tek .wfm files.
#
#   When using very short record lengths (10-20k and lower) it can be very difficult to keep up with
#   the stream of incomming waveforms.  In order to keep up, this script performs the writes to disk
#   using multiple threads, enabling every waveform to be saved without slowing down the acqusition
#   rate.
# 
#   The number of threads used for writing can be configured in the script user variables.  If the
#   acquisition queue becomes full, increase the number of threads.  Data will not be lost of the
#   queue becomes full.  However, the acqusition rate will be reduced.

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import keyboard
import os
import pyvisa as visa                   # https://pyvisa.readthedocs.io/en/latest/
from queue import Queue
import sys
import tekhsi
import threading
import time
import tm_data_types
from tm_data_types import AnalogWaveform
import typing

# Configure Script Here
#=======================
# Basic
#scope_ipaddr = "169.254.62.37"
#scope_ipaddr = "169.254.6.6"
scope_ipaddr = "169.254.5.238"
#scope_ipaddr = "169.254.74.113"
#scope_ipaddr = "169.254.113.94"
dataOutFolder = ".\\data"

# Advanced
WFM_WRITER_MIN_THREAD_COUNT : int = 2
WFM_WRITER_MAX_THREAD_COUNT : int = 12
ACQ_QUEUE_SIZE : int = 50
#=======================
# End Config

@dataclass
class Acquisition():
    timestamp : datetime = datetime.now()
    waveforms : list[AnalogWaveform] = field(default_factory=list)


# Globals
scope : visa.resources.MessageBasedResource
dataQ : Queue = Queue(ACQ_QUEUE_SIZE)
userAborted : bool = False
receivedAcqCount : int = 0
pauseTimeSec : float = 12.0
pauseAcqs : bool = False
pauseStart : float = time.perf_counter()
displayOn : bool = True

def main():
    global dataQ
    global userAborted
    global receivedAcqCount
    global pauseAcqs
    global scope
    global displayOn

    print ("Starting HSI Receiver")
    print ("=====================")

    # Stops the flashing cursor while printing status to screen
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    # Make sure the folder where data is to be saved exists and make CWD
    outFolder = dataOutFolder.strip('\\')
    isExist = os.path.exists(outFolder)
    if not isExist:
        os.makedirs(outFolder)
    os.chdir(outFolder)

    rm = visa.ResourceManager()
    scope = typing.cast(visa.resources.MessageBasedResource, rm.open_resource(f"TCPIP::{scope_ipaddr}::inst0::INSTR"))
    scope.timeout = 20000
    print(scope.query("*IDN?"))
    displayOn = int(scope.query("DISPLAY:WAVEFORM?")) > 0

    # Connect event handler(s) for key presses
    keyboard.on_press_key('q',on_press_q_key)
    keyboard.on_press_key('p',on_press_p_key)
    keyboard.on_press_key('d',on_press_d_key)
    # Connect to HSI server on scope and begin receiving data
    hsi_url = f"{scope_ipaddr}:5000"
    print(f"Connecting to TekHSI at {hsi_url}")
    with tekhsi.TekHSIConnect(hsi_url, None, callback=cb_tekHSI) as hsiConnection:
        print("Active Symbols: ", end="")
        print(hsiConnection.activesymbols)

        print("Start waveform writer thread(s).")
        writerThreads : list[threading.Thread] = []
        exitEvents : list[threading.Event] = []
        for i in range(0,WFM_WRITER_MIN_THREAD_COUNT):
            exitEvents.append(threading.Event())
            writerThreads.append(threading.Thread(target=waveform_to_disk_writer, args=(exitEvents[len(exitEvents)-1],)))
            writerThreads[i].start()

        print(f"\r\nPress 'q' to quit.  Press 'p' to pause for {pauseTimeSec:0.1f} seconds.  Press 'd' to toggle scope waveform display.\r\n")

        

        cLast = receivedAcqCount
        tLast = time.perf_counter()
        acqRate = 0
        while not userAborted:
            time.sleep(0.1)

            if pauseAcqs:
                if (time.perf_counter() - pauseStart) > pauseTimeSec:
                    pauseAcqs = False
            
            cNow = receivedAcqCount
            tNow = time.perf_counter()
            cDelta = cNow - cLast
            tDelta = tNow - tLast
            # Measure only if enough time has passed and at least 1 acq has been made.
            if tDelta >= 2 and cDelta >= 1:
                acqRate = cDelta / tDelta
                cLast = cNow
                tLast = tNow
            
            queueLen = dataQ.qsize()

            print(f"\rAcq Queue Length: {queueLen}  Thread Count: {len(writerThreads)}  Acq. Count: {receivedAcqCount}  Acq. Rate: {acqRate:.3f} acqs/sec    ", end='\r')

            if queueLen > ACQ_QUEUE_SIZE / 3: # Then add another thread
                if len(writerThreads) < WFM_WRITER_MAX_THREAD_COUNT:
                    exitEvents.append(threading.Event())
                    writerThreads.append(threading.Thread(target=waveform_to_disk_writer, args=(exitEvents[len(exitEvents)-1],)))
                    writerThreads[len(writerThreads)-1].start()
            
            # Reduce writer thread count if a lot of threadqs are sitting around doing nothing
            elif queueLen == 0 and len(writerThreads) > WFM_WRITER_MIN_THREAD_COUNT:
                exitEvent = exitEvents.pop()
                writerThread = writerThreads.pop()
                exitEvent.set()
                writerThread.join()

        # End while
    # End with TekHSIConnect

    scope.write("DISPLAY:WAVEFORM ON")
    scope.close()
    rm.close()

    sys.stdout.write("\033[?25h")
    sys.stdout.flush()
    keyboard.unhook_all()

    print("\r\n")
    return

        
            
def on_press_q_key(args : keyboard.KeyboardEvent):
    global userAborted
    userAborted = True
    return

def on_press_p_key(args : keyboard.KeyboardEvent):
    global pauseAcqs
    global pauseStart
    pauseStart = time.perf_counter()
    pauseAcqs = True

def on_press_d_key(args : keyboard.KeyboardEvent):
    global displayOn
    if displayOn:
        scope.write("DISPLAY:WAVEFORM OFF")
    else:
        scope.write("DISPLAY:WAVEFORM ON")
    displayOn = not displayOn
    return


def cb_tekHSI(waveforms) -> None:
    global receivedAcqCount

    tStamp = datetime.now()
    receivedAcqCount += 1
    acq = Acquisition(tStamp, waveforms)
        
    if dataQ.full():
        print("\r\nCallback found Q is full. Sleeping until room available.")
        while dataQ.full() and not userAborted:
            time.sleep(0.0001)
        if userAborted: # Then just quit
            return

    dataQ.put(acq) # push the received data into the queue

    if pauseAcqs:
        print(f"\r\nUser paused acquisitions for {pauseTimeSec:.2f} seconds.")
        while time.perf_counter() - pauseStart > pauseTimeSec:
            time.sleep(0.05)
            if userAborted:
                break
    return


def waveform_to_disk_writer(ExitEvent : threading.Event):
 
    # Keep processing as long as the user hasn't aborted or there are acqs still in the queue.
    # Quit only if the user chose to quit and there are no acqs left in the queue.
    while not userAborted or not dataQ.empty():
        
        # Checking the empty stats of the Queue blocks the HSI callback from adding to the queue so
        # put some time in between checks to minimize blocking.
        time.sleep(0.005)
        
        if not dataQ.empty(): # Then process data from the queue
            acq : Acquisition = dataQ.get()          
            tStamp : datetime = acq.timestamp

            for waveform in acq.waveforms:
                awfm : AnalogWaveform = waveform
                timePortion = tStamp.strftime("%Y-%m-%d_%H%M%S_%f")
                filename = f"{timePortion}_{awfm.source_name}.wfm"

                tm_data_types.write_file(filename, awfm)
        
        if ExitEvent.is_set():
            break
    # End while
    return

if __name__ == '__main__':
	main()
