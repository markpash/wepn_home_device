import json
from time import gmtime, strftime
from collections import deque
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
import logging.config
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
LOG_CONFIG="/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)

ipw =IPW()

class OnBoard():
    def __init__(self, logger=None):
        self.client = None
        self.unclaimed = True
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        if logger is not None:
            self.logger=logger
        else:
            self.logger = logging.getLogger("onboarding")
        self.device = Device(self.logger)
        self.mqtt_connected = 0
        self.mqtt_reason = 0
        self.factory = rpi_gpio.KeypadFactory()
        self.rand_key = None
        return


    def generate_rand_key(self):
        choose_from = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        self.rand_key = ''.join(random.SystemRandom().choice(choose_from) for _ in range(10))
        self.rand_key = self.rand_key + str(self.checksum(str(self.rand_key)))

    # this is used for checking previous keys used
    def set_rand_key(self, key):
        self.rand_key = key
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
        if not self.status.has_section('previous_keys'):
            self.status.add_section('previous_keys')
        saved_keys = deque([value for key, value in self.status.items('previous_keys')])
        self.logger.debug(saved_keys)
        # remove the oldest key
        try:
            # making the list longer was not 
            if saved_keys and (len(saved_keys) == 5):
                saved_keys.popleft()
        except Exception as e:
            self.logger.error("exception: " + str(e))
        # append the new key to the end
        saved_keys.append(self.rand_key)
        i = 0
        for key in saved_keys:
            self.status.set('previous_keys','key'+str(i), str(key))
            self.logger.debug("i=" + str(i)+ " key = "+str(key))
            i += 1
        self.status.set('status', 'temporary_key', self.rand_key)
        with open(STATUS_FILE, 'w') as statusfile:
            self.status.write(statusfile)

    def save_state(self, new_state, led_print=1):
        self.status.set('status', 'state', new_state)
        self.status.set('status', 'sw', self.status.get('status','sw'))
        with open(STATUS_FILE, 'w') as statusfile:
            self.status.write(statusfile)
        self.logger.debug('heartbeat from save_state '+new_state)
        heart_beat = HeartBeat(self.logger)
        heart_beat.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
        heart_beat.send_heartbeat(led_print)

    def process_key(self, key):
        services = Services(self.logger)
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
            led = OLED(self.logger)
            diag = WPDiag(self.logger)
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
            heart_beat = HeartBeat(self.logger)
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

    def on_disconnect(self, client, userdata, reason_code):
        self.logger.debug(">>>MQTT disconnected")

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, result_code):
        self.logger.debug("Connected with result code "+str(result_code))
        if (result_code == 0):
             self.logger.critical("* setting device to claimed")
             #save the randomly generated devkey
             self.config.set('mqtt','password',self.rand_key)
             self.config.set('django','device_key',self.rand_key)
             self.status.set('status','claimed', '1')
             self.status.set('status', 'temporary_key', "CLAIMED")
             with open(CONFIG_FILE, 'w') as configfile:
                  self.config.write(configfile)
             with open(STATUS_FILE, 'w') as statusfile:
                  self.status.write(statusfile)
             self.client.disconnect()
             self.client.loop_stop()
             self.unclaimed = False
             device = Device(self.logger)
             device.restart_pproxy_service()

    def on_message(self, client, userdata, msg):
        self.logger.debug(">>>on_message: "+msg.topic+" "+str(msg.payload))

    def start(self, run_once = False):
        run_once_done = False
        self.logger.debug("run_once= " + str(run_once))
        if not run_once:
            self.generate_rand_key()
            self.save_temp_key()
        oled = OLED()
        oled.set_led_present(self.config.get('hw','led'))
        oled.show_logo()
        #icons, if needed to add later: (1, chr(110)+ chr(43)+chr(75) , 1), 
        display_str = [(1, "Device Key:", 0), (2,'',0), (3, str(self.rand_key), 0),]
        oled.display(display_str, 18)
        self.client = mqtt.Client(self.config.get('mqtt', 'username'), clean_session=True)
        # TODO: to log this effectively for error logs,
        # instead of actual key save a hash of it to the log file. This way WEPN staff can
        # safely check if this is the correct key, without exposing the actual key
        self.logger.debug('Randomly generated device key: ' + self.rand_key)
        self.logger.debug('HW config: button='+str(int(self.config.get('hw','buttons'))) + '  LED='+
                self.config.get('hw','led'))
        if (int(self.config.get('hw','buttons'))):
            keypad = self.factory.create_keypad(keypad=KEYPAD, row_pins=ROW_PINS, col_pins=COL_PINS)
            keypad.registerKeyPressHandler(self.process_key)
        self.client.reconnect_delay_set(min_delay=1, max_delay=2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.tls_set("/etc/ssl/certs/DST_Root_CA_X3.pem", tls_version=ssl.PROTOCOL_TLSv1_2)
        rc= self.client.username_pw_set(username=self.config.get('mqtt', 'username'),
                               password=self.rand_key)
        self.logger.debug("mqtt host:" +str(self.config.get('mqtt','host')))
        while self.unclaimed and not run_once_done :
            try:
                  self.logger.debug("password for mqtt= "+ self.rand_key)
                  rc=self.client.connect(str(self.config.get('mqtt', 'host')),
                           int(self.config.get('mqtt', 'port')),
                           int(self.config.get('mqtt', 'timeout')))
                  self.client.loop_start()
                  time.sleep(int(self.config.get('mqtt', 'onboard-timeout')))
                  self.client.loop_stop()
            except Exception as error:
                self.logger.error("MQTT connect failed")
                display_str = [(1, chr(33)+'     '+chr(33),1), (2, "Network error,",0), (3, "check cable...", 0) ]
                oled.display(display_str, 15)
                if (int(self.config.get('hw','buttons'))):
                    keypad.cleanup()

                time.sleep(int(self.config.get('mqtt', 'onboard-timeout')))
                self.client.loop_stop()
                #raise
            finally:
                if run_once:
                    run_once_done = True

        if (int(self.config.get('hw','buttons'))):
            keypad.cleanup()
