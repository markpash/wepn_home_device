# for font reference: https://www.dafont.com/heydings-icons.font

try:
    import board
    import digitalio
    import adafruit_rgb_display.st7789 as st7789  # pylint: disable=unused-import
    import Adafruit_SSD1306
except Exception as err:
    print("Possibly unsupported board: " + str(err))

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import logging.config
import qrcode
try:
    import RPi.GPIO as GPIO
    gpio_enable = True
except:
    gpio_enable = False


try:
    from self.configparser import configparser
except ImportError:
    import configparser


CONFIG_FILE = '/etc/pproxy/config.ini'
LOG_CONFIG = "/etc/pproxy/logging.ini"
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
        print(self.lcd_present)
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
        self.SPI_PORT = 0
        self.SPI_DEVICE = 0
        if gpio_enable:
            if (GPIO.getmode() != 11):
                GPIO.setmode(GPIO.BCM)
            else:
                print("GPIO is already BCM")
        else:
            print("GPIO not set")
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

    def display(self, strs, size):
        if (self.lcd_present == 0):
            with open(TEXT_OUT, 'w') as out:
                for row, current_str, vtype, color in strs:
                    spaces = 20 - len(current_str)
                    out.write("row:[" + str(row) + "] \tstring:[\t" + current_str + " " * spaces
                              + "]\ttype:[" + str(vtype) + "]  color:[" + str(color) + "]\n")

        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 1
        top = padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x_pad = padding

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
        self.lcd.image(image, 0, 0)

    def show_logo(self, x=0, y=0):
        if (self.lcd_present == 0):
            with open(TEXT_OUT, 'w') as out:
                out.write("[WEPN LOGO]")
            return
        if self.version == 2 or self.version == 3:
            img = DIR + 'wepn_240_240.png'
            image = Image.open(img)
            if self.logo_text is not None:
                rubik_regular = ImageFont.truetype(DIR + 'rubik/Rubik-Bold.ttf',
                                                   self.logo_text_size)
                draw = ImageDraw.Draw(image)
                draw.text((self.logo_text_x, self.logo_text_y), self.logo_text,
                          # font = rubik_regular, fill = self.logo_text_color)
                          font=rubik_regular, fill=(255, 255, 255, 255))
                self.logo_text = None
            if self.version == 2:
                image = image.rotate(270)
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
        any_err = (127 != diag_code)
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

        if (any_err):
            err = chr(50)  # thumb up
        else:
            err = chr(56)  # thumb down
        ret = str(err) + str(service) + str(device)
        return (ret, any_err)
