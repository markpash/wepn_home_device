import board
import neopixel
import time

pixels = neopixel.NeoPixel(board.D12, 24)

for i in range(24):
    #test red
    pixels[i] = (255/2, 0, 0)
    time.sleep(0.1)

for i in range(24):
    #test green
    pixels[i] = (0, 255/2, 0)
    time.sleep(0.1)

for i in range(24):
    #test blue
    pixels[i] = (0, 0, 255/2)
    time.sleep(0.1)

pixels.fill((0, 0, 0))


