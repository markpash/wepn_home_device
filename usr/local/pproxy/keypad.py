import time
import signal
import os
try:
    from self.configparser import configparser
except ImportError:
    import configparser
import board
import logging
from digitalio import DigitalInOut, Direction, Pull
from PIL import Image, ImageDraw, ImageFont
import sys,tty,termios

BUTTON_PIN = board.D17
JOYDOWN_PIN = board.D27
JOYLEFT_PIN = board.D22
JOYUP_PIN = board.D23
JOYRIGHT_PIN = board.D24
JOYSELECT_PIN = board.D16

from oled import OLED as OLED
from diag import WPDiag
from device import Device

PWD='/usr/local/pproxy/ui/'
CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'
LOG_CONFIG="/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)


class KEYPAD:

    def __init__(self, menu_items=None):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        self.logger = logging.getLogger("keypad")
        self.device = Device(self.logger)
        if (int(self.config.get('hw','button-version'))) == 1:
            # this is an old model, no need for the keypad service
            print("old keypad")
            self.enabled = False
            return
        else:
            print("new keypad")
            self.enabled = True
        self.diag_shown = False
        self.buttons = [BUTTON_PIN, JOYUP_PIN, JOYDOWN_PIN,
                        JOYLEFT_PIN, JOYRIGHT_PIN, JOYSELECT_PIN]
        for i,pin in enumerate(self.buttons):
            self.buttons[i] = DigitalInOut(pin)
            self.buttons[i].direction = Direction.INPUT
            self.buttons[i].pull = Pull.UP
        self.button, self.joyup, self.joydown, self.joyleft, self.joyright, self.joyselect = self.buttons


        self.lcd = OLED()
        self.lcd.set_led_present(self.config.get('hw','led'))
        self.width = 240 
        self.height = 240
        self.menu_row_y_size = 40
        self.menu_items= menu_items

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
        out = out.rotate(270)
        self.lcd.show_image(out)

    def get(self, current):
          if not self.button.value:
            print("Button pressed")
          if not self.joyup.value:
            print("Joystick left")
          if not self.joydown.value:
            print("Joystick right")
          if not self.joyleft.value:
            print("Joystick up")
            if current > 0:
                current -= 1
          if not self.joyright.value:
            print("Joystick down")
            if current < len(self.menu_items)-1:
                current += 1
          if not self.joyselect.value:
            print("Joystick select on" + str(current))
            self.menu_items[current]["action"]()
            if self.diag_shown == True:
                self.diag_shown = False
                self.render(current)

          time.sleep(0.1)
          return current

    def show_claim_info(self):
            current_key = self.status.get('status', 'temporary_key')
            serial_number = self.config.get('django','serial_number')
            display_str = [(1, "Device Key:", 0,"blue"), (2,str(current_key),0,"white"), 
                    (3, "Serial #",0,"blue"), (4, serial_number,0,"white"), ]
            self.lcd.display(display_str, 20)
            time.sleep(15)
            self.render(0)

    def show_claim_info_qrcode(self):
            current_key = self.status.get('status', 'temporary_key')
            serial_number = self.config.get('django','serial_number')
            display_str = [(1, "https://red.we-pn.com/?s="+
                str(serial_number) + "&k="+str(current_key), 2, "white")]
            self.lcd.display(display_str, 20)

    def restart(self):
        self.device.reboot()
        pass

    def power_off(self):
        self.device.turn_off()
        pass

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

def main():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)

    keypad = KEYPAD()
    if keypad.enabled == False:
        return
    items = [{"text":"Restart", "action":keypad.restart},
            {"text":"Power off", "action":keypad.power_off},
                {"text":"Diagnostics", "action":keypad.run_diagnostics},
                {"text":"Exit", "action":keypad.show_claim_info_qrcode}]
    if 0 == int(status.get('status','claimed')):
        items.insert(0,{"text":"Claim Info", "action":keypad.show_claim_info})

    keypad.set_menu(items)
    current = 0
    while True:
        prev_current=current
        current = keypad.get(current)
        if current != prev_current:
            keypad.render(current)

if __name__=='__main__':
    main()
