import lcd
import time
import sys
import os
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)


LCD = lcd.LCD()
LCD.set_lcd_present(1)
# LCD.display([(1,"PIN:",0, "white"), (2,"2018727523",0i, "red"), (3,"zxcvbnmmm,./asdfghjkl;qwertyuiop",2,"greed")], 20)
LCD.display([(1, "PIN:", 0, "white"), (2, "2018727523", 0, "red"),
            (3, "https://youtu.be/jYgeDSG9G0A", 2, "green")], 20)
input("PIN string shown, skip: Enter")
LCD.display([(1, "https://youtu.be/jYgeDSG9G0A", 2, "green")], 20)
input("only qr code shown, skip: Enter")

# LCD.show_logo()
#input("Logo shown, step: Enter")
for ch in range(30, 255):
    LCD.display([(1, str(ch), 0, "blue"), (2, chr(ch), 1, "blue")], 20)
    input(str(ch) + " shown ...")
