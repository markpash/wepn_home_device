
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
import ipw
import paho.mqtt.client as mqtt
from pad4pi import rpi_gpio
from oled import OLED as OLED

COL_PINS = [26] # BCM numbering
ROW_PINS = [19,13,6] # BCM numbering
KEYPAD = [
        ["1",],["2",],["3"],
]
CONFIG_FILE='/etc/pproxy/config.ini'


class Device():
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))

    def execute_cmd(self, cmd):
        try:
            args = shlex.split(cmd)
            process = subprocess.Popen(args)
            process.wait()
        except Exception as error_exception:
            print(args)
            print("Error happened in running command:" + cmd)
            print("Error details:\n"+str(error_exception))
            process.kill()

    def turn_off(self):
        cmd = "sudo /sbin/poweroff"
        self.execute_cmd(cmd)

    def restart_pproxy_service(self):
        cmd = "sudo /usr/local/sbin/restart-pproxy.sh"
        self.execute_cmd(cmd)

    def reboot(self):
        cmd = "sudo /sbin/reboot"
        self.execute_cmd(cmd)

    def update(self):
        cmd = "sudo /bin/sh /usr/local/sbin/update-pproxy.sh"
        self.execute_cmd(cmd)

    def update_all(self):
        cmd = "sudo /bin/sh /usr/local/sbin/update-system.sh"
        self.execute_cmd(cmd)

    def open_port(self, port, text):
        cmd="/usr/bin/upnpc -e '"+str(text)+"' -r "+str(port)+"  TCP > /dev/null 2>&1"
        print(cmd)
        self.execute_cmd(cmd)
        cmd="/usr/bin/upnpc -e '"+str(text)+"' -r "+str(port)+"  UDP > /dev/null 2>&1"
        print(cmd)
        self.execute_cmd(cmd)

    def close_port(self, port):
        cmd="/usr/bin/upnpc -d "+str(port)+"  TCP > /dev/null 2>&1"
        self.execute_cmd(cmd)
        cmd="/usr/bin/upnpc -d "+str(port)+"  UDP > /dev/null 2>&1"
        self.execute_cmd(cmd)
