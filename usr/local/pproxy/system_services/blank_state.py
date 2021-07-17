import sys, os
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)

from lcd import LCD as LCD
from led_client import LEDClient
lcd = LCD()
lcd.set_lcd_present(1)
display_str = [(1, "",0,"black"), ]
lcd.display(display_str, 20)
led_client = LEDClient()
led_client.blank()
