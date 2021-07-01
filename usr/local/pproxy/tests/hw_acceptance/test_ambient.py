
import time
import board
import adafruit_veml7700
import os
import sys
from PIL import Image
from PIL import ImageDraw
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../../'
sys.path.append(up_dir)
from oled import OLED as OLED
LED = OLED()
LED.set_led_present(1)

i2c = board.I2C()  # uses board.SCL and board.SDA
veml7700 = adafruit_veml7700.VEML7700(i2c)
result = True

while True:
    print("Ambient light:", veml7700.light)
    time.sleep(0.1)

LED.display([(1,"Cover the ambient sensor",0,"white"),], 20)
baseline = int(veml7700.light)
current_result = input("Covered sensor and press enter\n")
print("Ambient light:", baseline)
current_result = input("Covered sensor and valid reading? [y/n]>\t\n")
result = result and (current_result == "y")


LED.display([(1,"Uncover the ambient sensor",0,"white"),], 20)
current_result = input("Uncovered sensor and press enter\n")
reading = int(veml7700.light)
delta = reading - baseline
print("Ambient light:", reading)
print("Delta = " , delta)
current_result = input("Uncovered sensor and valid reading? [y/n]>\t\n")
result = result and (current_result == "y")


LED.display([(1,"Flash a light source on the light sensor",0,"white"),], 20)
current_result = input("Flash a light at sensor  and press enter\n")
reading = int(veml7700.light)
delta = reading - baseline
print("Ambient light:", reading)
print("Delta = " , str(reading - baseline))
current_result = input("Valid reading? [y/n]>\t\n")
result = result and (current_result == "y")


if result:
    sys.exit(0)
else:
    sys.exit(1)

