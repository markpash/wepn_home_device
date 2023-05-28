from lcd import LCD as LCD
from led_client import LEDClient
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)

lcd = LCD()
lcd.set_lcd_present(1)
display_str = [(1, "", 0, "black"), ]
lcd.display(display_str, 20)
lcd.set_backlight(on=False)
led_client = LEDClient()
led_client.blank()
