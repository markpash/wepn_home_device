import time
from oled import OLED as OLED
LED = OLED()
LED.set_led_present(1)
#LED.display([(1,"PIN:",0), (2,"2018727523",0), (3,"zxcvbnmmm,./asdfghjkl;qwertyuiop",1)], 20)
for ch in range(0, 255):
   LED.display([(1,str(ch),0),(2,chr(ch),1)], 20)
   input()
