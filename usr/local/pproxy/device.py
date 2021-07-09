
import json
from time import gmtime, strftime
import time
import ssl
import random
from getmac import get_mac_address
import logging.config
import netifaces
import atexit
import upnpclient as upnp
import requests
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
import ipw
import paho.mqtt.client as mqtt
try:
    from pad4pi import rpi_gpio
except RuntimeError as err:
    print("Error in pad4pi: "+str(err))
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
        self.igds = []
        self.port_mappers = []
        self.iface = str(self.config.get('hw','iface'))
        atexit.register(self.cleanup)

    def find_igds(self):
        devices = upnp.discover()
        self.logger.info("upnp devices:" + str(devices))
        for d in devices:
            if "InternetGatewayDevice" in d.device_type:
               self.igds.append(d)
               # Here we find the actual service provider that can forward ports
               # the default name is different for different routers
               for service in d.services:
                   for action in service.actions:
                       if "AddPortMapping" in action.name:
                           self.port_mappers.append(service)

    def check_igd_supports_portforward(self, igd):
        l3forward_supported = False
        wanipconn_supported = False
        for service in igd.services:
            if "Layer3Forwardingg" in service.service_id:
                l3forward_supported = True
            if "WANIPConn" in service.service_id:
                wanipconn_supported = True
        if not l3forward_supported:
            self.logger.error("Error: could not find L3 forwarding")
        if not wanipconn_supported:
            self.logger.error("Error: could not find WANIPConn")
        return (l3forward_supported and wanipconn_supported)

    # this method is just used for checking upnp capabilities
    # primarily used at boot, to add to the error log
    def check_port_mapping_igd(self):
        self.find_igds()
        if self.igds:
            for d in self.igds:
               try:
                    self.logger.critical("IGD found: {" + str(d.model_name) +\
                            ", " + str(d.manufacturer)+ ", "+ str(d.location) + "}")
                    self.check_igd_supports_portforward(d)
               except Exception as err:
                    self.logger.critical("IGD found, missing attributes")
                    print(err)
                    pass
        else:
            self.logger.error("No IGDs found")
        if not self.port_mappers:
            self.logger.error("No port mappers found")


    def correct_port_status_file(self):
        if not self.status.has_section('port-fwd'):
            self.status.add_section('port-fwd')
            self.status.set_field('port-fwd','fails','0')
            self.status.set_field('port-fwd','fails-max','3')
            self.status.set_field('port-fwd','skipping','0')
            self.status.set_field('port-fwd','skips','0')
            self.status.set_field('port-fwd','skips-max','20')
            self.status.save()

    def cleanup(self):
        if self.status is not None:
            self.status.save()

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))

    def execute_cmd(self, cmd):
        out, err, failed, pid = self.execute_cmd_output(cmd)
        return failed

    def execute_cmd_output(self, cmd, detached=False):
        try:
            failed = 0
            args = shlex.split(cmd)
            out = ""
            err = ""
            if detached:
                sp = subprocess.Popen(args)
            else:
                sp = subprocess.Popen(args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                out, err = sp.communicate()
                sp.wait()
                if err:
                    time.sleep(3)
                    failed+=1
            return out, err, failed, sp
        except Exception as error_exception:
            self.logger.error(args)
            self.logger.error("Error happened in running command:" + cmd)
            self.logger.error("Error details:\n"+str(error_exception))
            sp.kill()
            return "","running failed", 99, None


    def turn_off(self):
        cmd = "sudo /sbin/poweroff"
        self.execute_cmd(cmd)

    def restart_pproxy_service(self):
        cmd = "sudo /usr/local/sbin/restart-pproxy.sh"
        self.execute_cmd(cmd)

    def reboot(self):
        cmd = "sudo /sbin/reboot"
        if self.config.has_option('hw','disable-reboot'):
            if self.config.getint('hw','disable-reboot') == 1:
                # used for hardware that reboot is not realistic
                cmd = "sudo /usr/local/sbin/restart-pproxy.sh"
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
        local_ip = self.get_local_ip()
        if not self.igds:
            self.find_igds()
        if not self.igds:
            self.logger.error("No IGDs found in retry")
        if not self.port_mappers:
            self.logger.error("No port mappers found in retry")
        for port_mapper in self.port_mappers:
            try:
                if open_close == "open":
                    ret = port_mapper.AddPortMapping(
                            NewRemoteHost='',
                            NewExternalPort=port,
                            NewProtocol='TCP',
                            NewInternalPort=port,
                            NewInternalClient=str(local_ip),
                            NewEnabled='1',
                            NewPortMappingDescription=str(text),
                            NewLeaseDuration=500000)
                    if ret:
                        self.logger.critical("return of port forward" + str(ret))

                    ret = port_mapper.AddPortMapping(
                            NewRemoteHost='',
                            NewExternalPort=port,
                            NewProtocol='UDP',
                            NewInternalPort=port,
                            NewInternalClient=str(local_ip),
                            NewEnabled='1',
                            NewPortMappingDescription=str(text),
                            NewLeaseDuration=500000)
                    if ret:
                        self.logger.critical("return of port forward" + str(ret))
                else:
                    ret = port_mapper.DeletePortMapping(
                            NewRemoteHost='',
                            NewExternalPort=port,
                            NewProtocol='TCP')
                    if ret:
                        self.logger.critical("return of port forward" + str(ret))
                    ret = port_mapper.DeletePortMapping(
                            NewRemoteHost='',
                            NewExternalPort=port,
                            NewProtocol='UDP')
                    if ret:
                        self.logger.critical("return of port forward" + str(ret))
            except Exception as err:
                self.logger.error("Port forward operation failed: "+str(err))
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

    def get_local_ip(self):
        try:
            ip = netifaces.ifaddresses(self.iface)[netifaces.AF_INET][0]['addr']
            return ip
        except Exception as error_exception:
            self.logger.error("Error happened in getting my IP")
            self.logger.error("Error details:\n"+str(error_exception))
            return '0.0.0.0'


    def get_local_mac(self):
       try:
          mac = netifaces.ifaddresses(self.iface)[netifaces.AF_LINK][0]['addr']
       except KeyError:
          pass
          mac= ""; 
       return mac

    def get_default_gw_ip(self):
        try:
            gws = netifaces.gateways()
            return gws['default'][netifaces.AF_INET][0]
        except Exception as error_exception:
            self.logger.error("Error happened in getting gateway IP")
            self.logger.error("Error details:\n"+str(error_exception))
            return '0.0.0.0'

    def get_default_gw_mac(self):
        gw_ip = self.get_default_gw_ip()
        try:
            gw_mac = get_mac_address(ip=gw_ip)
            return gw_mac
        except Exception as error_exception:
            self.logger.error("Error happened in getting gateway IP")
            self.logger.error("Error details:\n"+str(error_exception))
            return '0.0.0.0'
    def get_default_gw_vendor(self):
        return self.get_default_gw_mac()[:8]

    def update_dns(self, ip_address):
        if not self.config.has_section("dyndns"):
            return
        if not self.config.getboolean('dyndns','enabled'):
            return
        # NOIP code from https://github.com/quleuber/no-ip-updater/blob/master/no_ip_updater/noip.py
        messages = {
                "good":    "[SUCCESS] Host updated sucsessfully.",
                "nochg":   "[SUCCESS] No update needed to host.",
                "nohost":  "[ERROR] Host doesn't exist.",
                "badauth": "[ERROR] Username or password is invalid.",
                "badagent":"[ERROR] Client disabled. Client should exit and not perform any more updates without user intervention.",
                "!donator":"[ERROR] An update request was sent including a feature that is not available to that particular user such as offline options.",
                "abuse":   "[ERROR] Username is blocked due to abuse.",
                "911":     "[ERROR] A fatal error on our side such as a database outage. Retry the update no sooner than 30 minutes"
                }
        r = requests.get(self.config.get('dyndns','url').format(
            self.config.get('dyndns','username'),
            self.config.get('dyndns','password'),
            self.config.get('dyndns','hostname'), ip_address))
        if r.status_code != requests.codes.ok:
            self.logger.debug(r.content)
            for key in messages.keys():
                message = messages[key]
                if response.find(key.encode('utf-8')) == 0:
                    self.logger.error(message)

