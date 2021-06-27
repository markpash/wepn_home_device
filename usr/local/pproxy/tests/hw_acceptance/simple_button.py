import time
import busio
import board
import adafruit_aw9523

i2c = busio.I2C(board.SCL, board.SDA)
aw = adafruit_aw9523.AW9523(i2c)
print("Found AW9523")

# set all pins to be inputs
aw.directions = 0x0000

while True:
    # read all input bits and print them out as binary 0/1
    print("Int: ".format(aw.inputs))
    print("Inputs: {:016b}".format(aw.inputs))
    time.sleep(0.1)
