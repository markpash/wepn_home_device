import time
import os
import sys
from PIL import Image
from PIL import ImageDraw
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../../'
sys.path.append(up_dir)
from oled import OLED as OLED

result = True
LED = OLED()
LED.set_led_present(1)
#LED.show_logo()
#time.sleep(5)
LED.display([(1,"Next:",0,"white"), (2,"Mix of QR code",0,"white"),(3," and blue text",0,"white")], 20)
time.sleep(1)
LED.display([(1,"PIN:",0,"blue"), (2,"2018727523",0,"blue"), (3,"zxcvbnmmm,./asdfghjkl;qwertyuiop",2,"green")], 20)
#time.sleep(5)
current_result = input("PIN and number in blue, with QR code below? [y/n]>\t\n")
result = result and (current_result == "y")



LED.display([(1,"Next:",0,"white"), (2,"big boxes covering all screen:",0,"white"), (2,"red, then green, then blue",0,"white")], 10)
time.sleep(1)
for color in ["RED","GREEN","BLUE"]:
    print(color + " box")
    image = Image.new("RGB", (240, 240), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 240,240), outline=0, fill=color)
    LED.show_image(image)
    #time.sleep(5)
    current_result = input("color of box is "+color + "? [y/n]>\t\n")
    result = result and (current_result == "y")
#for ch in range(0, 255):
#   LED.display([(1,str(ch),0,136),(2,chr(ch),1,"purple")], 40)
#   time.sleep(1)
if result:
    sys.exit(0)
else:
    sys.exit(1)
