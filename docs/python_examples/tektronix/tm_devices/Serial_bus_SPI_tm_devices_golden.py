from tm_devices import DeviceManager
from tm_devices.drivers import MSO6B
from tm_devices.helpers import PYVISA_PY_BACKEND

import time

with DeviceManager(verbose=False) as device_manager:
    # Enable resetting the devices when connecting and closing
    device_manager.setup_cleanup_enabled = True
    device_manager.teardown_cleanup_enabled = True

    # Use the PyVISA-py backend
    device_manager.visa_library = PYVISA_PY_BACKEND

    # Creating Scope driver object by providing ip address.
    scope: MSO6B = device_manager.add_scope("169.254.113.94")
    scope.query("*IDN?")
    
    # Send some commands
    scope.turn_channel_on("CH3")  # turn on channel 3
    scope.write("display:waveview1:ch3_D0:state off")
    scope.write("display:waveview1:ch3_D1:state off")
    scope.write("display:waveview1:ch3_D2:state off")
    scope.write("display:waveview1:ch3_D3:state off")
    scope.write("display:waveview1:ch3_D7:state off")
    print("This test program sets up a SPI bus decode using a TLP058 connected to ch 3.")
    print("From MDO demo board 1, connect:\n  CH3_D4 to SPI_SS, \n  CH3_D5 to MOSI, \n  CH3_D6 to SPI_CLK.")
    print("The bit rate for this SPI bus is 200 kHz.")
    bit_rate = 200000
    #bit_rate = input("What is the bit rate of your SPI bus? ")

    Hscale = 2/int(bit_rate)
    scope.commands.horizontal.scale.write(Hscale)
    time.sleep(0.3)

    # Adding measurements
    scope.commands.measurement.addmeas.write("AMPLitude")
    scope.commands.measurement.addmeas.write("FREQUENCY")
    scope.commands.measurement.meas[1].source.write("CH1")
    scope.commands.measurement.meas[2].source.write("CH3_D6")
    input("Pausing to check scales and measurements. Press Enter to continue.")

    # Adding SPI Bus decode
    scope.commands.bus.addnew.write("B1")
    scope.commands.bus.b[1].type.write("SPI")
    scope.commands.bus.b[1].spi.number.inputs.write("ONE")
    scope.commands.bus.b[1].spi.select.source.write("CH3_D4")
    scope.commands.bus.b[1].spi.data.source.write("CH3_D5")
    scope.commands.bus.b[1].spi.clock.source.write("CH3_D6")

    # Setup the trigger
    scope.commands.horizontal.position.write(25)  # adjust horizontal scale
    scope.commands.trigger.a.type.write("EDGE")
    scope.commands.trigger.a.edge.source.write("CH3_D6")
    scope.commands.trigger.a.edge.slope.write("RIS")
    
    trig_options = "0"
    while(trig_options != "x"):
        trig_options = input("\n1 to trigger on SPI SS active\n2 to trigger on specific data\nx to exit this loop\nanything else to retrigger with the current settings" )
        if(trig_options == "1"):
            scope.commands.horizontal.position.write(25)  # adjust horizontal scale
            scope.commands.trigger.a.type.write("EDGE")
            scope.commands.trigger.a.edge.source.write("CH3_D4")
            scope.commands.trigger.a.edge.slope.write("FALL")
        if(trig_options ==  "2"):
            bin_data = input("What data do you want to trigger on (in 8 bit binary form)?")
            scope.commands.horizontal.position.write(75)  # adjust horizontal scale
            scope.commands.trigger.a.type.write("BUS")
            scope.commands.trigger.a.bus.b[1].spi.condition.write("DATA")
            scope.commands.trigger.a.bus.b[1].spi.data.value.write(bin_data)
        time.sleep(0.5)
        scope.commands.acquire.stopafter.write("SEQ")
        scope.commands.acquire.state.write("ON")

    input("Press Enter to exit (this will reset the scope).")


    # save the session as example.tss
    #scope.commands.save.session.write("spi_bus_CH3_withTLP058.tss")
    # save the waveform on CH1 as example.wfm
    #scope.commands.save.waveform.write('CH2,"example_SPI_waveform.wfm"')

    #scope.reset()  # reset the scope

    #scope.recall_session("example.tss")  # recall the saved session example.tss
    #scope.recall_reference("example.wfm", 1)  # recall example.wfm as REF1
