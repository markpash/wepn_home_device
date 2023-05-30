
import os
import sys
import paho.mqtt.client as mqtt
import ssl
import time
import ssl
import random
import os
import re
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'  # noqa
sys.path.append(up_dir)  # noqa

try:
    from self.configparser import configparser
except ImportError:
    import configparser
CONFIG_FILE = '/etc/pproxy/config.ini'

HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'


class MQTTTest():
    def __init__(self):
        self.current_mqtt_password = ""
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.mqtt_connected = 0
        self.mqtt_reason = 0
        self.mqtt_supposed_to_connect = False
        self.number_runs = 0
        self.final_result = True

    def on_disconnect(self, client, userdata, reason_code):
        print(">>>MQTT disconnected*, reason = " + str(reason_code))

    def on_connect(self, client, userdata, flags, result_code):
        print(">>>Connected with result code: " + str(result_code))
        print("was this supposed to work? " + str(self.mqtt_supposed_to_connect))
        self.mqtt_reason = result_code
        if result_code == 0:
            self.mqtt_connected = True
        print("conneted = " + str(self.mqtt_connected) + " supposed = " + str(self.mqtt_supposed_to_connect) +
              " result = " + str(self.mqtt_connected and self.mqtt_supposed_to_connect))
        if self.mqtt_connected and self.mqtt_supposed_to_connect:
            print("[" + OKGREEN + "PASS" + ENDC + "] connected when supposed to connect\n")
        elif not self.mqtt_connected and self.mqtt_supposed_to_connect:
            print("[" + FAIL + "FAILED" + ENDC + "] could not connect with the correct password \n")
            self.final_result = False
        elif self.mqtt_connected and self.mqtt_supposed_to_connect == False:
            print("[" + FAIL + "FAILED" + ENDC + "]wrong password does not fail MQTT connect\n")
            self.final_result = False
        else:
            print("[" + OKGREEN + "PASS" + ENDC + "] wrong password results in not connecting\n")
        if self.number_runs == 0:
            print("Done with tests")
            self.client.loop_stop()
            sys.exit()

    def on_message(self, client, userdata, msg):
        print(">>>on_message: " + msg.topic + " " + str(msg.payload))

    def run_test(self):
        mqtt.Client.connected_flag = False  # create flag in class
        self.client = mqtt.Client(self.config.get('mqtt', 'username'), clean_session=True)
        print('HW config: button=' + str(int(self.config.get('hw', 'buttons'))) + '  LED=' +
              self.config.get('hw', 'lcd'))
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.tls_set("/etc/ssl/certs/ISRG_Root_X1.pem", tls_version=ssl.PROTOCOL_TLSv1_2)

        steps = [("forcewrongpass", False),
                 (self.config.get('mqtt', 'password'), True)]
        self.number_runs = len(steps)
        # self.client.enable_logger()
        print("-------------------------------------------------------")
        for (mqtt_password, self.mqtt_supposed_to_connect) in steps:
            self.error_happened = 0
            print("runs=" + str(self.number_runs))
            self.connect_rc = self.client.username_pw_set(username=self.config.get('mqtt', 'username'),
                                                          password=mqtt_password)
            print("username=" + self.config.get('mqtt', 'username'))
            print("password=" + mqtt_password + " supposed = " + str(self.mqtt_supposed_to_connect))
            print("mqtt host:" + str(self.config.get('mqtt', 'host')))
            try:
                self.connect_rc = self.client.connect(str(self.config.get('mqtt', 'host')),
                                                      int(self.config.get('mqtt', 'port')),
                                                      int(self.config.get('mqtt', 'timeout')))
                print("set client rc=" + str(self.connect_rc))
                print(self.connect_rc)
                self.client.loop_start()
                print("after connect(): connect rc=" + str(self.connect_rc) +
                      " connected_flag = " + str(self.client.connected_flag))
                time.sleep(1)
            except Exception as error:
                print("MQTT connect failed: " + str(error))
                self.client.error_happened = 1
                self.final_result = False
            finally:
                self.number_runs -= 1
                self.client.disconnect()
                print("-------------------------------------------------------")
                self.client.loop_stop()


current_test = MQTTTest()
current_test.run_test()
if current_test.final_result:
    print("[" + OKGREEN + "PASS" + ENDC + "] Final result is pass")
else:
    print("[" + FAIL + "FAIL" + ENDC + "] Final result is pass")
sys.exit(current_test.final_result != True)
