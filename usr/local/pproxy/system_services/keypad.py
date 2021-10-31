import RPi.GPIO as GPIO
from adafruit_bus_device import i2c_device
import adafruit_aw9523
from PIL import Image, ImageDraw, ImageFont
import logging
import board
import math
import time
import signal
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)
# above line is needed for following classes:
from led_client import LEDClient  # noqa E402 need up_dir first
from heartbeat import HeartBeat  # noqa E402 need up_dir first
from device import Device  # noqa E402 need up_dir first
from diag import WPDiag  # noqa E402 need up_dir first
from lcd import LCD as LCD  # noqa E402 need up_dir first
try:
    from self.configparser import configparser
except ImportError:
    import configparser
display = True


DIR = '/usr/local/pproxy/ui/'
CONFIG_FILE = '/etc/pproxy/config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'
LOG_CONFIG = "/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)
INT_EXPANDER = 5
BUTTONS = ["0", "1", "2", "up", "down", "back", "home"]


class KEYPAD:

    def __init__(self, menu_items=None):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        self.logger = logging.getLogger("keypad")
        self.device = Device(self.logger)
        self.display_active = False
        self.window_stack = []
        self.led_enabled = True
        self.led_client = LEDClient()
        if (int(self.config.get('hw', 'button-version'))) == 1:
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
        self.lcd = LCD()
        self.lcd.set_lcd_present(self.config.get('hw', 'lcd'))
        self.lcd.display([(1, "Press all buttons", 0, "white"), ], 15)
        self.width = 240
        self.height = 240
        self.menu_row_y_size = 37
        self.menu_row_skip = 22
        self.menu = None
        self.menu_index = 0
        self.led_setting_index = 0
        self.current_title = "Main"

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
        # print(buffer)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        GPIO.add_event_detect(INT_EXPANDER, GPIO.FALLING, callback=self.key_press_cb)

    def key_press_cb(self, channel):
        inputs = self.aw.inputs
        # print("Inputs: {:016b}".format(inputs))
        inputs = 127 - inputs & 0x7F
        if inputs < 1:
            return
        index = (int)(math.log2(inputs))
        print("index is" + str(index))
        # return
        exit_menu = False
        menu_base_index = 0
        window_size = len(self.window_stack)
        if inputs > -1:
            if BUTTONS[index] == "up":
                print("Key up on " + str(index))
            if BUTTONS[index] == "down":
                print("Key down on " + str(index))
            if BUTTONS[index] == "back":
                print("Key back on " + str(index))
                if window_size > 0:
                    back = self.window_stack.pop()
                    self.menu_index = back
                    self.render()
                elif window_size == 0:
                    self.set_current_menu(0)
                    exit_menu = True
                    self.show_home_screen()
            if BUTTONS[index] in ["1", "2", "0"]:
                print("Key side =" + BUTTONS[index])
                if window_size == 0 or (self.menu_index != self.window_stack[window_size - 1]):
                    self.window_stack.append(self.menu_index)
                exit_menu = self.menu[self.menu_index][int(
                    BUTTONS[index]) + menu_base_index]["action"]()
                print(self.menu[self.menu_index][int(BUTTONS[index])])
                if self.diag_shown is True:
                    self.diag_shown = False
            if BUTTONS[index] == "home":
                print("Key home on " + str(index))
                exit_menu = True
                self.show_home_screen()
            if exit_menu is False:
                self.render()

    def set_full_menu(self, menu, titles):
        self.menu = menu
        self.titles = titles

    def set_current_menu(self, index):
        self.menu_index = index
        print(self.menu[index])

    def round_corner(self, radius, fill):
        """Draw a round corner"""
        corner = Image.new('RGB', (radius, radius), (0, 0, 0, 0))
        draw = ImageDraw.Draw(corner)
        draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=fill)
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

    def half_round_rectangle(self, size, radius, fill):
        """Draw a rounded rectangle"""
        width, height = size
        rectangle = Image.new('RGB', size, fill)
        corner = self.round_corner(radius, fill)
        # rectangle.paste(corner, (0, 0))
        # rectangle.paste(corner.rotate(90), (0, height - radius))  # Rotate the corner and paste it
        rectangle.paste(corner.rotate(180), (width - radius, height - radius))
        rectangle.paste(corner.rotate(270), (width - radius, 0))
        return rectangle

    def render(self):
        # get a font
        base = Image.new("RGBA", (self.width, self.height), (0, 0, 0))
        fnt = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 30)
        # fnt_title = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 8)
        txt = Image.new("RGBA", base.size, (255, 255, 255, 0))
        d = ImageDraw.Draw(txt)
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        title = self.titles[self.menu_index]
        d.text(((200 - len(title) * 8) / 2, 2), title, font=fnt, fill=(255, 255, 255, 255))
        x = 10
        y = 0
        i = 0
        corner = None
        for item in self.menu[self.menu_index]:
            y = y + int(self.menu_row_y_size / 2) + self.menu_row_skip
            opacity = 128
            if True:
                opacity = 255
                corner = self.half_round_rectangle((200, self.menu_row_y_size), int(self.menu_row_y_size / 2),
                                                   (255, 255, 255, 128))
                corner.putalpha(18)
                cornery = y
                overlay.paste(corner, (x, cornery))
            d.text((x, y), "  " + item['text'], font=fnt, fill=(255, 255, 255, opacity))
            i = i + 1
            y = y + int(self.menu_row_y_size / 2)
        out = Image.alpha_composite(base, txt)
        out.paste(overlay, (0, 0), overlay)
        out = out.rotate(0)
        self.lcd.show_image(out)

    def show_claim_info(self):
        current_key = self.status.get('status', 'temporary_key')
        serial_number = self.config.get('django', 'serial_number')
        display_str = [(1, "Device Key:", 0, "blue"), (2, str(current_key), 0, "white"),
                       (3, "Serial #", 0, "blue"), (4, serial_number, 0, "white"), ]
        self.lcd.display(display_str, 20)
        # self.render()
        return True  # exit the menu

    def show_claim_info_qrcode(self):
        current_key = self.status.get('status', 'temporary_key')
        serial_number = self.config.get('django', 'serial_number')
        display_str = [(1, "https://red.we-pn.com/?pk=NONE&s=" +
                        str(serial_number) + "&k =" + str(current_key), 2, "white")]
        self.lcd.display(display_str, 20)
        return True  # exit the menu

    def restart(self):
        self.lcd.set_logo_text("Restarting ...")
        self.lcd.show_logo()
        self.device.reboot()
        return True  # exit the menu

    def power_off(self):
        self.lcd.set_logo_text("Powering off ...")
        self.lcd.show_logo()
        self.device.turn_off()
        return True  # exit the menu

    def run_diagnostics(self):
        diag = WPDiag(self.logger)
        display_str = [(1, "Starting Diagnostics", 0, "white"), (2, "please wait ...", 0, "green")]
        self.lcd.display(display_str, 15)
        test_port = int(self.config.get('openvpn', 'port')) + 1
        diag_code = diag.get_error_code(test_port)
        serial_number = self.config.get('django', 'serial_number')
        time.sleep(3)
        display_str = [(1, "Status Code", 0, "blue"), (2, str(diag_code), 0, "white"),
                       (3, "Serial #", 0, "blue"), (4, serial_number, 0, "white"),
                       (5, "Local IP", 0, "blue"), (6, self.device.get_local_ip(), 0, "white"),
                       (7, "MAC Address", 0, "blue"), (8, self.device.get_local_mac(), 0, "white"), ]
        self.lcd.display(display_str, 20)
        self.logger.debug(display_str)
        time.sleep(15)
        display_str = [(2, "wepn://diag=" + str(diag_code), 2, "white"), ]
        self.lcd.display(display_str, 19)
        time.sleep(15)
        self.diag_shown = True
        return False  # stay in the menu

    def signal_main_wepn(self):
        print("starting")
        with open("/var/run/pproxy.pid", "r") as f:
            wepn_pid = int(f.readline())
            self.logger.debug("Signaling main process at: " + str(wepn_pid))
            print("Signaling main process at: " + str(wepn_pid))
            try:
                os.kill(wepn_pid, signal.SIGUSR1)
            except ProcessLookupError as process_error:
                self.logger.error("Could not find the process for main wepn: " +
                                  str(wepn_pid) + ":" + str(process_error))

    def show_home_screen(self):
        # self.render()
        # return
        self.display_active = False
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        if int(self.status.get("status", "claimed")) == 0:
            self.show_claim_info_qrcode()
        else:
            # show the status info
            hb = HeartBeat(self.logger)
            status = int(self.status.get("status", 'state'))
            display_str = hb.get_display_string_status(status, self.lcd)
            self.lcd.display(display_str, 20)

    def show_power_menu(self):
        self.display_active = True
        self.current_title = "Power"
        self.set_current_menu(1)
        self.render()

    def show_settings_menu(self):
        self.display_active = True
        self.current_title = "Settings"
        self.set_current_menu(3)
        self.render()

    def show_about_menu(self):
        self.display_active = True
        self.current_title = "About"
        self.set_current_menu(2)
        self.render()

    def toggle_led_setting(self):
        self.display_active = True
        options = ["Yellow", "White", "Red", "Green", "Brown", "Rainbow", "Reset", "Off"]

        new_index = (self.led_setting_index + 1) % len(options)
        if new_index < 5:
            # static on with colors
            self.led_enabled = True
            self.led_client.set_enabled(self.led_enabled)
            if new_index == 0:
                # yellow
                self.led_client.set_all(255, 255, 0)
            elif new_index == 1:
                # white
                self.led_client.set_all(255, 255, 255)
            elif new_index == 2:
                # red
                self.led_client.set_all(255, 0, 0)
            elif new_index == 3:
                # green
                self.led_client.set_all(0, 255, 0)
            elif new_index == 4:
                # brown
                self.led_client.set_all(165, 42, 42)
        elif new_index == 5:
            # rainbow
            self.led_enabled = True
            self.led_client.set_enabled(self.led_enabled)
            self.led_client.rainbow(0)  # 100ms wait
        elif new_index == 6:
            # reset
            self.led_enabled = True
            self.led_client.set_enabled(self.led_enabled)
            self.led_client.blank()
        elif new_index == 7:
            # completely off
            self.led_client.blank()
            self.led_enabled = False
            self.led_client.set_enabled(self.led_enabled)

        # self.led_enabled = not self.led_enabled
        # self.led_client.set_enabled(self.led_enabled)
        # self.led_client.set_all(255,255,0)
        # s = "OFF"
        # if self.led_enabled:
        #    s= "ON"
        self.menu[3][0]["text"] = "Ring: " + options[new_index]
        self.led_setting_index = new_index
        self.render()

    def show_git_version(self):
        self.display_active = True
        self.set_current_menu(4)
        # ONLY FOR UX DEVELOPMENT, show the git hash
        import subprocess  # nosec: dev only, static command = no injection
        label = "production"
        git_cmd = "git log -1 --format=format:\"%H\""
        try:
            label = subprocess.check_output(  # nosec: static command, go.we-pn.com/waiver-1
                git_cmd.split()).strip()
            label = label.decode("utf-8")[1:8]
        except subprocess.CalledProcessError:
            # self.logger.error(e.output)
            label = "no git hash"
        self.menu[4][0]["text"] = label
        self.render()

    def update_software(self):
        self.display_active = True
        self.menu[4][1]["text"] = "checking ..."
        self.render()
        self.device.software_update_from_git()
        self.menu[4][1]["text"] = "Update"
        self.show_git_version()


def main():
    keypad = KEYPAD()
    if keypad.enabled is False:
        return
    s = "OFF"
    if keypad.led_enabled:
        s = "ON"
    items = [
        [{"text": "Settings", "action": keypad.show_settings_menu},
         {"text": "Power", "action": keypad.show_power_menu},
         {"text": "About", "action": keypad.show_about_menu}, ],
        [{"text": "Restart", "action": keypad.restart},
         {"text": "Power off", "action": keypad.power_off}, ],
        [{"text": "Diagnostics", "action": keypad.run_diagnostics},
         {"text": "Git version", "action": keypad.show_git_version}],
        [{"text": "LED ring: " + s, "action": keypad.toggle_led_setting}, ],
        [{"text": "Getting version ...  " + s, "action": keypad.show_git_version},
         {"text": "Update", "action": keypad.update_software}, ],
    ]
    titles = ["Main", "Power", "About", "Settings", "Software"]

    if 0 == int(keypad.status.get('status', 'claimed')):
        items[2].insert(0, {"text": "Claim Info", "action": keypad.show_claim_info})

    keypad.set_full_menu(items, titles)
    keypad.set_current_menu(0)
    # default scren is QR Code
    keypad.show_home_screen()
    while True:
        time.sleep(100)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
