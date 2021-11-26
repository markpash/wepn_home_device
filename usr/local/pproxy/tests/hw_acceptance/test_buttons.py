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
import lcd
import math

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

LCD = lcd.LCD()
LCD.set_lcd_present(1)

aw = adafruit_aw9523.AW9523(i2c, 0x58)
new_i2c = i2c_device.I2CDevice(i2c, 0x58)
print("Found it")

# manually enable interrupts
#aw.interrupts_enables = 0x00
aw.directions = 0x0000
#aw.reset()
time.sleep(1)


new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
print(buffer)
buffer[0] = 0x06
buffer[1] = 0x00
new_i2c.write(buffer)
new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
print(buffer)

buffer[0]=0x07
buffer[1] = 0xff
new_i2c.write(buffer)
#print(buffer)
new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
print(buffer)


# keep track which button is pressed
pressed = [False]*7
buttons = ["1","2","3","up","down","ok","home"]


time.sleep(1)


# now we'll define the threaded callback function
# this will run in another thread when our event is detected
def my_callback(channel):
    #time.sleep(0.5)
    print("CALLBACK is called")
    inputs = aw.inputs
    print("Inputs: {:016b}".format(inputs))
    print(inputs)
    inputs = 127 - inputs & 0x7F
    print(inputs)
    if inputs < 0:
        return
    index = (int)(math.log2(inputs))
    print("index is")
    print(index)
    #return
    if inputs>0:
        pressed[index]=True
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
        LCD.display([(1,"Press all buttons",0, "white"), (2,pressed_ones,0, "green"), (3,not_pressed_ones,0,"red")], 15)
    if len(not_pressed_ones) == 0:
        LCD.display([(1,"Buttons:",0, "white"), (2,"PASSED",0, "green"), ], 15)
        sys.exit(0)

if display:
    LCD.display([(1,"Press all buttons",0, "white"), (2,"",0, "Green"), (3,"1,2,3,ok,home,up, down",0,"red")], 15)
try:
    print("Inputs: {:016b}".format(aw.inputs))
    GPIO.add_event_detect(INT_EXPANDER, GPIO.FALLING, callback=my_callback)
    print("Inputs: {:016b}".format(aw.inputs))
    #GPIO.wait_for_edge(INT_EXPANDER, GPIO.FALLING)
    while 1:
        time.sleep(100)
except KeyboardInterrupt:
    #GPIO.cleanup()       # clean up GPIO on CTRL+C exit
    print("HAHHA")
#GPIO.cleanup()           # clean up GPIO on normal exit
