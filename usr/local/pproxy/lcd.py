# for font reference: https://www.dafont.com/heydings-icons.font

try:
    import Adafruit_SSD1306
    import adafruit_rgb_display.st7789 as st7789  # pylint: disable=unused-import
    import board
    import digitalio
except Exception as err:
    print("Possibly unsupported board: " + str(err))

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFilter
from PIL import ImageFont
from PIL import ImageSequence
import logging.config
import os
import qrcode
import textwrap
import time

from constants import LOG_CONFIG
try:
    import RPi.GPIO as GPIO
    gpio_enable = True
except BaseException:
    gpio_enable = False


try:
    from configparser import configparser
except ImportError:
    import configparser

import constants as consts

CONFIG_FILE = '/etc/pproxy/config.ini'
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)
DIR = '/usr/local/pproxy/ui/'
TEXT_OUT = '/var/local/pproxy/fake_lcd'
IMG_OUT = '/var/local/pproxy/screen.png'

if gpio_enable:
    GPIO.setmode(GPIO.BCM)


class LCD:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.logo_text = None
        self.logo_text_x = None
        self.logo_text_y = None
        self.logo_text_color = None
        self.lcd_present = self.config.getint('hw', 'lcd')
        # LCD version:
        # 1 is the original b&w SSD1306,
        # 2 is 1.54 Adafruit ST7789
        try:
            self.version = self.config.getint('hw', 'lcd-version')
        except configparser.NoOptionError:
            self.version = 1
        if (self.lcd_present == 0):
            if self.version == 2 or self.version == 3:
                self.width = 240
                self.height = 240
            return

        # Raspberry Pi pin configuration:
        self.RST = 24
        # Note the following are only used with SPI:
        self.DC = 23
        self.CS = 9
        # backlight
        self.BL = 26
        self.SPI_PORT = 0
        self.SPI_DEVICE = 0
        if gpio_enable:
            if (GPIO.getmode() != 11):
                GPIO.setmode(GPIO.BCM)
        else:
            print("Error: GPIO not set")
        # proper fix incoming: version is sometimes not set right
        self.width = 240
        self.height = 240
        if self.version == 2 or self.version == 3:
            # Config for display baudrate (default max is 24mhz):
            BAUDRATE = 24000000

            # Setup SPI bus using hardware SPI:
            spi = board.SPI()
            # Configuration for CS and DC pins (these are PiTFT defaults):
            cs_pin = digitalio.DigitalInOut(board.CE0)
            dc_pin = digitalio.DigitalInOut(board.D25)
            reset_pin = digitalio.DigitalInOut(board.D24)
            self.lcd = st7789.ST7789(spi,
                                     height=self.height, width=self.width,
                                     y_offset=80, x_offset=0,
                                     rotation=180,
                                     cs=cs_pin,
                                     dc=dc_pin,
                                     rst=reset_pin,
                                     baudrate=BAUDRATE,
                                     )
        return

    def set_lcd_present(self, is_lcd_present):
        self.lcd_present = int(is_lcd_present)

    def clear(self):
        self.display((), 0)

    def set_backlight(self, turn_on=True):
        if self.lcd_present:
            if gpio_enable:
                GPIO.setup(self.BL, GPIO.OUT)
                if turn_on:
                    GPIO.output(self.BL, GPIO.HIGH)
                else:
                    GPIO.output(self.BL, GPIO.LOW)
        self.backlight_state_on = turn_on

    def get_backlight_is_on(self):
        # this function is not working as expected
        # despite documentation otherwise, reading from OUTPUT
        # seems to set it to high
        # `raspi-gpio set 26 op pn dl && raspi-gpio get 26`
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BL, GPIO.IN)
        return (GPIO.input(self.BL) == GPIO.HIGH)

    def display(self, strs, size):
        if (self.lcd_present == 0):
            with open(TEXT_OUT, 'w') as out:
                for row, current_str, vtype, color in strs:
                    spaces = 20 - len(current_str)
                    out.write("row:[" + str(row) + "] \tstring:[\t" + current_str + " " * spaces
                              + "]\ttype:[" + str(vtype) + "]  color:[" + str(color) + "]\n")
        if size < 10:
            size = 10
        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 1
        top = padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x_pad = padding
        self.set_backlight(turn_on=True)

        if self.version == 2 or self.version == 3:
            width = self.width
            height = self.height
            size = int(size * 1.5)
            x_offset = 20
            image = Image.new("RGB", (width, height), "BLACK")
        else:
            # Note you can change the I2C address by passing an i2c_address parameter like:
            disp = Adafruit_SSD1306.SSD1306_128_64(
                rst=self.RST, i2c_address=0x3C)
            # Initialize library.
            disp.begin()
            # Clear display.
            disp.clear()
            disp.display()
            # Make sure to create image with mode '1' for 1-bit color.
            width = disp.width
            height = disp.height
            x_offset = 0
            image = Image.new('1', (width, height))

        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)

        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        rubik_regular = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', size)
        # rubik_light = ImageFont.truetype('rubik/Rubik-Light.ttf', size)
        # rubik_medium = ImageFont.truetype('rubik/Rubik-Medium.ttf', size)
        font_icon = ImageFont.truetype(DIR + 'heydings_icons.ttf', size)

        # Alternatively load a TTF font.  Make sure the .ttf font file
        # is in the same directory as the python script!
        # Some other nice fonts to try: http://www.dafont.com/bitmap.php

        # sort array based on 'row' field
        # Write lines of text/icon/qr code.
        for _row, current_str, vtype, color in strs:
            vtype = int(vtype)
            if not (self.version == 2 or self.version == 3):
                color = 255
            if vtype == 1:
                # icon
                curr_x = x_pad + x_offset
                for s in current_str.split(" "):
                    draw.text((curr_x, top), s, font=font_icon, fill=color)
                    curr_x += (len(s) + 1) * size
            elif vtype == 2:
                # qr code
                # it is implied that QR codes are either the ending row, or only one
                if self.version == 2 or self.version == 3:
                    # if screen is not big, skip QR codes
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=1,
                    )
                    qr.add_data(current_str)
                    qr.make(fit=True)
                    img_qr = qr.make_image()
                    max_size = width - top - 5
                    img_qr = img_qr.resize((max_size, max_size))
                    pos = (int(width / 2 - 2 - img_qr.size[1] / 2), top + 2,)
                    image.paste(img_qr, pos)
            else:
                # normal text
                draw.text((x_pad + x_offset, top), current_str,
                          font=rubik_regular, fill=color)
            top = top + size
        # Display image.
        if (self.lcd_present == 0):
            image.save(IMG_OUT)
        else:
            if self.version == 3:
                image = image.convert('RGB')
                self.lcd.image(image, 0, 0)
            elif self.version == 2:
                image = image.rotate(270)
                self.lcd.image(image, 0, 0)
            else:
                disp.image(image)
                disp.display()

    def set_logo_text(self, text, x=60, y=200, color="red", size=15):
        self.logo_text = text
        self.logo_text_x = x
        self.logo_text_y = y
        self.logo_text_color = color
        self.logo_text_size = size

    def show_image(self, image):
        if (self.lcd_present == 0):
            image.save(IMG_OUT)
        else:
            image = image.convert('RGB')
            self.lcd.image(image, 0, 0)

    def show_logo(self, x=0, y=0):
        if (self.lcd_present == 0):
            with open(TEXT_OUT, 'w') as out:
                out.write("[WEPN LOGO]")
            return
        if self.version == 2 or self.version == 3:
            self.clear()
            self.set_backlight(1)
            # with Image.open("ui/confetti.gif") as im:
            #    index = 1
            #    while (index < 100):
            #        for frame in ImageSequence.Iterator(im):
            #            frame = frame.convert("RGBA")
            #            frame = frame.rotate(180)
            #            frame = frame.resize((240, 240))
            #            self.lcd.image(frame)
            #            index += 1
            #            # print(index)
            #            # time.sleep(0.1)
            # self.clear()

            img = DIR + 'wepn_240_240.png'
            image = Image.open(img)
            image = image.convert('RGB')
            if self.logo_text is not None:
                rubik_regular = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf',
                                                   self.logo_text_size)
                draw = ImageDraw.Draw(image)
                draw.text((self.logo_text_x, self.logo_text_y), self.logo_text,
                          # font = rubik_regular, fill = self.logo_text_color)
                          font=rubik_regular, fill=(255, 255, 255, 255))
                self.logo_text = None
            if self.version == 2:
                image = image.rotate(270)
            for i in range(0, 100):
                im2 = image.filter(ImageFilter.GaussianBlur(100 - i))
                self.lcd.image(im2, x, y)
                time.sleep(0.1)
            self.lcd.image(image, x, y)
        else:
            img = DIR + 'wepn_128_64.png'
            image = Image.open(img).convert('1')
            disp = Adafruit_SSD1306.SSD1306_128_64(
                rst=self.RST, i2c_address=0x3C)
            disp.begin()
            # Clear display.
            disp.clear()
            disp.display()
            disp.image(image)
            disp.display()
        image.save(IMG_OUT)

    def play_animation(self, filename=None, loop_count=1):
        self.clear()
        prev_backlight = self.get_backlight_is_on()
        self.set_backlight(1)
        # to avoid filename based attacks, all gifs are in the ui/ directory
        filename = os.path.basename(filename)
        with Image.open("ui/" + filename) as im:
            loops = 1
            while (loops < loop_count):
                for frame in ImageSequence.Iterator(im):
                    frame = frame.convert("RGBA")
                    frame = frame.rotate(180)
                    frame = frame.resize((240, 240))
                    self.lcd.image(frame)
                    # time.sleep(0.1)
                loops += 1
        self.clear()
        self.set_backlight(prev_backlight)

    def get_status_icons(self, status, is_connected, is_mqtt_connected):
        any_err = False
        if (status == 0 or status == 1 or status == 3):
            service = "X"  # service is off, X mark
            any_err = True
        elif (status == 4):
            service = "!"  # error in service, danger sign
            any_err = True
        else:
            service = "O"  # service is on, checkmark

        # TODO: device is calculated but not shown in error
        if (status == 1 or status == 2 or status == 4):
            # device is on
            device = chr(114)  # noqa: F841
        elif (status == 3):
            # device is restarting
            device = chr(77)  # noqa: F841
        else:
            # dvice is off
            device = chr(64)  # noqa: F841
            any_err = True

        if (is_connected):
            net = chr(51)  # network sign
        else:
            net = chr(77)  # magnifier sign
            any_err = True

        # TODO: mqtt is calculated but not shown in error
        if (is_mqtt_connected):
            # networks sign2
            _mqtt = chr(51)  # noqa: F841
        else:
            # magnifier sign2
            _mqtt = chr(77)  # noqa: F841

        if (any_err):
            err = chr(50)  # thumb up
        else:
            err = chr(56)  # thumb down
        ret = str(err) + "   " + str(net) + str(service)
        return (ret, any_err)

    def get_status_icons_v2(self, status, diag_code):
        any_err = (consts.HEALTHY_DIAG_CODE != diag_code)
        errs = [False] * 7
        flag = 1
        for i in range(7):
            if diag_code & flag:
                errs[i] = False
            else:
                errs[i] = True
            flag *= 2
        ret = chr(51) + chr(97) + chr(71) + chr(107) + chr(76) + chr(114) + chr(65)
        return (ret, any_err, errs)

    def show_menu(self, title, menu_items):
        # get a font [[MAYBE SET THE FONT GLOBALLY TOGETHER WITH BRANDING ASSETS]]
        base = Image.new("RGBA", (self.width, self.height), (0, 0, 0))
        fnt = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 30)
        # fnt_title = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 8)
        txt = Image.new("RGBA", base.size, (255, 255, 255, 0))
        d = ImageDraw.Draw(txt)
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        # title = self.titles[self.menu_index]
        # Display the menu title
        d.text((124, 2), title, font=fnt, anchor="ma", fill=(255, 255, 255, 255))
        # Define some offsets
        x = 10
        y = 0
        i = 0
        corner = None
        for item in menu_items:
            y = y + int(self.menu_row_y_size / 2) + self.menu_row_skip
            opacity = 128
            if True:
                opacity = 255
                corner = self.half_round_rectangle((200, self.menu_row_y_size), int(self.menu_row_y_size / 2),
                                                   (255, 255, 255, 128))
                corner.putalpha(18)
                cornery = y
                overlay.paste(corner, (x, cornery))
            d.text((x, y), "  " + item, font=fnt, fill=(255, 255, 255, opacity))
            i = i + 1
            y = y + int(self.menu_row_y_size / 2)
        out = Image.alpha_composite(base, txt)
        out.paste(overlay, (0, 0), overlay)
        out = out.rotate(0).convert('RGB')
        self.show_image(out)

    def show_prompt(self, title, options=[
                    {"text": "Yes", "color": "green"}, {"text": "No", "color": "red"}]):
        # get a font [[MAYBE SET THE FONT GLOBALLY TOGETHER WITH BRANDING ASSETS]]
        base = Image.new("RGBA", (self.width, self.height), (0, 0, 0))
        fnt = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 30)
        # font_icon = ImageFont.truetype(UI_DIR + './font-icon/font-awesome/Font Awesome 6 Free-Regular-400.otf', icon_size)
        # fnt_title = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 8)
        txt = Image.new("RGBA", base.size, (255, 255, 255, 0))
        d = ImageDraw.Draw(txt)
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        # title = self.titles[self.menu_index]
        y_text = 10
        # Display the menu title
        lines = textwrap.wrap(title, width=15)
        # width represents maximum characters. Meaning it will allow a
        # maximum of characters before it wraps to a new line
        if len(lines) > 2:
            raise Exception("The title text is too long. It must be less than 30 characters")
        for line in lines:
            width, height = fnt.getsize(line)
            d.text((124, y_text), line, font=fnt, anchor="ma", fill=(255, 255, 255, 255))
            y_text += height
        # Define some offsets
        x = 10
        y = 62
        i = 0
        corner = None
        for item in options:
            text = item["text"]
            color = item["color"]
            y = y + int(self.menu_row_y_size / 2) + self.menu_row_skip
            opacity = 128
            if True:
                opacity = 255
                corner = self.half_round_rectangle((120, self.menu_row_y_size), int(self.menu_row_y_size / 2),
                                                   color)
                corner.putalpha(130)
                cornery = y
                overlay.paste(corner, (x, cornery))
            d.text((x, y), "  " + text, font=fnt, fill=(255, 255, 255, opacity))
            i = i + 1
            y = y + int(self.menu_row_y_size / 2)
        out = Image.alpha_composite(base, txt)
        out.paste(overlay, (0, 0), overlay)
        out = out.rotate(0).convert('RGB')
        self.show_image(out)

    def progress_wheel(self, title, degree, color):
        """show progress circle/wheel"""
        base = Image.new("RGBA", (self.width, self.height), (0, 0, 0))
        fnt = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', 30)
        txt = Image.new("RGBA", base.size, (255, 255, 255, 0))
        d = ImageDraw.Draw(txt)
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        # Draw a Pie Slice
        radius = 100
        wheel = Image.new('RGB', (radius + 5, radius + 5), (0, 0, 0, 0))
        draw = ImageDraw.Draw(wheel)
        draw.arc((0, 0, radius, radius), start=0, end=degree, fill=color, width=20)
        # title = self.titles[self.menu_index]
        y_text = 10
        # Display the menu title
        lines = textwrap.wrap(title, width=15)
        # width represents maximum characters. Meaning it will allow a
        # maximum of characters before it wraps to a new line
        if len(lines) > 2:
            raise Exception("The title text is too long. It must be less than 15 characters")
        for line in lines:
            width, height = fnt.getsize(line)
            d.text((124, y_text), line, font=fnt, anchor="ma", fill=(255, 255, 255, 255))
            y_text += height
        # Define some offsets
        x = 70
        y = 100
        # opacity = 255
        # wheel.putalpha(130)
        overlay.paste(wheel, (x, y))
        out = Image.alpha_composite(base, txt)
        out.paste(overlay, (0, 0), overlay)
        out = out.rotate(0).convert('RGB')
        self.show_image(out)

    def show_summary(self, strs, size):
        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 1
        top = padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x_pad = padding

        if self.version == 2 or self.version == 3:
            width = self.width
            height = self.height
            pixel_size = int(size * 0.5)
            x_offset = 15
            image = Image.new("RGB", (width, height), "BLACK")
        else:
            # Note you can change the I2C address by passing an i2c_address parameter like:
            disp = Adafruit_SSD1306.SSD1306_128_64(
                rst=self.RST, i2c_address=0x3C)
            # Initialize library.
            disp.begin()
            # Clear display.
            disp.clear()
            disp.display()
            # Make sure to create image with mode '1' for 1-bit color.
            width = disp.width
            height = disp.height
            x_offset = 0
            image = Image.new('1', (width, height))

        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)
        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        rubik_regular = ImageFont.truetype(DIR + 'rubik/Rubik-Light.ttf', size)
        # rubik_light = ImageFont.truetype('rubik/Rubik-Light.ttf', size)
        # rubik_medium = ImageFont.truetype('rubik/Rubik-Medium.ttf', size)
        font_icon = ImageFont.truetype(DIR + 'heydings_icons.ttf', size)

        # sort array based on 'row' field
        # Write lines of text/icon/qr code.
        for current_str, icon, text_color, icon_color in strs:
            if (self.version == 2 or self.version == 3):
                curr_x = x_pad + x_offset
                # print(curr_x)
                # normal text
                draw.text((curr_x, top), current_str,
                          font=rubik_regular, fill=text_color)
                curr_x += (len(current_str) + 1) * pixel_size
                # print(curr_x)
                # icon
                # draw.text((curr_x, top), icon, font=font_icon, fill=icon_color)
                draw.text((self.width - (x_offset + x_pad + 10), top),
                          icon, font=font_icon, fill=icon_color)
                # add vetical offset
                top = top + size
        # Display image.
        if (self.lcd_present == 0):
            image.save(IMG_OUT)
        else:
            if self.version == 3:
                image = image.convert('RGB')
                self.lcd.image(image, 0, 0)
            elif self.version == 2:
                image = image.rotate(270)
                self.lcd.image(image, 0, 0)
            else:
                disp.image(image)
                disp.display()

    def long_text(self, txt, top_icon="i", color="red"):
        strs = [(1, str(top_icon).center(7), 1, color)]
        txt = textwrap.fill(txt, width=15, expand_tabs=True, tabsize=8)
        i = 2
        subs = txt.split("\n")
        for s in subs:
            strs.append((i, s.center(16), 0, "white"))
            i += 1

        self.display(strs, 20)
