
import os
import sys
import paho.mqtt.client as mqtt
import ssl
import time
import ssl
import random
import os
import re
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)

try:
    from self.configparser import configparser
except ImportError:
    import configparser
CONFIG_FILE='/etc/pproxy/config.ini'

class MQTTTest():
    def __init__(self):
        self.current_mqtt_password = "";
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.mqtt_connected = 0
        self.mqtt_reason = 0
        self.mqtt_supposed_to_connect  = False
        self.number_runs = 0

    def on_disconnect(self, client, userdata, reason_code):
        print(">>>MQTT disconnected")
    def on_connect(self, client, userdata, flags, result_code):
        print(">>>Connected with result code "+str(result_code))
        print("was this supposed to work"  +str(self.mqtt_supposed_to_connect))
        self.mqtt_reason = result_code
        if result_code == 0:
            self.mqtt_connected = True
        print("conneted = "+str(self.mqtt_connected)+" supposed = "+str(self.mqtt_supposed_to_connect) + " result = " + str(self.mqtt_connected and self.mqtt_supposed_to_connect))
        if self.mqtt_connected  and self.mqtt_supposed_to_connect:
            print("[PASS] connected when supposed to connect\n")
        elif not self.mqtt_connected and self.mqtt_supposed_to_connect:
            print("[FAILED] could not connect with the correct password \n")
        elif self.mqtt_connected and self.mqtt_supposed_to_connect== False:
            print("[1FAILED]: wrong password does not fail MQTT connect\n")
        else:
            print("[PASS] wrong password results in not connecting\n")
        if self.number_runs == 0:
            print("Done with tests")
            sys.exit()

    def on_message(self, client, userdata, msg):
        print(">>>on_message: "+msg.topic+" "+str(msg.payload))


    def run_test(self):
        mqtt.Client.connected_flag=False#create flag in class
        self.client = mqtt.Client(self.config.get('mqtt', 'username'), clean_session=True)
        print('HW config: button='+str(int(self.config.get('hw','buttons'))) + '  LED='+
            self.config.get('hw','lcd'))
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.tls_set("/etc/ssl/certs/DST_Root_CA_X3.pem", tls_version=ssl.PROTOCOL_TLSv1_2)
    
        steps = [   ("forcewrongpass" , False),
                    (self.config.get('mqtt', 'password'), True) ]
        self.number_runs = len(steps)
        #self.client.enable_logger()
        print("-------------------------------------------------------")
        for (mqtt_password, self.mqtt_supposed_to_connect) in steps:
            self.error_happened = 0
            self.connect_rc= self.client.username_pw_set(username=self.config.get('mqtt', 'username'),
                           password=mqtt_password)
            print("username="+self.config.get('mqtt','username'))
            print("password="+mqtt_password + " supposed = " + str(self.mqtt_supposed_to_connect))
            print("set client rc=" + str(self.connect_rc))
            print(self.connect_rc)
            print("mqtt host:" +str(self.config.get('mqtt','host')))
            try:
                self.connect_rc = self.client.connect(str(self.config.get('mqtt', 'host')),
                           int(self.config.get('mqtt', 'port')),
                           int(self.config.get('mqtt', 'timeout')))
                print("after connect(): connect rc=" + str(self.connect_rc) + " connected_flag = "+str(self.client.connected_flag))
            except Exception as error:
                print("MQTT connect failed")
                self.client.error_happened = 1
            finally:
                self.number_runs -= 1
                print("-------------------------------------------------------")
        self.client.loop_forever()


current_test = MQTTTest()
current_test.run_test()
