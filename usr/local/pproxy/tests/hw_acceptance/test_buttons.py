import time
import busio
import board
import digitalio
import adafruit_aw9523
import sys
import os
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../../'
sys.path.append(up_dir)
import time
import oled

from adafruit_bus_device import i2c_device

display = True

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
# Set this to the GPIO of the interrupt:
INT_EXPANDER = 5
GPIO.setup(INT_EXPANDER, GPIO.IN, pull_up_down=GPIO.PUD_UP)

i2c = board.I2C()
buffer = bytearray(2)
#buffer[0] = 0x7f
#buffer[1] = 0x01

LED = oled.OLED()
LED.set_led_present(1)

aw = adafruit_aw9523.AW9523(i2c)
new_i2c = i2c_device.I2CDevice(i2c, 0x58)
print("Found it")

aw.directions = 0x0000
# manually enable interrupts
buffer[0] = 0x06
buffer[1] = 0x00
new_i2c.write(buffer)


# keep track which button is pressed
pressed = [False]*7
buttons = ["1","2","3","ok","home","up","down"]



# now we'll define the threaded callback function
# this will run in another thread when our event is detected
def my_callback(channel):
    #time.sleep(0.5)
    print("CALLBACK is called")
    inputs = aw.inputs
    print("Inputs: {:016b}".format(inputs))
    print(inputs)
    return
    if inputs>0:
        pressed[inputs-1]=True
    pressed_ones = ""
    not_pressed_ones =""
    i=0
    for p in pressed:
        if p:
            pressed_ones += buttons[i] + ", "
        else:
            not_pressed_ones += buttons[i] + ", "
        i+=1
    print(pressed_ones)
    print(not_pressed_ones)
    if display:
        LED.display([(1,"Press all buttons",0, "white"), (2,pressed_ones,0, "green"), (3,not_pressed_ones,0,"red")], 15)

if display:
    LED.display([(1,"Press all buttons",0, "white"), (2,"",0, "Green"), (3,"1,2,3,ok,home,up, down",0,"red")], 15)
try:
    GPIO.add_event_detect(INT_EXPANDER, GPIO.FALLING, callback=my_callback)
    #GPIO.wait_for_edge(INT_EXPANDER, GPIO.FALLING)
    while 1:
        time.sleep(100)
except KeyboardInterrupt:
    GPIO.cleanup()       # clean up GPIO on CTRL+C exit
GPIO.cleanup()           # clean up GPIO on normal exit
