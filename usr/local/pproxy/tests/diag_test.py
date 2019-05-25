import sys
import json
import os
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)

import socket
import time
from oled import OLED
import threading
from diag import WPDiag
try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'


def open_listener(host, port):
    print("listener up...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host,port))

    s.listen(1)
    conn,addr = s.accept()
    print ('Connected by ', addr)
    data = conn.recv(8)
    conn.sendall(data)
    conn.close()

port  = 4001 
oled = OLED()
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
oled.set_led_present(config.get('hw','led'))
listener = threading.Thread(target=open_listener,args=['',port])
listener.setDaemon(True)
listener.start()
while True:
      WPD = WPDiag()
      local_ip = WPD.get_local_ip()
      print('local ip='+WPD.get_local_ip())
      
      internet = WPD.is_connected_to_internet()
      print('internet: '+str(internet))
      service = WPD.is_connected_to_service()
      print('service: '+str(service))
      WPD.open_test_port(port)
      iport = WPD.can_connect_to_external_port(port)  
      print('port test:' + str(iport))
      #error_code = 1*(local_ip is not "") + internet *2 + 4 * service + 8 * port; 
      error_code = WPD.get_error_code(0)
      print('device status code: '+str(error_code))

      s_resp = WPD.get_server_diag_analysis(error_code)
      #s_json = json.load(s_resp)
      WPD.close_test_port(port)
      print('*------------------------------------------------------------*')
      for i in s_resp:
          if i['state']:
              stat = 'OK'
          else:
              stat = 'X'
          print(stat + '\t'+i['description'])
      print('*------------------------------------------------------------*')
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
      '''
      print("local port test:" + str(WPD.can_connect_to_internal_port(port)))
      print("remote port test:" + str(WPD.can_connect_to_external_port(port)))
      break
      '''
#listener._stop()
