import time
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
from lcd import LCD as LCD
LCD = LCD()
LCD.set_lcd_present(1)
#LCD.show_logo()
#time.sleep(5)
LCD.display([(1,"PIN:",0,"blue"), (2,"2018727523",0,"blue"), (3,"zxcvbnmmm,./asdfghjkl;qwertyuiop",2,"green")], 20)
time.sleep(10)
#for ch in range(0, 255):
#   LCD.display([(1,str(ch),0,136),(2,chr(ch),1,"purple")], 40)
#   time.sleep(1)
