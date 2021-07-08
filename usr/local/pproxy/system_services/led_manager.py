
import board
import sys
import neopixel
import time
import os
import socket
import stat
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)

NUM_LED = 24
LM_SOCKET_PATH="/tmp/ledmanagersocket.sock"
class LEDManager:
    def __init__(self):
        self.led_ring_present = True
        self.current_color = None
        self.current_bright_one = 0
        if self.led_ring_present:
            self.pixels = neopixel.NeoPixel(pin=board.D12,
                    n=NUM_LED, brightness=1, bpp=3)
        pass

    def set_all(self, color):
        if not self.led_ring_present:
            return
        self.pixels.fill(color)

    def blank(self):
        if not self.led_ring_present:
            return
        self.set_all((0, 0, 0))

    def set_all_slow(self, color):
        if not self.led_ring_present:
            return
        for i in range(24):
            self.pixels[i] = color
            time.sleep(0.1)

    def progress_wheel_step(self, color):
        if not self.led_ring_present:
            return
        dim_factor = 20
        self.set_all( (color[0]/dim_factor, color[1]/dim_factor, color[2]/dim_factor) )
        self.current_bright_one = (self.current_bright_one + 1) % NUM_LED
        before = (self.current_bright_one - 1) % NUM_LED
        if before < 0:
            before = NUM_LED + before
        after = (self.current_bright_one + 1) % NUM_LED

        self.pixels[before] = color
        self.pixels[after] = color
        self.pixels[self.current_bright_one] = color


# LED system needs to be root, so need to
# create a socket based command system
# TODO: make the socket write permission group based
# this way, apps can be set to be in LED group for permission to control
# the LEDs
if __name__=='__main__':
    lm = LEDManager()
    if os.path.exists(LM_SOCKET_PATH):
        os.remove(LM_SOCKET_PATH)

    print("LED Manager opening socket...")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(LM_SOCKET_PATH)
    os.chmod(LM_SOCKET_PATH,
            stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWOTH | stat.S_IWUSR)

    print("LED Manager Listening...")
    while True:
        datagram = server.recv(1024)
        if not datagram:
            break
        else:
            print("-" * 20)
            incoming_str = datagram.decode('utf-8')
            print(incoming_str)
            incoming = incoming_str.split()
            if len(incoming)==0 or "DONE" == incoming_str:
                break
            if incoming[0] == "progress_wheel_step":
                if len(incoming) == 4:
                    lm.progress_wheel_step((int(incoming[1]),
                        int(incoming[2]), int(incoming[3])))
            if incoming[0] == "set_all":
                if len(incoming) == 4:
                    lm.set_all((int(incoming[1]),
                        int(incoming[2]), int(incoming[3])))
            if incoming[0] == "blank":
                lm.blank()
    print("-" * 20)
    print("Shutting down...")
    server.close()
    os.remove(LM_SOCKET_PATH)
    print("Done") 
