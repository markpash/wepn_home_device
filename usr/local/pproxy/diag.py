import socket
import netifaces as ni
import shlex
import subprocess
import json
import requests
import threading
from device import Device
import time 
import atexit
import datetime as datetime
from datetime import timedelta
import dateutil.parser
import logging.config
 
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
       atexit.register(self.cleanup)

    def cleanup(self):
        self.shutdown_listener = True

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


    def open_listener(self, host, port):
        self.logger.debug("listener starting..." + str(port))
        start = int(time.time())
        print(start)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)
        try:
            s.bind((host,int(port)))
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
            "input":{"port":str(port),"experiment_name":"port_test"},
        }
        data_json = json.dumps(data)
        self.logger.debug("Port check data to send: " +data_json)
        url = self.config.get('django', 'url')+"/api/experiment/"
        try:
            response = requests.post(url, data=data_json, headers=headers)
            self.logger.debug("Response to port check request" + str(response.status_code))
            resp = response.json()
            self.logger.error("response: \r\n\t" + str(resp))
            experiment_num = resp['id']
        except requests.exceptions.RequestException as exception_error:
            self.logger.error("Error in sending portcheck request: \r\n\t" + str(exception_error))
            self.logger.error("response: \r\n\t" + str(resp))
        except KeyError as key_missing_err:
            self.logger.error("Error in gettin the resonse: \r\n\t" + str(key_missing_err))
            self.logger.error("response: \r\n\t" + str(resp))
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

    # Method to get the results of a pending experiment from the server
    # True: keep waiting
    # False: got it done
    def get_results_from_server(self, port):
           result =  self.fetch_port_check_results(self.status.get_field("port_check","experiment_number"))
           try:
               if result['finished_time'] != None:
                       self.logger.info("test results are in")
                       self.close_test_port(port)
                       self.status.set_field("port_check","pending", False)
                       try:
                           self.status.set_field("port_check","result", result['result']['experiment_result'])
                           self.status.set_field("port_check","last_check", str(result['finished_time']))
                       except:
                           self.logger.error("result from server did not contain actual results")
                           self.status.set_field("port_check","result", False)
                           pass
                       self.status.save()
                       return False
               else:
                    self.logger.info("still waiting for test results")
                    return True 
           except KeyError as key_err:
                self.logger.error("Error in the results parsing: \t\r\n" + str(key_err))
                return False

    # This method is a big wrapper to take care of all port testing aspects
    # If a recent result is available, just skips doing anything
    # If an experiment is ongoing (pending), just try fetching results of that
    # If neither of above, try starting a new one
    def perform_server_port_check(self, port):

        if self.status.has_section("port_check"):
            last_port_check = self.status.get_field("port_check","last_check")
            self.logger.info("last port check was " + str(last_port_check))
            last_check_date = dateutil.parser.parse(last_port_check)
            self.logger.info("last port check was " + str(last_check_date))


            long_term_expired = (last_check_date.replace(tzinfo=None) < 
                    (datetime.datetime.now().replace(tzinfo=None) + timedelta(days = -1)))
            short_term_expired = (last_check_date.replace(tzinfo=None) 
                    < (datetime.datetime.now().replace(tzinfo=None) + timedelta(hours = -2)))
            previous_failed = self.status.get_field("port_check","result") == "False"

            self.logger.info("pending test results? " + self.status.get_field("port_check","pending"))
            if self.status.get_field("port_check","pending") == "True":
               self.logger.debug("A test has been initiated previously, getting the results")
               self.get_results_from_server(port)
            elif long_term_expired or (previous_failed and short_term_expired): 
               #results are too old, request a new one
               self.logger.info("port test results too old recently failed, retesting")
               # please note that the port opened here will be closed by either
               # (1) server successfully making a connection to it, or
               # (2) timing out
               # (3) a call to get_results_from_server. In theory 1 covers this too.
               self.open_test_port(port)
               experiment_number = self.request_port_check(port)
               if experiment_number > 0:
                   self.logger.debug("requesting new port check: " + str(experiment_number))
                   self.status.set_field("port_check","pending", True)
                   self.status.set_field("port_check","experiment_number", experiment_number)
                   self.status.save()
               else:
                    self.logger.error("HB request to start port check returned bad id 0")

               time.sleep(15)
               attempts = 0
               while self.get_results_from_server(port):
                    time.sleep(5)
                    attempts += 1
                    if attempts > 5:
                        # it is taking too long, let a future call retreive it
                        # the 'pending' status variable is used for this
                        break

    def can_connect_to_internal_port(self,port):
        #NOTE: if this is used, make sure there is an extra port listener
        #running. By default, only one connection will be handled.
        try:
            internal_ip = str(self.device.get_local_ip())
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
        local_ip = self.device.get_local_ip()
        internet = self.is_connected_to_internet()
        service = self.is_connected_to_service()
        self.perform_server_port_check(port_no)
        shadow = self.can_shadow_to_self(port_no)
        mqtt = int(self.status.get('mqtt'))
        claimed = int(self.status.get('claimed'))
        port = 0
        if self.status.get_field('port_check', 'result')=="True":
            port = 1
        error_code = (local_ip != "") + (internet << 1) +  (service<< 2) + (port << 3) + (mqtt << 4) + (shadow << 5) + (claimed << 6)
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
