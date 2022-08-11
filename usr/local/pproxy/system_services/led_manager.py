
import board
import sys
import neopixel
import time
import os
import socket
import stat
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)

LM_SOCKET_PATH = "/var/local/pproxy/ledmanagersocket.sock"
# The order of the pixel colors - RGB or GRB.
# Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.GRB
CONFIG_FILE = '/etc/pproxy/config.ini'
try:
    from self.configparser import configparser
except ImportError:
    import configparser



class LEDManager:
    def __init__(self):
        self.led_ring_present = True
        self.current_color = None
        self.brightness = 1
        self.current_bright_one = 0
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        if self.config.has_option('hw', 'num_leds'):
            self.num_leds = int(self.config.get('hw', 'num_leds'))
        else:
            # some hw in the wild do not have the config
            self.num_leds = 24
        if self.led_ring_present:
            self.pixels = neopixel.NeoPixel(pin=board.D12,
                                            n=self.num_leds, brightness=1,
                                            bpp=3, auto_write=False,
                                            pixel_order=ORDER)
        pass

    def adjust_brightness(self, color):
        b = self.brightness
        color = (color[0]*b, color[1]*b, color[2]*b)
        return color

    def set_enabled(self, enabled=1):
        if enabled == 0:
            self.blank()
        self.led_ring_present = enabled

    def set_all(self, color):
        if not self.led_ring_present:
            return
        color = self.adjust_brightness(color)
        self.pixels.fill(color)
        self.pixels.show()

    def blank(self):
        if not self.led_ring_present:
            return
        self.set_all((0, 0, 0))

    def fill_upto(self, color, percentage, wait):
        if not self.led_ring_present:
            return
        for i in range(int(self.num_leds * percentage)):
            self.pixels[i] = self.adjust_brightness(color)
            time.sleep(wait/1000)
            self.pixels.show()
        time.sleep(5*wait/1000)

    def fill_downfrom(self, color, percentage, wait):
        if not self.led_ring_present:
            return
        color = self.adjust_brightness(color)
        self.pixels[:int(self.num_leds * percentage)] = [color] * int(self.num_leds * percentage)
        self.pixels.show()
        time.sleep(5*wait/1000)
        for i in range(int(self.num_leds * percentage)-1, -1, -1):
            self.pixels[i] = (0,0,0)
            time.sleep(wait/1000)
            self.pixels.show()

    def progress_wheel_step(self, color):
        if not self.led_ring_present:
            return
        dim_factor = 20
        color = self.adjust_brightness(color)
        self.set_all((color[0] / dim_factor, color[1] / dim_factor,
                      color[2] / dim_factor))
        self.current_bright_one = (self.current_bright_one + 1) % self.num_leds
        before = (self.current_bright_one - 1) % self.num_leds
        if before < 0:
            before = self.num_leds + before
        after = (self.current_bright_one + 1) % self.num_leds

        self.pixels[before] = color
        self.pixels[after] = color
        self.pixels[self.current_bright_one] = color
        self.pixels.show()

    def wheel(self, pos):
        # Input a value 0 to 255 to get a color value.
        # The colours are a transition r - g - b - back to r.
        if pos < 0 or pos > 255:
            r = g = b = 0
        elif pos < 85:
            r = int(pos * 3)
            g = int(255 - pos * 3)
            b = 0
        elif pos < 170:
            pos -= 85
            r = int(255 - pos * 3)
            g = 0
            b = int(pos * 3)
        else:
            pos -= 170
            r = 0
            g = int(pos * 3)
            b = int(255 - pos * 3)
        return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)

    # wait is in milliseconds
    def rainbow(self, rounds=50, wait=1):
        if not self.led_ring_present:
            return
        for _r in range(rounds):
            for j in range(255):
                for i in range(self.num_leds):
                    pixel_index = (i * 256 // self.num_leds) + j
                    self.pixels[i] = self.wheel(pixel_index & 255)*self.brightness
                self.pixels.show()
                time.sleep(wait / 1000)
        self.blank()

    def pulse(self, color, wait, repetitions):
        # wait is in milliseconds
        # repetitions is the number of retepting pluses
        if not self.led_ring_present:
            return
        dim_steps = 20
        color = self.adjust_brightness(color)
        for _r in range(repetitions):
            for i in range(dim_steps):
                m = (i / dim_steps)
                self.pixels.fill((color[0] * m,
                              color[1] * m,
                              color[2] * m))
                self.pixels.show()
                time.sleep(wait / 1000)
            for i in range(dim_steps):
                j = (dim_steps - i) / dim_steps
                self.pixels.fill( (color[0] * j ,
                              color[1] * j ,
                              color[2] * j ))
                self.pixels.show()
                time.sleep(wait / 1000)
        self.blank()

    def blink(self, color, wait, repetitions):
        # wait is in milliseconds
        # repetitions is the number of blinks
        if not self.led_ring_present:
            return
        color = self.adjust_brightness(color)
        for _r in range(repetitions):
            self.pixels.fill( (color[0],
                            color[1],
                            color[2]))
            self.pixels.show()
            time.sleep(wait / 1000)
            self.blank()
            time.sleep(1.5*wait / 1000)

    def spinning_wheel(self, color, wait=100, length=5, repetitions=5):
        if not self.led_ring_present:
            return
        color = self.adjust_brightness(color)
        ring = [(0,0,0)] * self.num_leds
        ring[0:length] = [color] * (length)
        if length > self.num_leds:
            print("invalid light strip length! must be under {}".format(self.num_leds))
            return
        for _r in range(repetitions):
            for i in range(self.num_leds):
                shifted = ring[i:] + ring[:i]
                #for j in self.num_leds
                self.pixels[:] = shifted
                self.pixels.show()
                time.sleep(wait / 1000)
        self.blank()


    def progress_wheel(self, color, percentage):
        # percentage is a float value between 0 and 1
        if not self.led_ring_present:
            return
        color = self.adjust_brightness(color)
        ring = [(0,0,0)] * self.num_leds
        ring[0:int(self.num_leds * percentage)] = [color] * (int(self.num_leds * percentage))
        self.pixels[:] = ring
        self.pixels.show()


# LED system needs to be root, so need to
# create a socket based command system
# TODO: make the socket write permission group based
# this way, apps can be set to be in LED group for permission to control
# the LEDs
if __name__ == '__main__':
    lm = LEDManager()
    if os.path.exists(LM_SOCKET_PATH):
        os.remove(LM_SOCKET_PATH)

    print("LED Manager opening socket...")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(LM_SOCKET_PATH)
    print(hex(stat.S_IRUSR))
    permission = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWUSR
    print(hex(permission))
    os.chmod(LM_SOCKET_PATH,
             permission)

    print("LED Manager Listening...")
    # lm.pulse((255, 0, 0), 50, 5)
    # lm.blink((255, 0, 0), 200, 5)
    # lm.spinning_wheel((255, 255, 255), 100, 10, 6)
    # lm.progress_wheel((255, 255, 255), 10)
    # for i in range(25):
    #     lm.progress_wheel((0, 0, 255), i/22)
    #     time.sleep(0.5)
    #     lm.blank()
    # lm.rainbow(5, 10)
    # lm.fill_upto((255, 0, 255), 1, 25)
    # time.sleep(1)
    # lm.fill_downfrom((255, 0, 255), 1, 25)
    lm.blank()
    while True:
        try:
            datagram = server.recv(1024)
            if not datagram:
                break
            else:
                print("-" * 20)
                incoming_str = datagram.decode('utf-8')
                print(incoming_str)
                incoming = incoming_str.split()
                if len(incoming) == 0 or "DONE" == incoming_str:
                    break
                if incoming[0] == "set_enabled":
                    if len(incoming) == 2:
                        lm.set_enabled(int(incoming[1]))
                # set brightness of LEDs
                if incoming[0] == "set_brightness":
                    if len(incoming) == 2:
                        brightness_value = float(incoming[1])
                        if 0 < brightness_value <= 1:
                            lm.set_brightness(brightness_value)
                if incoming[0] == "set_all":
                    if len(incoming) == 4:
                        lm.set_all((int(incoming[1]),
                                    int(incoming[2]), int(incoming[3])))
                if incoming[0] == "blank":
                    lm.blank()
                if incoming[0] == "rainbow":
                    if len(incoming) == 3:
                        lm.rainbow(int(incoming[1]), float(incoming[2]))
                if incoming[0] == "pulse":
                    # pulse(self, color, wait, repetitions):
                    if len(incoming) == 6:
                        lm.pulse((int(incoming[1]),
                                  int(incoming[2]),
                                  int(incoming[3])),
                                  wait = int(incoming[4]),
                                  repetitions = int(incoming[5]))
                if incoming[0] == "blink":
                    # blink(self, color, wait, repetitions):
                    if len(incoming) == 6:
                        lm.blink((int(incoming[1]),
                                  int(incoming[2]),
                                  int(incoming[3])),
                                  wait = int(incoming[4]),
                                  repetitions = int(incoming[5]))
                if incoming[0] == "progress_wheel_step":
                    if len(incoming) == 4:
                        lm.progress_wheel_step((int(incoming[1]),
                                                int(incoming[2]), int(incoming[3])))
                if incoming[0] == "spinning_wheel":
                    # spinning_wheel(self, color, wait, length, repetitions):
                    if len(incoming) == 7:
                        lm.spinning_wheel((int(incoming[1]),
                                          int(incoming[2]),
                                          int(incoming[3])),
                                          wait = int(incoming[4]),
                                          length = int(incoming[5]),
                                          repetitions = int(incoming[6]))
                if incoming[0] == "progress_wheel":
                    # progress_wheel(self, color, percentage):
                    if len(incoming) == 5:
                        lm.progress_wheel((int(incoming[1]),
                                          int(incoming[2]),
                                          int(incoming[3])),
                                          percentage = float(incoming[4]))
                if incoming[0] == "fill_upto":
                    #fill_upto(self, color, percentage, wait):
                    if len(incoming) == 6:
                        lm.fill_upto((int(incoming[1]),
                                        int(incoming[2]),
                                        int(incoming[3])),
                                        percentage = float(incoming[4]),
                                        wait = int(incoming[5]))
                if incoming[0] == "fill_downfrom":
                    #fill_upto(self, color, percentage, wait):
                    if len(incoming) == 6:
                        lm.fill_downfrom((int(incoming[1]),
                                        int(incoming[2]),
                                        int(incoming[3])),
                                        percentage = float(incoming[4]),
                                        wait = int(incoming[5]))

        except KeyboardInterrupt:
            print('Interrupted')
            server.close()
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
    print("-" * 20)
    print("Shutting down...")
    server.close()
    os.remove(LM_SOCKET_PATH)
    print("Done")
