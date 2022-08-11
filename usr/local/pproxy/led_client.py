import os
import logging
import logging.config
import socket

LM_SOCKET_PATH = "/var/local/pproxy/ledmanagersocket.sock"
LOG_CONFIG = "/etc/pproxy/logging-debug.ini"
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
            self.client.connect(LM_SOCKET_PATH)

    def __del__(self):
        if self.client is not None:
            self.client.close()

    def set_enabled(self, enabled=True):
        if self.client is None:
            return
        self.send("set_enabled " + str(int(enabled)))

    def send(self, cmd):
        self.client.send(cmd.encode('utf-8'))

    def set_all(self, color = (255,255,255)):
        '''
        sets all LEDs to the specified color
        '''
        if self.client is None:
            return
        (r,g,b) = color
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

    def progress_wheel_step(self, color = (255,255,255)):
        '''
        increments the position of bright strip by one step.
        '''
        if self.client is None:
            return
        (r,g,b) = color
        self.send("progress_wheel_step " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b))
    def pulse(self, color = (255,255,255),
                    wait = 100,
                    repetitions = 5):
        if self.client is None:
            return
        (r,g,b) = color
        self.send("pulse " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(wait) + " " +
                  str(repetitions))

    def blink(self, color = (255,255,255),
                    wait = 100,
                    repetitions = 5):
        if self.client is None:
            return
        (r,g,b) = color
        self.send("blink " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(wait) + " " +
                  str(repetitions))

    def spinning_wheel(self,
                        color = (255,255,255),
                        wait = 100,
                        length = 5,
                        repetitions = 5):
        if self.client is None:
            return
        (r,g,b) = color
        self.send("spinning_wheel " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(wait) + " " +
                  str(length) + " " +
                  str(repetitions))

    def progress_wheel(self,
                        color = (255,255,255),
                        percentage = 0.5):
        if self.client is None:
            return
        (r,g,b) = color
        self.send("progress_wheel " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(percentage))

    def fill_upto(self,
                        color = (255,255,255),
                        percentage = 0.5,
                        wait = 100):
        if self.client is None:
            return
        (r,g,b) = color
        self.send("fill_upto " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(percentage) + " " +
                  str(wait))

    def fill_downfrom(self,
                        color = (255,255,255),
                        percentage = 0.5,
                        wait = 100):
        if self.client is None:
            return
        (r,g,b) = color
        self.send("fill_downfrom " +
                  str(r) + " " +
                  str(g) + " " +
                  str(b) + " " +
                  str(percentage) + " " +
                  str(wait))


if __name__ == '__main__':
    lc = LEDClient()
    lc.set_enabled(True)
    time.sleep(1)
    lc.blank()
    #fill_upto
    lc.fill_upto((0,0,255), 1, 15)
    time.sleep(2)
    #fill_downfrom
    lc.fill_downfrom((0,0,255), 1, 15)
    time.sleep(5)
    #magenta
    lc.set_all((255, 0, 255))
    time.sleep(2)
    #yellow
    lc.set_all((255, 255, 0))
    time.sleep(2)
    #cyan
    lc.set_all((0, 255, 255))
    time.sleep(2)
    #white
    lc.set_all((255, 255, 255))
    time.sleep(2)
    #red
    lc.set_all((255, 0, 0))
    time.sleep(2)
    #green
    lc.set_all((0, 255, 0))
    time.sleep(2)
    #blue
    lc.set_all((0, 0, 255))
    time.sleep(2)
    # #turn off all
    lc.blank()
    # activate rainbow
    lc.rainbow(3, 5)
    time.sleep(5)
    # show progress wheel step
    for i in range(10):
        lc.progress_wheel_step((0, 255, 0))
        time.sleep(0.5)
    # pulse
    lc.pulse((255, 0, 255), 50, 5)
    time.sleep(5)
    # blink
    lc.blink((255, 0, 0), 200, 5)
    time.sleep(1)
    # spinning wheel
    lc.spinning_wheel((255, 255, 255), 20, 10, 3)
    time.sleep(10)
    lc.blank()
    #set progress wheel to 60%
    for i in range(25):
        lc.progress_wheel((0, 0, 255), i/25)
        time.sleep(0.5)
    lc.blank()
