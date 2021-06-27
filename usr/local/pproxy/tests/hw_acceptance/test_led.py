import board
import sys
import neopixel
import time

result = True
pixels = neopixel.NeoPixel(board.D12, 24)

for i in range(24):
    #test red
    pixels[i] = (255/2, 0, 0)
    time.sleep(0.1)
current_result = input("all LEDs filled with red? [y/n]>\t\n")
result = result and (current_result == "y")


for i in range(24):
    #test green
    pixels[i] = (0, 255/2, 0)
    time.sleep(0.1)
current_result = input("all LEDs filled with green? [y/n]>\t\n")
result = result and (current_result == "y")

for i in range(24):
    #test blue
    pixels[i] = (0, 0, 255/2)
    time.sleep(0.1)
current_result = input("all LEDs filled with blue? [y/n]>\t\n")
result = result and (current_result == "y")

pixels.fill((0, 0, 0))



if result:
    sys.exit(0)
else:
    notes = input("Leave a note of what went wrong:\n")
    sys.exit(1)
