import sys
import os
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
import time
import oled

LED = oled.OLED()
LED.set_led_present(1)
LED.display([(1,"PIN:",0), (2,"2018727523",0), (3,"zxcvbnmmm,./asdfghjkl;qwertyuiop",1)], 20)
input("PIN string shown, skip: Enter")

LED.show_logo()
input("Logo shown, skep: Enter")
for ch in range(30, 255):
   LED.display([(1,str(ch),0),(2,chr(ch),1)], 20)
   input(str(ch)+" shown ...")
