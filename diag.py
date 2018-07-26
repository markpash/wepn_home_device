import socket
import netifaces as ni
import shlex
import subprocess
import json
import requests
from device import Device
 
try:
    from self.configparser import configparser
except ImportError:
    import configparser
from ipw import IPW
from wstatus import WStatus

ipw= IPW()

CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'

class WPDiag:

    def __init__(self):
       self.config = configparser.ConfigParser()
       self.config.read(CONFIG_FILE)
       self.status = WStatus()
       self.claimed = self.status.get('claimed')
       self.port = 987
       self.mqtt_connected = 0
       self.mqtt_reason = 0
       self.device = Device()

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))

    def execute_cmd(self, cmd):
        try:
            args = shlex.split(cmd)
            subprocess.Popen(args)
        except Exception as error_exception:
            print("Error happened in running command:" + cmd)
            print("Error details:\n"+str(error_exception))
            system.exit()

    def get_local_ip(self):
       try:
          ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
       except KeyError:
          pass
          ip= ""; 
       return ip

    def open_test_port(self, port):
        self.device.open_port(port, 'pproxy test port')

    def close_test_port(self, port):
        self.device.close_port(port)
       
    def is_connected_to_internet(self):
        try:
            # connect to the host -- tells us if the host is actually
            # reachable
            socket.create_connection(("www.google.com", 80),10)
            return True
        except OSError:
            pass
            return False

    def is_connected_to_service(self):
        try:
            socket.create_connection(("www.we-pn.com", 443),10)
            return True
        except OSError:
            pass
            return False

    def can_connect_to_external_port(self,port):
        try:
            external_ip = str(ipw.myip())
            print('.external ip is '+str(external_ip))
            s = socket.create_connection((external_ip, port),10)
            s.sendall(b'test\n')
            return True
        except OSError:
            pass
            return False

    def can_connect_to_internal_port(self,port):
        try:
            internal_ip = str(self.get_local_ip())
            print('local ip is '+str(internal_ip))
            s = socket.create_connection((internal_ip, port),10)
            s.sendall(b'test\n')
            return True
        except OSError:
            pass
            return False

    def can_shadow_to_self(self,port):
        try:
            #cmd = "/usr/bin/python shadow_diag.py -c aes-ctr.json"
            #r = self.execute_cmd(cmd)
            print("return values is ")
            return True
        except OSError:
            pass
            return False

    def set_mqtt_state(self,is_connected, reason):
        self.mqtt_connected = is_connected
        self.mqtt_reason = reason

    def get_error_code(self,port):
        local_ip = self.get_local_ip()
        internet = self.is_connected_to_internet()
        service = self.is_connected_to_service()
        port = self.can_connect_to_external_port(port)    
        shadow = self.can_shadow_to_self(port)
        mqtt = int(self.status.get('mqtt'))
        claimed = int(self.status.get('claimed'))
        error_code = (local_ip is not "") + (internet << 1) +  (service<< 2) + (port << 3) + (mqtt << 4) + (shadow << 5) + (claimed << 6)
        return error_code



    def get_server_diag_analysis(self, error_code):
        headers = {"Content-Type": "application/json"}
        data = {
                "device_code": error_code,
                }
        data_json = json.dumps(data)
        url = self.config.get('django', 'url')+"/api/device/diagnosis/"
        try:
            response = requests.post(url, data=data_json, headers=headers)
            print(response.status_code)
            return response.json()
        except requests.exceptions.RequestException as exception_error:
            print("Error" + str(exception_error))
            pass
