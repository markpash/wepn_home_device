# for font reference: https://www.dafont.com/heydings-icons.font

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import Adafruit_SSD1306

PWD='/usr/local/pproxy/ui/'
TEXT_OUT='/tmp/fake_oled'

class OLED:
    def __init__(self):
        # Raspberry Pi pin configuration:
        self.RST = 24
        # Note the following are only used with SPI:
        self.DC = 23
        self.SPI_PORT = 0
        self.SPI_DEVICE = 0
        self.led_present = 0
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

        # Note you can change the I2C address by passing an i2c_address parameter like:
        # disp = Adafruit_SSD1306.SSD1306_128_64(rst=self.RST, i2c_address=0x3C)
        disp = Adafruit_SSD1306.SSD1306_128_64(rst=self.RST, i2c_address=0x3C)


        # Initialize library.
        disp.begin()

        # Clear display.
        disp.clear()
        disp.display()


        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        width = disp.width
        height = disp.height
        image = Image.new('1', (width, height))

        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)

        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 1
        #shape_width = 20
        top = padding
        #bottom = height-padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x_pad = padding


        # Load default font.
        #font = ImageFont.load_default()
        #font20 = ImageFont.truetype('cool.ttf', size)
        #font20 = ImageFont.truetype('rubik/Rubik-Light.ttf', size)
        rubik_regular = ImageFont.truetype(PWD+'rubik/Rubik-Regular.ttf', size)
        #rubik_light = ImageFont.truetype('rubik/Rubik-Light.ttf', size)
        #rubik_medium = ImageFont.truetype('rubik/Rubik-Medium.ttf', size)
        font_icon = ImageFont.truetype(PWD+'heydings_icons.ttf', size)

        # Alternatively load a TTF font.  Make sure the .ttf font file
	      #is in the same directory as the python script!
        # Some other nice fonts to try: http://www.dafont.com/bitmap.php


        #sort array based on 'row' field
        # Write two lines of text.
        for row, current_str, is_icon in strs:
            if is_icon:
                   curr_x=x_pad
                   for s in current_str.split(" "):
                     draw.text((curr_x, top), s, font=font_icon, fill=255)
                     draw.text((curr_x+len(s)*size, top), " ", font=rubik_regular, fill=255)
                     curr_x+=(len(s)+1)*size
            else:
                  draw.text((x_pad, top), current_str, font=rubik_regular, fill=255)
            top = top + 18
        # Display image.
        disp.image(image)
        disp.display()

    def show_logo(self):
        if (self.led_present==0):
            with open(TEXT_OUT, 'w') as out:
                out.write("[WEPN LOGO]")
            return
        disp = Adafruit_SSD1306.SSD1306_128_64(rst=self.RST, i2c_address=0x3C)
        disp.begin()
        # Clear display.
        disp.clear()
        disp.display()
        img=PWD+'wepn_128_64.png'
        image  = Image.open(img).convert('1')
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

