from diag import WPDiag
import time
from oled import OLED

try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'

oled = OLED()
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
oled.set_led_present(config.get('hw','led'))

while True:
      WPD = WPDiag()
      local_ip = WPD.get_local_ip()
      print('local ip='+WPD.get_local_ip())
      internet = WPD.is_connected_to_internet()
      print(internet)
      service = WPD.is_connected_to_service()
      print(service)
      port = WPD.can_connect_to_external_port(1194)  
      print(port)
      error_code = 1*(local_ip is not "") + internet *2 + 4 * service + 8 * port; 
      display_str = [(1, "internet="+str(internet),0), (2,"service="+str(service) , 0), (3,"port="+str(port),0)]
      oled.display(display_str, 10)
      display_str = [(1, "error_code="+str(error_code),0)]
      try:
          oled.display(display_str, 17)
      except:
          print("Retrying in 60 seconds ....")
          time.sleep(60)
          continue
      break
