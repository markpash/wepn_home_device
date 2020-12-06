import socket
import netifaces as ni
import shlex
import subprocess
import json
import requests
import threading
from device import Device
import time 
 
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

    def __init__(self, logger):
       self.logger = logger
       self.config = configparser.ConfigParser()
       self.config.read(CONFIG_FILE)
       self.status = WStatus(logger)
       self.claimed = self.status.get('claimed')
       self.iface = str(self.config.get('hw','iface'))
       self.port = 987
       self.mqtt_connected = 0
       self.mqtt_reason = 0
       self.device = Device(logger)
       self.listener = None
       self.shutdown_listener = False

    def __del__(self):
        if self.listener:
            self.listener._stop()

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))

    def execute_cmd(self, cmd):
        try:
            args = shlex.split(cmd)
            subprocess.Popen(args)
        except Exception as error_exception:
            self.logger.error("Error happened in running command:" + cmd)
            self.logger.error("Error details:"+str(error_exception))
            system.exit()

    def get_local_ip(self):
       try:
          ip = ni.ifaddresses(self.iface)[ni.AF_INET][0]['addr']
       except KeyError:
          pass
          ip= ""; 
       return ip

    def get_local_mac(self):
       try:
          mac = ni.ifaddresses(self.iface)[ni.AF_LINK][0]['addr']
       except KeyError:
          pass
          mac= ""; 
       return mac

    def open_listener(self, host, port):
        self.logger.debug("listener starting..." + str(port))
        start = int(time.time())
        print(start)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)
        try:
            s.bind((host,port))
        except OSError as err:
            self.logger.error("OSError in openning diag listener: "+str(err))
            return

        #this listener should die after one connection
        #if port forwarding does not work, it will stay alive, so
        # destructor will stop this thread
        s.listen(1)
        while not self.shutdown_listener:
            if int(time.time()) - start > 120:
                    self.shutdown_listener = True
            self.logger.info ('waiting ... ')
        conn,addr = s.accept()
            self.logger.info ('Connected by '+ str(addr[0]))
        data = conn.recv(8)
        conn.sendall(data)
        conn.close()

    def open_test_port(self, port):
        self.shutdown_listener = False
        self.listener = threading.Thread(target=self.open_listener,args=['',port])
        self.listener.setDaemon(True)
        self.listener.start()
        self.device.open_port(port, 'pproxy test port')

    def close_test_port(self, port):
        self.shutdown_listener = True
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

    # DEPRECATED
    # Getting to the extrenal port from the device itself is not reliable,
    # and many consumer routers lack the "route back" capability.
    # As a result, we use the server to run a test for us now
    def can_connect_to_external_port(self,port):
        try:
            external_ip = str(ipw.myip())
            self.logger.debug('Diag: external ip is '+str(external_ip))
            s = socket.create_connection((external_ip, port),10)
            s.sendall(b'test\n')
            return True
        except OSError as err:
            print(err)
            pass
            return False


    def request_port_check(self, port):
        experiment_num = 0
        headers = {"Content-Type": "application/json"}
        data = {
            "serial_number": self.config.get('django', 'serial_number'),
            "device_key":self.config.get('django', 'device_key'),
            "input":{"port":str(port),"experiment_name":"HB started"},
        }
        data_json = json.dumps(data)
        self.logger.debug("Port check data to send: " +data_json)
        url = self.config.get('django', 'url')+"/api/experiment/"
        try:
            response = requests.post(url, data=data_json, headers=headers)
            self.logger.debug("Response to port check request" + str(response.status_code))
            resp = response.json()
            experiment_num = resp['id']
        except requests.exceptions.RequestException as exception_error:
            self.logger.error("Error in sending portcheck request: \r\n\t" + str(exception_error))
        return experiment_num

    def fetch_port_check_results(self, experiment_number):
        headers = {"Content-Type": "application/json"}
        data = {
                "serial_number": self.config.get('django', 'serial_number'),
                "device_key":self.config.get('django', 'device_key'),
                }
        data_json = json.dumps(data)
        url = self.config.get('django', 'url')+"/api/experiment/"+ experiment_number+"/result/"
        try:
            response = requests.post(url, data=data_json, headers=headers)
            self.logger.info("server experiment results" + str(response.status_code))
            self.logger.info(response.json())
            return response.json()
        except requests.exceptions.RequestException as exception_error:
            self.logger.error("Error is parsing experiment results: " + str(exception_error))
            pass
        return

    def can_connect_to_internal_port(self,port):
        #NOTE: if this is used, make sure there is an extra port listener
        #running. By default, only one connection will be handled.
        try:
            internal_ip = str(self.get_local_ip())
            self.logger.debug('Diag connect internet: local ip is '+str(internal_ip))
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
            #print("return values is ")
            return True
        except OSError:
            pass
            return False

    def set_mqtt_state(self,is_connected, reason):
        self.mqtt_connected = is_connected
        self.mqtt_reason = reason

    def get_error_code(self,port_no):
        local_ip = self.get_local_ip()
        internet = self.is_connected_to_internet()
        service = self.is_connected_to_service()
        self.open_test_port(port_no)
        shadow = self.can_shadow_to_self(port_no)
        mqtt = int(self.status.get('mqtt'))
        claimed = int(self.status.get('claimed'))
        port = 0
        if self.status.get_field('port_check', 'result')=="True":
            port = 1
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
            self.logger.info("server diag analysis:" + str(response.status_code))
            return response.json()
        except requests.exceptions.RequestException as exception_error:
            self.logger.error("Error is parsing server's diag analysis: " + str(exception_error))
            pass
