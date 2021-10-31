
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
import device
import logging
import time
#from led_manager import LEDManager
import socket
import os


LM_SOCKET_PATH="/var/local/pproxy/ledmanagersocket.sock"
LOG_CONFIG="/etc/pproxy/logging-debug.ini"

logging.config.fileConfig(LOG_CONFIG,
        disable_existing_loggers=False)

logger = logging.getLogger("led_manager")


#leds = LEDManager()

#leds.set_all((0,0,255))
if os.path.exists(LM_SOCKET_PATH):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    client.connect(LM_SOCKET_PATH)
i = 0
j = 0
while True:
    #leds.progress_wheel_step((0,0,255))
    try:
        if False:
            x =[
                "progress_wheel_step 0 178 16",
                "progress_wheel_step 218 41 28",
                "progress_wheel_step 196 50 39",
                "progress_wheel_step 219 200 182",]
            #x = "set_all 0 178 16"
            client.send(x[j].encode('utf-8'))
            i = (i + 1)
            if i == 24:
                j = (j + 1) % 4
                i = 0
        else: 
            x = "progress_wheel_step 230 81 0"
            x = "set_all 255 145 0"
            client.send(x.encode('utf-8'))

        time.sleep(0.1)
    except KeyboardInterrupt as k:
            print("Shutting down.")
            x = "set_all 255 0 0"
            client.send(x.encode('utf-8'))
            #time.sleep(1)
            x = "blank"
            client.send(x.encode('utf-8'))
            time.sleep(0.1)
            #client.send("DONE".encode('utf-8'))
            client.close()
            break
