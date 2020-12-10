#!/usr/bin/python
import json
import random
import requests
import socket
import netifaces as ni
import platform
import os
import sys
import logging.config

from ipw import IPW
ipw = IPW()

from oled import OLED as OLED
from diag import WPDiag
from shadow import Shadow

CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'
try:
    from self.configparser import ConfigParser
except ImportError:
    import configparser
from wstatus import WStatus
from services import Services

class HeartBeat:
    def __init__(self, logger):
        # instantiate
        self.mqtt_connected = 0
        self.logger = logger
        self.mqtt_reason = 0
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = WStatus(logger)
        self.diag = WPDiag(logger)
        self.services = Services(logger)
        # This one is displayed on screen for call verification
        self.pin = random.SystemRandom().randint(1111111111, 9999999999)
        # This one is used for API access
        self.local_token = random.SystemRandom().randint(1111111111, 9999999999)
        # Print these to screen for bring-your-own device users without a screen
        self.logger.debug("PIN="+str(self.pin))
        self.logger.debug("Local token="+str(self.local_token))
    

    def is_connected(self):
        try:
            # connect to the host -- tells us if the host is actually
            # reachable
            socket.create_connection(("www.google.com", 80))
            return True
        except OSError:
            pass
            return False

    def set_mqtt_state(self,is_connected, reason):
       self.mqtt_connected = is_connected
       self.mqtt_reason = reason
       pass


    #send heartbeat. if led_print==1, update LED
    def send_heartbeat(self, led_print=1):
        headers = {"Content-Type": "application/json"}
        external_ip = str(ipw.myip())
        ni.ifaddresses(self.config.get('hw','iface'))
        local_ip = ni.ifaddresses(self.config.get('hw','iface'))[ni.AF_INET][0]['addr']
        test_port=int(self.config.get('openvpn','port')) + 1
        if int(self.config.get('shadow','enabled'))==1:
            shadow = Shadow(self.logger)
            test_port=int( shadow.get_max_port() ) + 2
        # this line can update the status file contents
        diag_code = self.diag.get_error_code(test_port)
        self.status.reload()
        status = int(self.status.get('state'))
        access_creds = self.services.get_service_creds_summary(external_ip)
        usage_status = self.services.get_usage_status_summary()
        self.logger.debug(usage_status)
        data = {
            "serial_number": self.config.get('django', 'serial_number'),
            "ip_address": external_ip,
            "status": str(status),
            "pin": str(self.pin),
            "local_token": str(self.local_token),
            "local_ip_address" : str(local_ip),
            "device_key":self.config.get('django', 'device_key'),
            'port': self.config.get('openvpn', 'port'),
            "software_version": self.status.get('sw'),
            "diag_code": diag_code,
            "access_cred": access_creds,
            "usage_status": usage_status,
        }
        self.status.set('pin', str(self.pin))
        self.status.set('local_token', str(self.local_token))
        self.status.save()

        data_json = json.dumps(data)
        self.logger.debug("HB data to send: " +data_json)
        url = self.config.get('django', 'url')+"/api/device/heartbeat/"
        try:
            response = requests.get(url, data=data_json, headers=headers)
            self.logger.debug("Response to HB" + str(response.status_code))
        except requests.exceptions.RequestException as exception_error:
            self.logger.error("Error in sending heartbeat: \r\n\t" + str(exception_error))
        if (led_print):
            led = OLED()
            led.set_led_present(self.config.get('hw','led'))
            if (status == 2):
               icon = "O"
            else:
               icon = "!X"
            icon = led.get_status_icons(status, self.is_connected(), self.mqtt_connected)
            display_str = [(1, "PIN: ",0), (2, str(self.pin), 0), (3,icon,1)]
            led.display(display_str, 20)
