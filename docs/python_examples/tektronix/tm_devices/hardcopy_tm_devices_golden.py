from tm_devices.drivers import MSO5
from tm_devices import DeviceManager
from pathlib import Path
from datetime import datetime



# Modify the following lines
# == 
# Scope Address
address = "169.254.8.157"
scope_save_location = Path("c:/")
local_save_location = Path("c:/Users/amccann/Pictures/")
# ==


with DeviceManager() as dm:
    scope_handle: MSO5 = dm.add_scope(address)
    # Alias out the commands to make it faster to type
    mso5 = scope_handle.commands
    mso5.idn.query()

    # Set up the 
    dt = datetime.now()
    # .bmp, .png, .jpg are supported
    filename = dt.strftime("%Y%m%d_%H%M%S.png")
    
    mso5.save.image.composition.write("NORMAL") # or INVERTED
    mso5.save.image.write((scope_save_location / filename).as_posix())
    if int(mso5.opc.query()) == 1: 
        mso5.filesystem.readfile.write((scope_save_location / filename).as_posix())
        
        # Have to directly access the visa resource to read the buffer
        data = scope_handle.read_raw()
        image_path = Path(local_save_location) / filename
        local_file = open(image_path, 'wb')
        local_file.write(data)
        local_file.close()

    else:
        print('failed')


    




