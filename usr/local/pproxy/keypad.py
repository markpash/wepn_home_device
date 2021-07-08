import time
import signal
import os
import math
try:
    from self.configparser import configparser
except ImportError:
    import configparser
import board
import logging
from digitalio import DigitalInOut, Direction, Pull
from PIL import Image, ImageDraw, ImageFont
import sys,tty,termios
import adafruit_aw9523
from adafruit_bus_device import i2c_device
display = True
import RPi.GPIO as GPIO
from adafruit_bus_device import i2c_device

from oled import OLED as OLED
from diag import WPDiag
from device import Device
from heartbeat import HeartBeat

PWD='/usr/local/pproxy/ui/'
CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'
LOG_CONFIG="/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)
INT_EXPANDER = 5
BUTTONS = ["1","2","3","up","down","ok","home"]


class KEYPAD:

    def __init__(self, menu_items=None):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        self.logger = logging.getLogger("keypad")
        self.device = Device(self.logger)
        self.display_active = False
        if (int(self.config.get('hw','button-version'))) == 1:
            # this is an old model, no need for the keypad service
            print("old keypad")
            self.enabled = False
            return
        else:
            print("new keypad")
            self.aw = None
            self.init_i2c()
            self.enabled = True
        self.diag_shown = False
        self.lcd = OLED()
        self.lcd.set_led_present(self.config.get('hw','led'))
        self.lcd.display([(1,"Press all buttons",0, "white"), ], 15)
        self.width = 240 
        self.height = 240
        self.menu_row_y_size = 40
        self.menu_items= menu_items
        self.current = 0


    def init_i2c(self):
        GPIO.setmode(GPIO.BCM)
        i2c = board.I2C()
        # Set this to the GPIO of the interrupt:
        GPIO.setup(INT_EXPANDER, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.aw = adafruit_aw9523.AW9523(i2c)
        new_i2c = i2c_device.I2CDevice(i2c, 0x58)
        time.sleep(1)
        buffer = bytearray(2)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        buffer[0] = 0x06
        buffer[1] = 0x00
        new_i2c.write(buffer)
        #print(buffer)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        GPIO.add_event_detect(INT_EXPANDER, GPIO.FALLING, callback=self.key_press_cb)

    def key_press_cb(self, channel):
        print("CALLBACK is called")
        inputs = self.aw.inputs
        print("Inputs: {:016b}".format(inputs))
        print(inputs)
        inputs = 127 - inputs & 0x7F
        print(inputs)
        if inputs < 1:
            return
        index = (int)(math.log2(inputs))
        print("index is")
        print(index)
        #return
        exit_menu = False
        if inputs>-1:
            button= BUTTONS[index]
            if BUTTONS[index]  == "up":
              print("Key up on " + str(self.current))
              if self.current > 0:
                  self.current -= 1
              self.display_active = True
            if BUTTONS[index]=="down":
              print("Key down on " + str(self.current))
              if self.current < len(self.menu_items)-1:
                  self.current += 1
              self.display_active = True
            if BUTTONS[index]=="ok":
              print("Key select on " + str(self.current))
              if self.display_active:
                  exit_menu = self.menu_items[self.current]["action"]()
                  if self.diag_shown == True:
                    self.diag_shown = False
            if BUTTONS[index]  == "home":
              print("Key home on " + str(self.current))
              exit_menu = True
              self.show_home_screen()
            if exit_menu == False:
                self.render(self.current) 

    def set_menu(self, menu_items):
        self.menu_items= menu_items

    def round_corner(self, radius, fill):
        """Draw a round corner"""
        corner = Image.new('RGB', (radius, radius), (0, 0, 0, 0))
        draw = ImageDraw.Draw(corner)
        draw.pieslice((0, 0, radius * 2, radius * 2),180, 270, fill=fill)
        return corner


    def round_rectangle(self, size, radius, fill):
        """Draw a rounded rectangle"""
        width, height = size
        rectangle = Image.new('RGB', size, fill)
        corner = self.round_corner(radius, fill)
        rectangle.paste(corner, (0, 0))
        rectangle.paste(corner.rotate(90), (0, height - radius))  # Rotate the corner and paste it
        rectangle.paste(corner.rotate(180), (width - radius, height - radius))
        rectangle.paste(corner.rotate(270), (width - radius, 0))
        return rectangle

    def render(self, selected):
        # get a font
        base = Image.new("RGBA",(self.width,self.height), (0,0,0))
        fnt = ImageFont.truetype(PWD+'rubik/Rubik-Light.ttf', 30)
        txt = Image.new("RGBA", base.size, (255,255,255,0))
        d = ImageDraw.Draw(txt)
        overlay= Image.new("RGBA", base.size, (255,255,255,0))
        x=10
        y=0
        i = 0
        corner = None
        for item in self.menu_items:
            y = y + self.menu_row_y_size
            opacity = 128
            if i == selected:
                opacity = 255
                corner = self.round_rectangle((220,40), int(self.menu_row_y_size/2),
                        (255,255,255,128))
                corner.putalpha(128)
                cornery = y - int(self.menu_row_y_size/4) + 5
                overlay.paste(corner, (5,cornery))
            d.text((x,y), "  "+item['text'], font=fnt, fill=(255,255,255, opacity))
            i = i +1
        out = Image.alpha_composite(base, txt)
        out.paste(overlay,(0,0),overlay)
        out = out.rotate(0)
        self.lcd.show_image(out)

    def show_claim_info(self):
            current_key = self.status.get('status', 'temporary_key')
            serial_number = self.config.get('django','serial_number')
            display_str = [(1, "Device Key:", 0,"blue"), (2,str(current_key),0,"white"), 
                    (3, "Serial #",0,"blue"), (4, serial_number,0,"white"), ]
            self.lcd.display(display_str, 20)
            time.sleep(15)
            self.render(0)
            return True # exit the menu

    def show_claim_info_qrcode(self):
            current_key = self.status.get('status', 'temporary_key')
            serial_number = self.config.get('django','serial_number')
            display_str = [(1, "https://red.we-pn.com/?s="+
                str(serial_number) + "&k="+str(current_key), 2, "white")]
            self.lcd.display(display_str, 20)
            return True # exit the menu

    def restart(self):
        self.device.reboot()
        return True # exit the menu

    def power_off(self):
        self.device.turn_off()
        return True # exit the menu

    def run_diagnostics(self):
        diag = WPDiag(self.logger)
        display_str = [(1, "Starting Diagnostics",0,"white"), (2, "please wait ...",0,"green") ]
        self.lcd.display(display_str, 15)
        test_port=int(self.config.get('openvpn','port')) + 1
        diag_code = diag.get_error_code( test_port )
        serial_number = self.config.get('django','serial_number')
        time.sleep(3)
        display_str = [(1, "Status Code",0,"blue"), (2, str(diag_code),0,"white"),
                       (3, "Serial #",0,"blue"), (4, serial_number,0,"white"), 
                       (5, "Local IP",0,"blue"), (6, self.device.get_local_ip(),0,"white"), 
                       (7, "MAC Address",0,"blue"), (8, self.device.get_local_mac(),0,"white"), ]
        self.lcd.display(display_str, 20)
        self.logger.debug(display_str)
        time.sleep(15)
        display_str = [(2, "wepn://diag="+str(diag_code) ,2,"white"), ]
        self.lcd.display(display_str, 19)
        time.sleep(15)
        self.diag_shown = True
        return False # stay in the menu

    def signal_main_wepn(self):
        print("starting")
        with open("/var/run/pproxy.pid", "r") as f:
            wepn_pid = int(f.readline())
            self.logger.debug("Signaling main process at: "+ str(wepn_pid))
            print("Signaling main process at: "+ str(wepn_pid))
            try:
                os.kill(wepn_pid, signal.SIGUSR1)
            except ProcessLookupError as process_error:
                self.logger.error("Could not find the process for main wepn: "+str(wepn_pid)+":" + str(process_error))

    def show_home_screen(self):
        self.current = 0
        self.display_active = False
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        if int(self.status.get("status", "claimed")) == 0:
            self.show_claim_info_qrcode()
        else:
            # show the status info
            hb = HeartBeat(self.logger)
            status = int(self.status.get("status", 'state'))
            display_str = hb.get_display_string_status(self.lcd, status)
            self.lcd.display(display_str, 20)


def main():
    keypad = KEYPAD()
    if keypad.enabled == False:
        return
    items = [{"text":"Restart", "action":keypad.restart},
            {"text":"Power off", "action":keypad.power_off},
                {"text":"Diagnostics", "action":keypad.run_diagnostics},
                {"text":"Exit", "action":keypad.show_home_screen}]
    if 0 == int(keypad.status.get('status', 'claimed')):
        items.insert(0,{"text":"Claim Info", "action":keypad.show_claim_info})

    keypad.set_menu(items)
    keypad.current = 0
    # default scren is QR Code
    keypad.show_home_screen()
    while True:
        time.sleep(100)

if __name__=='__main__':
    main()
