import json
from time import gmtime, strftime
import time
import ssl
import random
try:
    from self.configparser import configparser
except ImportError:
    import configparser

import smtplib
from os.path import basename
import subprocess
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from subprocess import call
import shlex
#import ipw
from ipw import IPW
import paho.mqtt.client as mqtt
from heartbeat import HeartBeat
from pad4pi import rpi_gpio
from oled import OLED as OLED
from diag import WPDiag
from services import Services
from device import Device
import string

COL_PINS = [26] # BCM numbering
ROW_PINS = [19,13,6] # BCM numbering
KEYPAD = [
        ["1",],["2",],["3"],
]
CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'

ipw =IPW()

class OnBoard():
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        self.device = Device()
        self.mqtt_connected = 0
        self.mqtt_reason = 0
        self.factory = rpi_gpio.KeypadFactory()
        choose_from = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        self.rand_key = ''.join(random.SystemRandom().choice(choose_from) for _ in range(10))
        self.rand_key = self.rand_key + str(self.checksum(str(self.rand_key)))
        return

    #simple checksum ONLY to prevent user mistakes in entering the key
    #no security protection intended
    def checksum(self, in_str):
        space = string.digits + string.ascii_uppercase
        chksum = 0
        for i in in_str:
            chksum = space.index(i) + chksum
        return space[chksum % len(space)]

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))


    def save_temp_key(self):
        # this is needed for the local webserver to read
        self.status.set('status', 'temporary_key', self.rand_key)
        with open(STATUS_FILE, 'w') as statusfile:
            self.status.write(statusfile)

    def save_state(self, new_state, led_print=1):
        self.status.set('status', 'state', new_state)
        self.status.set('status', 'sw', self.status.get('status','sw'))
        with open(STATUS_FILE, 'w') as statusfile:
            self.status.write(statusfile)
        print('heartbeat from save_state '+new_state)
        heart_beat = HeartBeat()
        heart_beat.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
        heart_beat.send_heartbeat(led_print)

    def process_key(self, key):
        services = Services()
        if (key == "1"):
            current_state=self.status.get('status','state')
            if (current_state == "2"):
                  new_state = "1"
                  services.stop()
            else:
                  new_state = "2"
                  services.start()
            self.save_state(str(new_state))
        #Run Diagnostics
        elif (key == "2"):
            led = OLED()
            diag = WPDiag()
            led.set_led_present(self.config.get('hw','led'))
            display_str = [(1, "Starting Diagnostics",0), (2, "please wait ...",0) ]
            led.display(display_str, 15)
            diag.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
            display_str = [(1, "Status Code",0), (2, str(diag.get_error_code( self.config.get('openvpn','port') )),0) ]
            led.display(display_str, 20)
            time.sleep(2)
            serial_number = self.config.get('django','serial_number')
            display_str = [(1, "Serial #",0), (2, serial_number,0), ]
            led.display(display_str, 19)
            time.sleep(5)
            heart_beat = HeartBeat()
            heart_beat.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
            heart_beat.send_heartbeat(0)
            display_str = [(1, "Device Key:", 0), (2,'',0), (3, str(self.rand_key), 0),]
            led.display(display_str, 18)

        #Power off   
        elif (key == "3"):
            services.stop()
            led = OLED()
            led.set_led_present(self.config.get('hw','led'))
            display_str = [(1, "Powering down",0), ]
            led.display(display_str, 15)
            time.sleep(2)
            self.save_state("0",0)
            led.show_logo()
            display_str = [(1, "",0), ]
            time.sleep(2)
            led.display(display_str, 20)
            self.device.turn_off()


    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, result_code):
        print("Connected with result code "+str(result_code))
        if (result_code == 0):
             #save the randomly generated devkey
             self.config.set('mqtt','password',self.rand_key)
             self.config.set('django','device_key',self.rand_key)
             self.status.set('status','claimed', '1')
             self.status.set('status', 'temporary_key', "CLAIMED")
             with open(CONFIG_FILE, 'w') as configfile:
                  self.config.write(configfile)
             with open(STATUS_FILE, 'w') as statusfile:
                  self.status.write(statusfile)
             client.disconnect()
             device = Device()
             device.restart_pproxy_service()


    def start(self):
        #generate randomdevkey
        oled = OLED()
        oled.set_led_present(self.config.get('hw','led'))
        oled.show_logo()
        self.save_temp_key()
        #icons, if needed to add later: (1, chr(110)+ chr(43)+chr(75) , 1), 
        display_str = [(1, "Device Key:", 0), (2,'',0), (3, str(self.rand_key), 0),]
        oled.display(display_str, 18)
        client = mqtt.Client(self.config.get('mqtt', 'username'), clean_session=False)
        print('Randomly generated device key: ' + self.rand_key)
        print('HW config: button='+str(int(self.config.get('hw','buttons'))) + '  LED='+
                self.config.get('hw','led'))
        if (int(self.config.get('hw','buttons'))):
            keypad = self.factory.create_keypad(keypad=KEYPAD, row_pins=ROW_PINS, col_pins=COL_PINS)
            keypad.registerKeyPressHandler(self.process_key)
        client.on_connect = self.on_connect
        client.tls_set("/etc/ssl/certs/DST_Root_CA_X3.pem", tls_version=ssl.PROTOCOL_TLSv1_2)
        rc= client.username_pw_set(username=self.config.get('mqtt', 'username'),
                               password=self.rand_key)
        print("mqtt host:" +str(self.config.get('mqtt','host')))
        while True:
            try:
                  time.sleep(int(self.config.get('mqtt', 'onboard-timeout')))
                  print("password for mqtt= "+ self.rand_key)
                  rc=client.connect(str(self.config.get('mqtt', 'host')),
                           int(self.config.get('mqtt', 'port')),
                           int(self.config.get('mqtt', 'onboard-timeout')))
            except Exception as error:
                print("MQTT connect failed")
                display_str = [(1, chr(33)+'     '+chr(33),1), (2, "Network error,",0), (3, "check cable...", 0) ]
                oled.display(display_str, 15)
                if (int(self.config.get('hw','buttons'))):
                    keypad.cleanup()

                time.sleep(int(self.config.get('mqtt', 'onboard-timeout')))
                #raise

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.
        client.loop_forever()
        if (int(self.config.get('hw','buttons'))):
            keypad.cleanup()
