# for font reference: https://www.dafont.com/heydings-icons.font

import board
import digitalio
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import adafruit_rgb_display.st7789 as st7789  # pylint: disable=unused-import
import Adafruit_SSD1306
import logging.config
import qrcode

try:
    from self.configparser import configparser
except ImportError:
    import configparser


CONFIG_FILE='/etc/pproxy/config.ini'
LOG_CONFIG="/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)
PWD='/usr/local/pproxy/ui/'
TEXT_OUT='/tmp/fake_oled'


class OLED:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        # LED version:
        # 1 is the original b&w SSD1306,
        # 2 is 1.54 Adafruit ST7789
        try:
            self.version = self.config.getint('hw','led-version')
        except configparser.NoOptionError as e:
            self.version = 1

        # Raspberry Pi pin configuration:
        self.RST = 24
        # Note the following are only used with SPI:
        self.DC = 23
        self.CS = 9
        self.SPI_PORT = 0
        self.SPI_DEVICE = 0
        self.led_present = 0
        if self.version==2:
            # Config for display baudrate (default max is 24mhz):
            BAUDRATE = 24000000

            # Setup SPI bus using hardware SPI:
            spi = board.SPI()
            # Configuration for CS and DC pins (these are PiTFT defaults):
            cs_pin = digitalio.DigitalInOut(board.CE0)
            dc_pin = digitalio.DigitalInOut(board.D25)
            reset_pin = digitalio.DigitalInOut(board.D24)
            self.lcd = st7789.ST7789(spi, 
                height=240, width=240,
                y_offset=80, x_offset=0,
                rotation=180,
                cs=cs_pin,
                dc=dc_pin,
                rst=reset_pin,
                baudrate=BAUDRATE,
            )
        self.logo_text = None
        self.logo_text_x = None
        self.logo_text_y = None
        self.logo_text_color = None
        return
    def set_led_present(self, is_led_present):
        self.led_present = int(is_led_present)

    def display(self, strs, size):
        if (self.led_present == 0):
            with open(TEXT_OUT, 'w') as out:
                for row, current_str, is_icon in strs:
                    spaces = 20 - len(current_str)
                    out.write("row=["+ str(row) + "] \tstring=[\t" + current_str + " "*spaces + "]\ticon? [" + str(is_icon) + "]\n");
            return

        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 1
        #shape_width = 20
        top = padding
        #bottom = height-padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x_pad = padding

        if self.version==2:
            width = 240 
            height = 240
            size = int(size*1.5)
            image = Image.new("RGB", (width, height), "BLACK")
        else:
            # Note you can change the I2C address by passing an i2c_address parameter like:
            disp = Adafruit_SSD1306.SSD1306_128_64(rst=self.RST, i2c_address=0x3C)
            # Initialize library.
            disp.begin()
            # Clear display.
            disp.clear()
            disp.display()
            # Make sure to create image with mode '1' for 1-bit color.
            width = disp.width
            height = disp.height
            image = Image.new('1', (width, height))

        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)

        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)



        # Load default font.
        #font = ImageFont.load_default()
        #font20 = ImageFont.truetype('cool.ttf', size)
        #font20 = ImageFont.truetype('rubik/Rubik-Light.ttf', size)
        rubik_regular = ImageFont.truetype(PWD+'rubik/Rubik-Light.ttf', size)
        #rubik_light = ImageFont.truetype('rubik/Rubik-Light.ttf', size)
        #rubik_medium = ImageFont.truetype('rubik/Rubik-Medium.ttf', size)
        font_icon = ImageFont.truetype(PWD+'heydings_icons.ttf', size)

        # Alternatively load a TTF font.  Make sure the .ttf font file
        #is in the same directory as the python script!
        # Some other nice fonts to try: http://www.dafont.com/bitmap.php


        #sort array based on 'row' field
        # Write lines of text/icon/qr code.
        for row, current_str, vtype, color in strs:
            vtype = int(vtype)
            if not self.version==2:
                color = 255
            if vtype == 1:
                   # icon
                   curr_x=x_pad
                   for s in current_str.split(" "):
                     draw.text((curr_x, top), s, font=font_icon, fill=color)
                     #draw.text((curr_x+len(s)*size, top), " ", font=rubik_regular, fill=255)
                     curr_x+=(len(s)+1)*size
            elif vtype == 2:
                # qr code
                # it is implied that QR codes are either the ending row, or only one
                if self.version==2:
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
                    #pos = (image.size[0] - img_qr.size[0]-5, image.size[1] - img_qr.size[1]-5)
                    pos = (int(width/2 - 2 - img_qr.size[1]/2), top + 2,)
                    image.paste(img_qr, pos)
            else:
                # normal text
                  draw.text((x_pad, top), current_str, font=rubik_regular, fill=color)
            top = top + size
        # Display image.
        if self.version==2:
            image = image.rotate(270)
            self.lcd.image(image,0,0)
        else:
            disp.image(image)
            disp.display()
        image.save("/tmp/screen.png")


    def set_logo_text(self, text, x, y, color, size):
        self.logo_text = text
        self.logo_text_x = x
        self.logo_text_y = y
        self.logo_text_color = color
        self.logo_text_size = size

    def show_image(self, image):
        self.lcd.image(image,0,0)

    def show_logo(self):
        if (self.led_present==0):
            with open(TEXT_OUT, 'w') as out:
                out.write("[WEPN LOGO]")
            return
        if self.version==2:
                img=PWD+'wepn_240_240.png'
                image = Image.open(img)
                if self.logo_text is not None:
                    rubik_regular = ImageFont.truetype(PWD+'rubik/Rubik-Bold.ttf', self.logo_text_size)
                    draw = ImageDraw.Draw(image)
                    draw.text((self.logo_text_x, self.logo_text_y), self.logo_text, font = rubik_regular, fill = self.logo_text_color)
                    self.logo_text = None
                image = image.rotate(270)
                self.lcd.image(image,0,0)
        else:
            img=PWD+'wepn_128_64.png'
            image  = Image.open(img).convert('1')
            disp = Adafruit_SSD1306.SSD1306_128_64(rst=self.RST, i2c_address=0x3C)
            disp.begin()
            # Clear display.
            disp.clear()
            disp.display()
            disp.image(image)
            disp.display()
        image.save("/tmp/screen.png")

    def get_status_icons(self, status, is_connected, is_mqtt_connected):
        any_err = False 
        if (status == 0 or status == 1 or status == 3):
            service = "X" #service is off, X mark
            any_err = True
        elif (status == 4):
            service = "!"  #error in service, danger sign
            any_err = True
        else:
            service = "O" #service is on, checkmark

        if (status == 1 or status == 2 or status == 4):
            device =  chr(114) #device is on
        elif (status == 3):
            device = chr(77) #device is restarting
        else:
            device = chr(64) #device is off
            any_err = True

        if (is_connected):
           net = chr(51) #network sign
        else:
           net = chr(77) #magnifier sign
           any_err = True

        if (is_mqtt_connected):
           mqtt = chr(51) #netis_mqtt_connectedwork sign
        else:
           mqtt = chr(77) #magnifier sign
           #any_err = True

        if (any_err):
           err = chr(50)  #thumb up
        else:
           err = chr(56)  #thumb down
        ret=str(err)+"   "+str(net)+str(service)
        return (ret, any_err)

