import sys
import os
import time
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)
import lcd # noqa


LCD = lcd.LCD()
LCD.set_lcd_present(1)
LCD.set_backlight(True)
LCD.play_animation("barbie.gif", 10)
exit()
time.sleep(1)
print("Shows this function is not working right: backlight is on?" + str(lcd.get_backlight_is_on()))
# LCD.display([(1,"PIN:",0, "white"), (2,"2018727523",0i, "red"), (3,"zxcvbnmmm,./asdfghjkl;qwertyuiop",2,"greed")], 20)
LCD.display([(1, "PIN:", 0, "white"), (2, "2018727523", 0, "red"),
            (3, "https://youtu.be/jYgeDSG9G0A", 2, "green")], 20)
input("PIN string shown, skip: Enter")
LCD.display([(1, "https://youtu.be/jYgeDSG9G0A", 2, "green")], 20)
input("only qr code shown, skip: Enter")

LCD.show_logo()
LCD.play_animation("/etc/passwd", 2)
input("Logo shown, step: Enter")
for ch in range(30, 255):
    LCD.display([(1, str(ch), 0, "blue"), (2, chr(ch), 1, "blue")], 20)
    input(str(ch) + " shown ...")
