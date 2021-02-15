import time
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
from oled import OLED as OLED
LED = OLED()
LED.set_led_present(1)
#LED.show_logo()
#time.sleep(5)
LED.display([(1,"PIN:",0,"blue"), (2,"2018727523",0,"blue"), (3,"zxcvbnmmm,./asdfghjkl;qwertyuiop",2,"green")], 20)
time.sleep(10)
#for ch in range(0, 255):
#   LED.display([(1,str(ch),0,136),(2,chr(ch),1,"purple")], 40)
#   time.sleep(1)
