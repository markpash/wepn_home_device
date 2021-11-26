import time
import busio
import board
import adafruit_aw9523

from adafruit_bus_device import i2c_device
#i2c = busio.I2C(board.SCL, board.SDA)
i2c = board.I2C()
time.sleep(1) #added
aw = adafruit_aw9523.AW9523(i2c, 0x5b)
time.sleep(1) #added
new_i2c = i2c_device.I2CDevice(i2c, 0x5b)
print("Found AW9523")
time.sleep(1) #added

# set all pins to be inputs
aw.directions = 0x0000
time.sleep(1)

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
# Set this to the GPIO of the interrupt:
INT_EXPANDER = 5
GPIO.setup(INT_EXPANDER, GPIO.IN, pull_up_down=GPIO.PUD_UP)

buffer = bytearray(2)
buffer[0]=0x00
buffer[1]=0x00
new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
print(buffer)
time.sleep(1)
buffer[0]=0x01
buffer[1]=0x00
new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
print(buffer)
time.sleep(1) #added
print("Inputs: {:016b}".format(aw.inputs))
buffer[0] = 0x06
buffer[1] = 0xfd
new_i2c.write(buffer)
new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
print(buffer)
time.sleep(1) #added
buffer[0] = 0x07
buffer[1] = 0xff
new_i2c.write(buffer)
print("Inputs: {:016b}".format(aw.inputs))
new_i2c.write_then_readinto(buffer, buffer, out_end=1, in_start=1)
print(buffer)
time.sleep(1)

while True:
    # read all input bits and print them out as binary 0/1
    # print("Int: ".format(aw.inputs))
    print("Inputs: {:016b}".format(aw.inputs))
    time.sleep(1)
    print(GPIO.input(5))
    time.sleep(1)
