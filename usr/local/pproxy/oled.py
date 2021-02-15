# for font reference: https://www.dafont.com/heydings-icons.font

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import Adafruit_SSD1306
import LCD_1in44
import LCD_Config
import logging.config
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
        # 2 is 1.44 waveshare ST735
        try:
            self.version = self.config.getint('hw','led-version')
        except configparser.NoOptionError as e:
            self.version = 1

        # Raspberry Pi pin configuration:
        self.RST = 24
        # Note the following are only used with SPI:
        self.DC = 23
        self.SPI_PORT = 0
        self.SPI_DEVICE = 0
        self.led_present = 0
        if self.version==2:
            self.lcd = LCD_1in44.LCD()
            Lcd_ScanDir = LCD_1in44.SCAN_DIR_DFT  #SCAN_DIR_DFT = D2U_L2R
            self.lcd.LCD_Init(Lcd_ScanDir)
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
            #self.lcd.LCD_Clear()
            width = 128 
            height = 128
            image = Image.new('RGB', (width, height))
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
        # Write two lines of text.
        for row, current_str, is_icon, color in strs:
            if not self.version==2:
                color = 255
            LCD_Config.Driver_Delay_ms(500)
            if is_icon:
                   curr_x=x_pad
                   for s in current_str.split(" "):
                     draw.text((curr_x, top), s, font=font_icon, fill=color)
                     draw.text((curr_x+len(s)*size, top), " ", font=rubik_regular, fill=255)
                     curr_x+=(len(s)+1)*size
            else:
                  draw.text((x_pad, top), current_str, font=rubik_regular, fill="BLUE")
            top = top + size
        # Display image.
        if self.version==2:
            image = image.rotate(270)
            self.lcd.LCD_ShowImage(image,0,0)
            LCD_Config.Driver_Delay_ms(100)
        else:
            disp.image(image)
            disp.display()


    def set_logo_text(self, text, x, y, color, size):
        self.logo_text = text
        self.logo_text_x = x
        self.logo_text_y = y
        self.logo_text_color = color
        self.logo_text_size = size

    def show_logo(self):
        if (self.led_present==0):
            with open(TEXT_OUT, 'w') as out:
                out.write("[WEPN LOGO]")
            return
        if self.version==2:
                self.lcd.LCD_Clear()
                img=PWD+'wepn_128_128.png'
                image = Image.open(img)
                if self.logo_text is not None:
                    rubik_regular = ImageFont.truetype(PWD+'rubik/Rubik-Bold.ttf', self.logo_text_size)
                    draw = ImageDraw.Draw(image)
                    draw.text((self.logo_text_x, self.logo_text_y), self.logo_text, font = rubik_regular, fill = self.logo_text_color)
                    self.logo_text = None
                image = image.rotate(270)
                self.lcd.LCD_ShowImage(image,0,0)
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
        return ret

