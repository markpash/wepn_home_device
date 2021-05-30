import time
import os
import sys
from PIL import Image
from PIL import ImageDraw
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../../'
sys.path.append(up_dir)
from oled import OLED as OLED
LED = OLED()
LED.set_led_present(1)
#LED.show_logo()
#time.sleep(5)
LED.display([(1,"Next:",0,"white"), (2,"Mix of QR code",0,"white"),(3," and blue text",0,"white")], 20)
time.sleep(5)
LED.display([(1,"PIN:",0,"blue"), (2,"2018727523",0,"blue"), (3,"zxcvbnmmm,./asdfghjkl;qwertyuiop",2,"green")], 20)
time.sleep(5)
LED.display([(1,"Next:",0,"white"), (2,"big boxes covering all screen:",0,"white"), (2,"red, then blue, then green",0,"white")], 10)
time.sleep(5)
for color in ["RED","GREEN","BLUE"]:
    print(color + " box")
    image = Image.new("RGB", (240, 240), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 240,240), outline=0, fill=color)
    LED.show_image(image)
    time.sleep(5)
#for ch in range(0, 255):
#   LED.display([(1,str(ch),0,136),(2,chr(ch),1,"purple")], 40)
#   time.sleep(1)
