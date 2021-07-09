import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
from diag import WPDiag
import time
from lcd import LCD

try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'

lcd = LCD()
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
lcd.set_lcd_present(config.get('hw','lcd'))

while True:
      WPD = WPDiag()
      local_ip = Device.get_local_ip()
      print('local ip='+local_ip)
      internet = WPD.is_connected_to_internet()
      print("* Internet connected?")
      print(internet)
      service = WPD.is_connected_to_service()
      print("* Conncted to service?")
      print(service)
      port = WPD.can_connect_to_external_port(1194)  
      print("*Connected to external port?")
      print(port)
      error_code = 1*(local_ip is not "") + internet *2 + 4 * service + 8 * port; 
      display_str = [(1, "internet="+str(internet),0), (2,"service="+str(service) , 0), (3,"port="+str(port),0)]
      lcd.display(display_str, 10)
      display_str = [(1, "error_code="+str(error_code),0)]
      try:
          lcd.display(display_str, 17)
      except:
          print("Retrying in 60 seconds ....")
          time.sleep(60)
          continue
      break
