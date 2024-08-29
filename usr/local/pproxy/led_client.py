import logging
import logging.config
import os
import socket
import time

import device

from constants import LOG_CONFIG

LM_SOCKET_PATH = "/var/local/pproxy/ledmanagersocket.sock"
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)

logger = logging.getLogger("led_client")


class LEDClient:
    ''' The nethods of this class send commands to the LED manager,
    which runs with root previlages due to hardware DMA security constraints.
    The commands are sent through a socket connection to the LED manager.

    The LED manager is a Python script that runs as a daemon. The LED manager
    is a daemon because it uses DMA to control the LEDs. This is a hardware security constraint.

    The LED client is a Python script that runs as a non-root user. The LED client function
    is to serialize LED commands and send them to the LED manager in a secure manner.
    '''

    def __init__(self):
        self.client = None
        if os.path.exists(LM_SOCKET_PATH):
            self.client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            try:
                self.client.connect(LM_SOCKET_PATH)
            except PermissionError:
                self.device = device.Device(logger)
                self.device.execute_setuid("1 14")
                self.client.connect(LM_SOCKET_PATH)
            except Exception:
                self.client = None
                logger.exception("LED Client failed to connect")
                pass

    def __del__(self):
        if self.client is not None:
            self.client.close()

    def set_enabled(self, enabled=True):
        if self.client is None:
            return
        self.send("set_enabled " + str(int(enabled)))

    def set_brightness(self, brightness=0.5):
        '''
        sets led brightness
        '''
        if self.client is None:
            return
        if brightness < 0 or brightness > 1:
            print("brightness must be between 0 and 1")
            return
        self.send("set_brightness " +
                  str(brightness))

    def send(self, cmd):
        self.client.send(cmd.encode('utf-8'))

    def set_all(self, color=(255, 255, 255)):
        '''
        sets all LEDs to the specified color
        '''
        if self.client is None:
            return
        (r, g, b) = color
        self.send("set_all " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b))

    def blank(self):
        if self.client is None:
            return
        self.send("blank")

    def rainbow(self, rounds, wait):
        '''
        glows the LEDs in a rainbow pattern
        percentage: is a float between 0 and 1
        wait: is in milliseconds
        '''
        if self.client is None:
            return
        self.send("rainbow " +
                  str(rounds) + " " +
                  str(wait))

    def progress_wheel_step(self, color=(255, 255, 255)):
        '''
        increments the position of bright strip by one step.
        '''
        if self.client is None:
            return
        (r, g, b) = color
        self.send("progress_wheel_step " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b))

    def pulse(self, color=(255, 255, 255),
              wait=100,
              repetitions=5):
        if self.client is None:
            return
        (r, g, b) = color
        self.send("pulse " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(wait) + " " +
                  str(repetitions))

    def blink(self, color=(255, 255, 255),
              wait=100,
              repetitions=5):
        if self.client is None:
            return
        (r, g, b) = color
        self.send("blink " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(wait) + " " +
                  str(repetitions))

    def spinning_wheel(self,
                       color=(255, 255, 255),
                       wait=100,
                       length=5,
                       repetitions=5):
        if self.client is None:
            return
        (r, g, b) = color
        self.send("spinning_wheel " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(wait) + " " +
                  str(length) + " " +
                  str(repetitions))

    def progress_wheel(self,
                       color=(255, 255, 255),
                       percentage=0.5):
        if self.client is None:
            return
        (r, g, b) = color
        self.send("progress_wheel " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(percentage))

    def fill_upto(self,
                  color=(255, 255, 255),
                  percentage=0.5,
                  wait=100):
        if self.client is None:
            return
        (r, g, b) = color
        self.send("fill_upto " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(percentage) + " " +
                  str(wait))

    def fill_downfrom(self,
                      color=(255, 255, 255),
                      percentage=0.5,
                      wait=100):
        if self.client is None:
            return
        (r, g, b) = color
        self.send("fill_downfrom " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(percentage) + " " +
                  str(wait))


if __name__ == '__main__':
    # add test cased for (1) enable and disable (2) set brightness
    lc = LEDClient()
    lc.set_enabled(True)
    lc.set_all((255, 255, 255))
    time.sleep(1)
    print("white ring must glow for 1 second")
    lc.set_enabled(False)
    lc.set_all((255, 0, 0))
    print("red ring must NOT glow for 1 second")
    time.sleep(1)
    lc.set_enabled(True)
    lc.blank()
    # fill_upto
    lc.fill_upto((0, 0, 255), 1, 20)
    time.sleep(1)
    # fill_downfrom
    lc.fill_downfrom((0, 0, 255), 1, 20)
    time.sleep(1)
    # magenta
    lc.set_all((255, 0, 255))
    time.sleep(1)
    # yellow
    lc.set_all((255, 255, 0))
    time.sleep(1)
    # cyan
    lc.set_all((0, 255, 255))
    time.sleep(1)
    # white
    lc.set_all((255, 255, 255))
    time.sleep(1)
    # red
    lc.set_all((255, 0, 0))
    time.sleep(1)
    # green
    lc.set_all((0, 255, 0))
    time.sleep(1)
    # blue
    lc.set_all((0, 0, 255))
    time.sleep(1)
    # turn off all
    lc.blank()
    # activate rainbow
    lc.rainbow(10, 5)
    time.sleep(1)
    for i in range(0, 11, 1):
        lc.set_brightness(i / 10)
        time.sleep(0.2)
    # show progress wheel step
    for i in range(15):
        lc.progress_wheel_step((0, 255, 0))
        time.sleep(0.1)
    # pulse
    lc.pulse((255, 0, 255), 50, 5)
    time.sleep(2)
    # blink
    lc.blink((255, 0, 0), 200, 5)
    time.sleep(1)
    # spinning wheel
    lc.spinning_wheel((255, 255, 255), 20, 10, 3)
    time.sleep(2)
    lc.blank()
    # set progress wheel to 60%
    for i in range(25):
        lc.progress_wheel((0, 0, 255), i / 25)
        time.sleep(0.1)
    lc.blank()
    time.sleep(1)
    lc.rainbow(3, 5)
    time.sleep(2)
    lc.blank()
