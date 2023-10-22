try:
    import RPi.GPIO as GPIO
    from adafruit_bus_device import i2c_device
    import adafruit_aw9523
except:
    print("RPi import failed")
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
import constants as consts  # noqa E402 need up_dir first
from constants import LOG_CONFIG # noqa E402 need up_dir first
from constants import FORCE_SCREEN_ON # noqa E402 need up_dir first

try:
    from self.configparser import configparser
except ImportError:
    import configparser
display = True


DIR = '/usr/local/pproxy/ui/'
CONFIG_FILE = '/etc/pproxy/config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)
INT_EXPANDER = 5
BUTTONS = ["0", "1", "2", "up", "down", "back", "home"]

# Unit of time: how often it wakes from sleep
# in seconds
UNIT_TIMEOUT = 30
# Multiply by unit above for all below timeouts
NRML_SCREEN_TIMEOUT = 40
# if an error is detected, keep screen
# on longer
ERR_SCREEN_TIMEOUT = 100
MENU_TIMEOUT = 10


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
        self.titles = []
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
        self.lcd.display([(1, "WEPN loading ... ", 0, "white"), ], 15)
        self.chin = {"text": "", "color": (0, 0, 0), "opacity": 100, "errs": [False] * 7}
        self.width = 240
        self.height = 240
        self.menu_row_y_size = 37
        self.menu_row_skip = 22
        self.menu = None
        self.menu_index = 0
        self.led_setting_index = 0
        self.current_title = "Main"
        self.menu_active_countdown = MENU_TIMEOUT
        self.countdown_to_turn_off_screen = NRML_SCREEN_TIMEOUT
        self.screen_timed_out = False
        self.leds_turned_for_error = False
        self.diag_code = 0
        self.prev_diag_code = 0
        self.err_pending_ack = False
        self.dev_remaining = 7
        self.channel = "prod"

    def init_i2c(self):
        if (int(self.config.get('hw', 'buttons'))) == 0:
            return
        GPIO.setmode(GPIO.BCM)
        i2c = board.I2C()
        # Set this to the GPIO of the interrupt:
        GPIO.setup(INT_EXPANDER, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        try:
            self.aw = adafruit_aw9523.AW9523(i2c, 0x58)
            new_i2c = i2c_device.I2CDevice(i2c, 0x58)
        except:
            try:
                self.aw = adafruit_aw9523.AW9523(i2c, 0x5b)
                new_i2c = i2c_device.I2CDevice(i2c, 0x5b)
            except:
                self.aw = adafruit_aw9523.AW9523(i2c, 0x5a)
                new_i2c = i2c_device.I2CDevice(i2c, 0x5a)
        self.aw.reset()
        # print("Inputs: {:016b}".format(self.aw.inputs))
        self.aw.directions = 0xff00
        # self.aw.outputs = 0x0000
        time.sleep(1)
        # first write to both registers to reset the interrupt flag
        buffer = bytearray(2)
        buffer[0] = 0x00
        buffer[1] = 0x00
        new_i2c.write(buffer)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        time.sleep(0.1)
        buffer[0] = 0x01
        buffer[1] = 0x00
        new_i2c.write(buffer)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        # disable interrupt for higher bits
        buffer[0] = 0x06
        buffer[1] = 0x00
        new_i2c.write(buffer)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        buffer[0] = 0x07
        buffer[1] = 0xff
        new_i2c.write(buffer)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        # read registers again to reset interrupt
        buffer[0] = 0x00
        buffer[1] = 0x00
        new_i2c.write(buffer)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        time.sleep(0.1)
        buffer[0] = 0x01
        buffer[1] = 0x00
        new_i2c.write(buffer)
        new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
        time.sleep(0.1)
        # _inputs = self.aw.inputs
        # for i in range(1):
        #    print("Inputs: {:016b}".format(self.aw.inputs))
        #    time.sleep(0.5)
        time.sleep(0.5)
        GPIO.add_event_detect(INT_EXPANDER, GPIO.FALLING, callback=self.key_press_cb)

    def key_press_cb(self, channel):
        inputs = self.aw.inputs
        # print("Inputs: {:016b}".format(inputs))
        inputs = 127 - inputs & 0x7F
        if inputs < 1:
            return
        index = (int)(math.log2(inputs))
        exit_menu = False
        menu_base_index = 0
        window_size = len(self.window_stack)
        self.err_pending_ack = False
        if inputs > -1:
            # first set countdown for menu being active to 10
            # this ensures while menu is actively used
            # it is not overwritten
            self.menu_active_countdown = MENU_TIMEOUT
            # This below countdown will turn off screen if not used
            # every time keys are touched, the countdown will be reset
            self.countdown_to_turn_off_screen = NRML_SCREEN_TIMEOUT
            # if screen has timed out, first button press should ONLY
            # render the screen and nothing else
            if self.screen_timed_out is True:
                self.screen_timed_out = False
                # just show whatever the last menu was on screen
                self.render()
                return

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
                if window_size == 0 or (self.menu_index != self.window_stack[window_size - 1]):
                    self.window_stack.append(self.menu_index)
                exit_menu = self.menu[self.menu_index][int(
                    BUTTONS[index]) + menu_base_index]["action"]()
                if self.diag_shown is True:
                    self.diag_shown = False
            if BUTTONS[index] == "home":
                print("Key home on " + str(index))
                self.window_stack.clear()
                exit_menu = True
                self.show_home_screen()
            if exit_menu is False:
                self.render()

    def clear_screen(self):
        self.lcd.clear()
        self.lcd.set_backlight(turn_on=False)

    def set_full_menu(self, menu, titles):
        self.menu = menu
        self.titles = titles

    def set_current_menu(self, index):
        self.menu_index = index

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

    def render(self, title=None):
        # get a font
        base = Image.new("RGBA", (self.width, self.height), (0, 0, 0))
        fnt = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 30)
        # fnt_title = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 8)
        txt = Image.new("RGBA", base.size, (255, 255, 255, 0))
        d = ImageDraw.Draw(txt)
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        if (title is None):
            title = self.titles[self.menu_index]["text"]
        if "color" in self.titles[self.menu_index]:
            color = self.titles[self.menu_index]["color"]
        else:
            color = (255, 255, 255)
        d.text(((200 - len(title) * 8) / 2, 2), title, font=fnt,
               fill=(color[0], color[1], color[2], 255))
        x = 10
        y = 0
        i = 0
        corner = None
        for item in self.menu[self.menu_index]:
            if "display" in item and item["display"] is False:
                skip = True
            else:
                skip = False

            if "color" in item:
                color = item["color"]
            else:
                color = (255, 255, 255)

            y = y + int(self.menu_row_y_size / 2) + self.menu_row_skip
            opacity = 128
            if not skip:
                opacity = 255
                corner = self.half_round_rectangle((200, self.menu_row_y_size), int(self.menu_row_y_size / 2),
                                                   (255, 255, 255, 128))
                corner.putalpha(18)
                cornery = y
                overlay.paste(corner, (x, cornery))
            if not skip:
                d.text((x, y), "  " + item['text'], font=fnt,
                       fill=(color[0], color[1], color[2], opacity))
            i = i + 1
            y = y + int(self.menu_row_y_size / 2)
        if self.menu_index == 5:
            # show a chin line for Home
            font_icon = ImageFont.truetype('/usr/local/pproxy/ui/heydings_icons.ttf', 25)
            y = y + int(self.menu_row_y_size / 2) + 6
            x = 20
            i = 0
            for c in self.chin['text']:
                if self.chin['errs'][i]:
                    if i == 5:
                        # for self-test, just show orange not red
                        # self test is sadly unreliable
                        # TODO: remove this once self test is reliable
                        color = (255, 105, 0)
                    else:
                        color = (255, 0, 0)
                else:
                    color = (0, 255, 0)
                i += 1
                d.text((x, y), c, font=font_icon,
                       fill=(color[0],
                             color[1],
                             color[2],
                             self.chin["opacity"]))
                x += 30
        out = Image.alpha_composite(base, txt)
        out.paste(overlay, (0, 0), overlay)
        out = out.rotate(0)
        self.lcd.set_backlight(turn_on=True)
        self.lcd.show_image(out)

    def show_claim_info(self):
        self.config.read(CONFIG_FILE)
        self.status.read(STATUS_FILE)
        current_key = self.status.get('status', 'temporary_key')
        current_e2e_key = self.status.get('status', 'temp_e2e_key')
        serial_number = self.config.get('django', 'serial_number')
        device_number = self.config.get('django', 'id')
        display_str = [(1, "Device Key:", 0, "blue"), (2, str(current_key), 0, "white"),
                       (3, "Serial #", 0, "blue"), (4, serial_number, 0, "white"),
                       (5, "[ID]", 0, "blue"), (6, device_number, 0, "white"),
                       (7, current_e2e_key, 0, "white")]
        self.lcd.display(display_str, 20)
        # self.render()
        return True  # exit the menu

    def show_claim_info_qrcode(self):
        current_key = self.status.get('status', 'temporary_key')
        current_e2e_key = self.status.get('status', 'temp_e2e_key')
        serial_number = self.config.get('django', 'serial_number')
        display_str = [(1, "https://red.we-pn.com/?pk=" + str(current_e2e_key) + "&s=" +
                        str(serial_number) + "&k=" + str(current_key), 2, "white"), ]
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
        display_str = "Starting Diagnostics, please wait."
        self.lcd.long_text(display_str, "i", "green")
        test_port = int(self.config.get('openvpn', 'port')) + 1
        self.diag_code = diag.get_error_code(test_port)
        serial_number = self.config.get('django', 'serial_number')
        time.sleep(3)
        display_str = [(1, "Status Code", 0, "blue"), (2, str(self.diag_code), 0, "white"),
                       (3, "Serial #", 0, "blue"), (4, serial_number, 0, "white"),
                       (5, "Local IP", 0, "blue"), (6, self.device.get_local_ip(), 0, "white"),
                       (7, "MAC Address", 0, "blue"), (8, self.device.get_local_mac(), 0, "white"), ]
        self.lcd.display(display_str, 20)
        self.logger.debug(display_str)
        return True  # stay in the menu

    def show_diag_qr_code(self):
        if not hasattr(self, "diag_code"):
            self.run_diagnostics()
        display_str = [(2, "wepn://diag=" + str(self.diag_code), 2, "white"), ]
        self.lcd.display(display_str, 19)
        self.diag_shown = True
        return True  # stay in the menu

    def signal_main_wepn(self):
        with open("/var/run/pproxy.pid", "r") as f:
            wepn_pid = int(f.readline())
            self.logger.debug("Signaling main process at: " + str(wepn_pid))
            print("Signaling main process at: " + str(wepn_pid))
            try:
                os.kill(wepn_pid, signal.SIGUSR1)
            except ProcessLookupError as process_error:
                self.logger.error("Could not find the process for main wepn: " +
                                  str(wepn_pid) + ":" + str(process_error))

    def show_dummy_home(self, new_title, new_str):
        new_menu_location = len(self.menu)
        self.titles.insert(new_menu_location, {"text": new_title})
        self.lcd.display(new_str, 20)

    def append_current_title(self, new_str):
        _title = self.titles[self.menu_index]["text"] + new_str
        self.render(title=_title)

    def refresh_status(self, led_update=True):
        self.status.read(STATUS_FILE)
        diag_code = self.status.get("status", "last_diag_code")
        if diag_code != "":
            self.prev_diag_code = self.diag_code
            self.diag_code = int(diag_code)
        if led_update:
            if self.diag_code != consts.HEALTHY_DIAG_CODE:
                if self.prev_diag_code == consts.HEALTHY_DIAG_CODE:
                    # new error just detected
                    # we need to show red pulse until user interacts with device
                    self.err_pending_ack = True
                if self.err_pending_ack:
                    # only pulse if no user interaction recorded since error was detected first
                    self.led_client.pulse(color=(255, 0, 0), wait=100, repetitions=1)
                self.leds_turned_for_error = True
            else:
                if self.leds_turned_for_error:
                    # turns off LEDS only if it set them previously
                    # ideally, this will be a central place in led_manager
                    # so one process cannot clear another ones
                    # TODO(amir): updated to new patterns
                    self.leds_turned_for_error = False
                    self.led_client.blank()

    def show_home_screen(self):
        self.display_active = True
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        state = self.status.get("status", "state")
        # a cold start has recently happened,
        # so data is outdated. Don't give incorrect info
        try:
            warmed = (int(self.status.get("status", "hb_to_warm")) == 0)
        except:
            warmed = True
        if int(self.status.get("status", "claimed")) == 0:
            if self.device.needs_package_update():
                # Disable showing QR Code when software needs upgrade
                # This way the update screen will not be covered
                # Other menus work though.
                # TODO: We need a proper WindowManager
                return
            self.show_claim_info_qrcode()
        else:
            # show the status info

            self.set_current_menu(5)
            self.titles[5]["color"] = (255, 255, 255)
            self.refresh_status(led_update=True)
            self.menu[5][0]["display"] = False
            self.menu[5][1]["display"] = False
            self.menu[5][2]["text"] = "Menu"
            self.menu[5][2]["action"] = self.show_main_menu
            self.menu[5][2]["display"] = True
            # TODO: self test is unreliable, so ignore bit 2
            if (self.diag_code | 32) != consts.HEALTHY_DIAG_CODE:
                if self.prev_diag_code == consts.HEALTHY_DIAG_CODE \
                        or self.prev_diag_code == 0:
                    # first time after diag says there's an error
                    # wake up the screen, and reset the count down
                    self.screen_timed_out = False
                    # keep screen on longer
                    self.countdown_to_turn_off_screen = ERR_SCREEN_TIMEOUT
                color = (255, 0, 0)
                title = "Error"
                self.menu[5][1]["text"] = "Help"
                self.menu[5][1]["action"] = self.show_summary
                self.menu[5][1]["display"] = True
            else:
                if self.countdown_to_turn_off_screen > NRML_SCREEN_TIMEOUT:
                    self.countdown_to_turn_off_screen = NRML_SCREEN_TIMEOUT
                color = (0, 255, 0)
                title = "OK"
            if not warmed:
                # data unreliable
                title = "WEPN "
                self.menu[5][1]["display"] = False
                color = (255, 255, 255)

            self.set_current_menu(5)
            self.titles[5]["color"] = color
            self.titles[5]["text"] = title
            if warmed:
                icons, any_err, errs = self.lcd.get_status_icons_v2(state, self.diag_code)
                self.chin["text"] = icons
                self.chin["errs"] = errs
                self.chin["color"] = color
                self.chin["opacity"] = 255
            if self.screen_timed_out is False:
                self.render()

    def show_main_menu(self):
        self.display_active = True
        self.set_current_menu(0)
        self.render()

    def show_summary(self):
        self.display_active = True
        new_menu_location = len(self.menu)
        self.titles.insert(new_menu_location, {"text": "Summary"})
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        state = self.status.get("status", "state")
        icons, any_err, errs = self.lcd.get_status_icons_v2(state, self.diag_code)
        txts = [
            ["Network up", "Internet up", "Services up",
                "Reachable", "Linked", "Self-tests pass", "Claimed"],
            ["Network down", "Internet down", "Services down", "Not reachable", "Not linked", "Self-tests fail", "Not claimed"]]
        lines = []
        t = 1
        for i in range(len(icons)):
            if errs[i]:
                icon_color = "red"
                txt_color = "red"
                t = 1
            else:
                icon_color = "green"
                txt_color = "white"
                t = 0
            lines.append((txts[t][i], icons[i], txt_color, icon_color))
        self.lcd.show_summary(lines, 28)
        # stay in the menu
        return True

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

    def show_config_menu(self):
        self.display_active = True
        self.current_title = "Access"
        self.set_current_menu(6)
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
                self.led_client.set_all(color=(255, 255, 0))
            elif new_index == 1:
                # white
                self.led_client.set_all(color=(255, 255, 255))
            elif new_index == 2:
                # red
                self.led_client.set_all(color=(255, 0, 0))
            elif new_index == 3:
                # green
                self.led_client.set_all(color=(0, 255, 0))
            elif new_index == 4:
                # brown
                self.led_client.set_all(color=(165, 42, 42))
        elif new_index == 5:
            # rainbow
            self.led_enabled = True
            self.led_client.set_enabled(self.led_enabled)
            self.led_client.rainbow(rounds=5, wait=50)  # 100ms wait
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

    def channel_update(self):
        print("channel_update:" + str(self.dev_remaining) + " channel: " + self.channel)
        if self.channel == "prod":
            if self.dev_remaining == 0:
                # 7 clicks done already, switch
                self.channel = "dev"
                self.chin = {"text": "Development", "color": (
                    255, 255, 255), "opacity": 50, "errs": [False] * 7}
                self.show_software_version()
            else:
                self.dev_remaining -= 1
        else:
            if self.dev_remaining == 7:
                self.channel = "prod"
                self.chin = {"text": "Production", "color": (
                    255, 255, 255), "opacity": 50, "errs": [False] * 7}
                self.show_software_version()
            else:
                self.dev_remaining += 1
        self.render()

    def show_software_version(self):
        print("show_software_version")
        self.display_active = True
        self.set_current_menu(4)
        # ONLY FOR UX DEVELOPMENT, show the git hash
        import subprocess  # nosec: dev only, static command = no injection
        label = "production"
        if self.channel == "dev":
            git_cmd = "git log -1 --format=format:\"%H\""
            try:
                label = subprocess.check_output(  # nosec: static command, go.we-pn.com/waiver-1
                    git_cmd.split()).strip()
                label = label.decode("utf-8")[1:8]
            except subprocess.CalledProcessError:
                # self.logger.error(e.output)
                label = "no git hash"
        else:
            label = self.device.get_installed_package_version()
        self.menu[4][0]["text"] = label
        self.menu[4][0]["action"] = self.channel_update
        self.render()

    def update_software(self):
        self.display_active = True
        self.menu[4][1]["text"] = "checking ..."
        self.render()
        if self.channel == "prod":
            self.device.software_update_blocking(self.lcd, self.led_client, use_latest_sw=True)
        else:
            self.device.software_update_from_git()
        self.menu[4][1]["text"] = "Update"
        self.show_software_version()

    def generate_config(self):
        self.display_active = True
        # this should only run if device has not real config
        # while initial provisioning is happening
        self.device.generate_new_config()
        self.config.read(CONFIG_FILE)
        self.render()
        self.show_claim_info()

    def toggle_ssh_server(self):
        self.lcd.long_text("Working on SSH")
        ssh_server = "ON"
        if self.device.is_service_active(b'ssh.service'):
            ssh_server = "OFF"
        self.menu[6][1]["text"] = "SSH: " + ssh_server
        self.device.generate_ssh_host_keys()
        self.device.set_sshd_service(not
                                     self.device.is_service_active(b'ssh.service'))
        self.render()

    def toggle_remote_ssh_session(self):
        self.lcd.long_text("Working on Remote SSH")
        if not self.device.is_remote_session_running():
            # if session is not running, start
            if not self.device.is_service_active(b'ssh.service'):
                # if local ssh server is off, first turn it on
                self.menu[6][1]["text"] = "SSH: ON"
                self.menu[6][2]["text"] = "Remote: ON"
                self.device.generate_ssh_host_keys()
                self.device.set_sshd_service(True)
            # ssh to the remote server, open local port
            # note: the remote server is exclusively for this
            # connect to relay.we-pn.com
            self.device.set_remote_ssh_session(enabled=True)
        else:
            # Provider might have enabled SSH server before
            # To be safe we will turn that off too, worst case they
            # will need to enable manually again.
            self.menu[6][1]["text"] = "SSH: OFF"
            self.menu[6][2]["text"] = "Remote: OFF"
            self.device.set_sshd_service(False)
            # Disabling SSH serve would NOT terminate session too
            self.device.set_remote_ssh_session(enabled=False)

        self.render()


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
         {"text": "Software", "action": keypad.show_software_version}],
        [{"text": "LED ring: " + s, "action": keypad.toggle_led_setting},
         {"text": "Access", "action": keypad.show_config_menu}, ],
        [{"text": "Getting version ...  " + s, "action": keypad.show_software_version},
         {"text": "Update", "action": keypad.update_software}, ],
        [{"text": "", "display": False, "action": 0},
            {"text": "Help", "display": False, "action": keypad.show_summary},
            {"text": "Menu", "action": keypad.show_home_screen}],
        [{"text": "", "display": False, "action": 0},
            {"text": "", "display": False, "action": 0},
            {"text": "", "display": False, "action": 0},
         ],
    ]
    titles = [{"text": "Main"}, {"text": "Power"}, {"text": "About"}, {"text": "Settings"},
              {"text": "Software"}, {"text": "Home", "color": (255, 255, 255)}, {"text": "Access", "color": (255, 0, 0)}]

    if 0 == int(keypad.status.get('status', 'claimed')):
        items[2].insert(0, {"text": "Claim Info", "action": keypad.show_claim_info})
    if keypad.config.get('django', 'serial_number') == "CHANGE_SERIALNUM":
        items[6].insert(0, {"text": "Generate", "display": True, "action": keypad.generate_config})
    if True:
        ssh_server = "OFF"
        if keypad.device.is_service_active(b'ssh.service'):
            ssh_server = "ON"
        items[6].insert(1, {"text": "SSH: " + ssh_server, display: True,
                        "action": keypad.toggle_ssh_server})
    if True:
        remote = "OFF"
        if keypad.device.is_remote_session_running():
            remote = "ON"
        items[6].insert(2, {"text": "Remote: " + remote, display: True,
                        "action": keypad.toggle_remote_ssh_session})

    try:
        status = configparser.ConfigParser()
        status.read(STATUS_FILE)
        booted = (int(status.get("status", "booting")) == 0)
    except:
        booted = True

    while not booted:
        time.sleep(5)
        status.read(STATUS_FILE)
        booted = (int(status.get("status", "booting")) == 0)
    keypad.set_full_menu(items, titles)
    keypad.set_current_menu(5)
    # default screen is QR Code
    keypad.show_home_screen()

    ############################
    # This is an example of how screen can show a custom message
    # This is to be used for getting messages from another process (socket?)
    # Advantage of showing the messager from here is that the error message
    # will stay on (and not be overwritten by screen refreshes) until user
    # manually dismisses them
    # display_str = [(1, "Status Code", 0, "blue"), (2, "123", 0, "white"),
    #                   (3, "Serial #", 0, "blue"), (4, "123", 0, "white"),
    #                   (5, "Local IP", 0, "blue"), (6, "123", 0, "white"),
    #                   (7, "MAC Address", 0, "blue"), (8, "123", 0, "white"), ]
    # keypad.show_dummy_home("HOORA", display_str)
    while True:
        # this timeout serves 2 purposes
        # first, if menu system (Keys) are not touched in some time,
        # it will take the menu back to home
        # second, if the status of device has changed (diag code updated in heartbeat)
        # this will refresh the home screen to show the new state (thumbs down/up).
        # challenge here is that if an error message is shown, this refresh should not overwrite it
        time.sleep(UNIT_TIMEOUT)
        if keypad.menu_index == 5:
            keypad.show_home_screen()
        else:
            # this allows showing LED error even with in different menu
            keypad.refresh_status(True)
        # print("menu_active_countdown: " + str(keypad.menu_active_countdown) +
        #     " countdown_to_turnoff_screen: " + str(keypad.countdown_to_turn_off_screen) +
        #     " screen is off? " + str(keypad.screen_timed_out))
        keypad.menu_active_countdown -= 1
        if keypad.menu_active_countdown == 0:
            # this part ensures we read status and update screen info
            keypad.show_home_screen()
            keypad.menu_active_countdown = MENU_TIMEOUT
        if keypad.screen_timed_out is False:
            keypad.countdown_to_turn_off_screen -= 1
        if keypad.countdown_to_turn_off_screen == 0:
            if not FORCE_SCREEN_ON:
                keypad.screen_timed_out = True
                keypad.clear_screen()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
