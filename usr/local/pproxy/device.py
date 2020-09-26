
import json
from time import gmtime, strftime
import time
import ssl
import random
import logging.config
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
from wstatus import WStatus as WStatus

COL_PINS = [26] # BCM numbering
ROW_PINS = [19,13,6] # BCM numbering
KEYPAD = [
        ["1",],["2",],["3"],
]
CONFIG_FILE='/etc/pproxy/config.ini'
PORT_STATUS_FILE='/var/local/pproxy/port.ini'


class Device():
    def __init__(self, logger):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = WStatus(logger, PORT_STATUS_FILE)
        self.logger = logger
        self.correct_port_status_file()

    def correct_port_status_file(self):
        if not self.status.has_section('port-fwd'):
            self.status.add_section('port-fwd')
            self.status.set_field('port-fwd','fails','0')
            self.status.set_field('port-fwd','fails-max','3')
            self.status.set_field('port-fwd','skipping','0')
            self.status.set_field('port-fwd','skips','0')
            self.status.set_field('port-fwd','skips-max','20')
            self.status.save()

    def __del__(self):
        if self.status is not None:
            self.status.save()

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))

    def execute_cmd(self, cmd):
        try:
            failed = 0
            args = shlex.split(cmd)
            process = subprocess.Popen(args)
            sp = subprocess.Popen(args, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
            out, err = sp.communicate()
            process.wait()
            #if out:
            #    print ("standard output of subprocess:")
            #    print (out)
            if err:
                failed+=1
                #print ("standard error of subprocess:")
                #print (err)
                #print ("returncode of subprocess:")
                #print ("returncode="+str(sp.returncode))
            # Does not work: return sp.returncode
            return failed
        except Exception as error_exception:
            self.logger.error(args)
            self.logger.error("Error happened in running command:" + cmd)
            self.logger.error("Error details:\n"+str(error_exception))
            process.kill()
            return 99 



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
        skip = int(self.status.get_field('port-fwd','skipping'))
        skip_count = int(self.status.get_field('port-fwd','skips'))
        if skip:
            if skip_count < int(self.status.get_field('port-fwd','skips-max')):
                # skip, do nothing just increase cound
                skip_count += 1
                self.status.set_field('port-fwd','skips', str(skip_count))
            else:
                # skipped too much, try open port again in case it works
                self.status.set_field('port-fwd','skipping', '0')
                self.status.set_field('port-fwd','skips', '0')
        else:
            # no skipping, just try opening port normally with UPNP
            self.set_port_forward("open", port, text)
        self.logger.info("skipping? " + str(skip) + " count=" + str(skip_count))

    def close_port(self, port):
        skip = int(self.status.get_field('port-fwd','skipping'))
        skip_count = int(self.status.get_field('port-fwd','skips'))
        if skip:
            if skip_count < int(self.status.get_field('port-fwd','skips-max')):
                # skip, do nothing just increase cound
                skip_count += 1
                self.status.set_field('port-fwd','skips', str(skip_count))
            else:
                # skipped too much, try open port again in case it works
                self.status.set_field('port-fwd','skipping', '0')
                self.status.set_field('port-fwd','skips', '0')
            self.status.save()
        else:
            # no skipping, just try opening port normally with UPNP
            self.set_port_forward("close", port, "")
        self.logger.info("skipping?" + str(skip) + " count=" + str(skip_count))

    def set_port_forward(self, open_close, port, text):
        failed = 0
        upnpc_cmd = "/usr/bin/upnpc "
        if open_close == "open":
            upnpc_cmd += "-e '"+str(text)+"' -r "+str(port)
        if open_close == "close":
            upnpc_cmd += " -d "+str(port)
        cmd= upnpc_cmd + "  TCP"
        self.logger.debug(cmd)
        if self.execute_cmd(cmd) != 0:
            failed += 1
        cmd=upnpc_cmd + "  UDP"
        self.logger.debug(cmd)
        if self.execute_cmd(cmd) != 0:
            failed += 1
        # if we failed, check to see if max-fails has passed
        fails = int(self.status.get_field('port-fwd','fails'))
        if failed > 0:
            self.logger.error("PORT MAP FAILED")
            if fails >= int(self.status.get_field('port-fwd','fails-max')):
                # if passed limit, reset fail count, 
                self.status.set_field('port-fwd','fails', 0 )
                # indicate next one is going to be skip
                self.status.set_field('port-fwd','skipping', 1 )
            else:
                # failed, but has not passed the threshold
                fails += failed
                self.status.set_field('port-fwd','fails', str(fails))
