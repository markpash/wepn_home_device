import time
from getmac import get_mac_address
import netifaces
import atexit
import upnpclient as upnp
import requests
import re

try:
    from self.configparser import configparser
except ImportError:
    import configparser

import subprocess  # nosec shlex split used for sanitization go.we-pn.com/waiver-1
import shlex
from wstatus import WStatus as WStatus

COL_PINS = [26]  # BCM numbering
ROW_PINS = [19, 13, 6]  # BCM numbering
KEYPAD = [
    ["1", ], ["2", ], ["3"],
]
CONFIG_FILE = '/etc/pproxy/config.ini'
PORT_STATUS_FILE = '/var/local/pproxy/port.ini'


# setuid command runner
SRUN = "/usr/local/sbin/wepn-run"


class Device():
    def __init__(self, logger):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = WStatus(logger, PORT_STATUS_FILE)
        self.logger = logger
        self.correct_port_status_file()
        self.igds = []
        self.port_mappers = []
        self.igd_names = []
        self.iface = str(self.config.get('hw', 'iface'))
        self.repo_pkg_version = None
        self.reached_repo = False
        atexit.register(self.cleanup)

    def find_igds(self):
        devices = upnp.discover()
        self.logger.info("upnp devices:" + str(devices))
        # for i in devices:
        # print(dir(i))
        # print("https://www.google.com/search?q=%s+port+forward" % (urllib.parse.quote_plus(i.friendly_name)))
        for d in devices:
            if "InternetGatewayDevice" in d.device_type:
                self.igds.append(d)
                try:
                    self.ig_names.append(d.friendly_name)
                    print("Type: %s name: %s manufacturer:%s model:%s model:%s model:%s serial:%s" % (
                        d.device_type, d.friendly_name, d.manufacturer, d.model_description, d.model_name, d.model_number, d.serial_number))
                except:
                    # mainly if friendly name is not there
                    self.logger.debug(
                        "InternetGatewayDevice likely did not have proper UPnP fields")
                    pass
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
    # True result means IGD found
    def check_port_mapping_igd(self):
        self.find_igds()
        if self.igds:
            for d in self.igds:
                try:
                    self.logger.critical("IGD found: {" + str(d.model_name) +
                                         ", " + str(d.manufacturer) + ", " + str(d.location) + "}")
                    return self.check_igd_supports_portforward(d)
                except Exception as err:
                    self.logger.critical("IGD found, missing attributes")
                    print(err)
                    pass
        else:
            self.logger.error("No IGDs found")
            return False
        if not self.port_mappers:
            self.logger.error("No port mappers found")
            return False
        return True

    def correct_port_status_file(self):
        if not self.status.has_section('port-fwd'):
            self.status.add_section('port-fwd')
            self.status.set_field('port-fwd', 'fails', '0')
            self.status.set_field('port-fwd', 'fails-max', '3')
            self.status.set_field('port-fwd', 'skipping', '0')
            self.status.set_field('port-fwd', 'skips', '0')
            self.status.set_field('port-fwd', 'skips-max', '20')
            self.status.save()

    def cleanup(self):
        if self.status is not None:
            self.status.save()

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))

    def execute_setuid(self, cmd):
        return self.execute_cmd(SRUN + " " + cmd)

    def execute_cmd(self, cmd):
        out, err, failed, pid = self.execute_cmd_output(cmd)
        return failed

    def execute_cmd_output(self, cmd, detached=False):
        self.logger.debug(cmd)
        try:
            failed = 0
            args = shlex.split(cmd)
            out = ""
            err = ""
            if detached:
                sp = subprocess.Popen(args)  # nosec: sanitized above, go.we-pn.com/waiver-1
            else:
                sp = subprocess.Popen(args,  # nosec: sanitized above, go.we-pn.com/waiver-1
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)  # nosec: sanitized above, go.we-pn.com/waiver-1
                out, err = sp.communicate()
                sp.wait()
                if err:
                    time.sleep(3)
                    failed += 1
            return out, err, failed, sp
        except Exception as error_exception:
            self.logger.error(args)
            self.logger.error("Error happened in running command:" + cmd)
            self.logger.error("Error details:\n" + str(error_exception))
            sp.kill()
            return "", "running failed", 99, None

    def turn_off(self):
        cmd = "1 0"
        self.execute_setuid(cmd)

    def restart_pproxy_service(self):
        cmd = "1 1"
        self.execute_setuid(cmd)

    def reboot(self):
        cmd = "1 2"
        if self.config.has_option('hw', 'disable-reboot'):
            if self.config.getint('hw', 'disable-reboot') == 1:
                # used for hardware that reboot is not realistic
                cmd = "1 1"
        self.execute_setuid(cmd)

    def update(self):
        cmd = "1 3"
        self.execute_setuid(cmd)

    def update_all(self):
        cmd = "1 4"
        self.execute_setuid(cmd)

    def open_port(self, port, text, outside_port=None, timeout=500000):
        if outside_port is None:
            outside_port = port
        skip = int(self.status.get_field('port-fwd', 'skipping'))
        skip_count = int(self.status.get_field('port-fwd', 'skips'))
        if skip:
            if skip_count < int(self.status.get_field('port-fwd', 'skips-max')):
                # skip, do nothing just increase cound
                skip_count += 1
                self.status.set_field('port-fwd', 'skips', str(skip_count))
            else:
                # skipped too much, try open port again in case it works
                self.status.set_field('port-fwd', 'skipping', '0')
                self.status.set_field('port-fwd', 'skips', '0')
        else:
            # no skipping, just try opening port normally with UPNP
            self.set_port_forward("open", port, text, outside_port, timeout)
        self.logger.info("skipping? " + str(skip) +
                         " count=" + str(skip_count))

    def close_port(self, port):
        skip = int(self.status.get_field('port-fwd', 'skipping'))
        skip_count = int(self.status.get_field('port-fwd', 'skips'))
        if skip:
            if skip_count < int(self.status.get_field('port-fwd', 'skips-max')):
                # skip, do nothing just increase cound
                skip_count += 1
                self.status.set_field('port-fwd', 'skips', str(skip_count))
            else:
                # skipped too much, try open port again in case it works
                self.status.set_field('port-fwd', 'skipping', '0')
                self.status.set_field('port-fwd', 'skips', '0')
            self.status.save()
        else:
            # no skipping, just try opening port normally with UPNP
            self.set_port_forward("close", port, "")
        self.logger.info("skipping?" + str(skip) + " count=" + str(skip_count))

    def set_port_forward(self, open_close, port, text, outside_port=None, timeout=500000):
        if outside_port is None:
            outside_port = port
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
                        NewExternalPort=outside_port,
                        NewProtocol='TCP',
                        NewInternalPort=port,
                        NewInternalClient=str(local_ip),
                        NewEnabled='1',
                        NewPortMappingDescription=str(text),
                        NewLeaseDuration=timeout)
                    if ret:
                        self.logger.critical(
                            "return of port forward" + str(ret))

                    ret = port_mapper.AddPortMapping(
                        NewRemoteHost='',
                        NewExternalPort=outside_port,
                        NewProtocol='UDP',
                        NewInternalPort=port,
                        NewInternalClient=str(local_ip),
                        NewEnabled='1',
                        NewPortMappingDescription=str(text),
                        NewLeaseDuration=timeout)
                    if ret:
                        self.logger.critical(
                            "return of port forward" + str(ret))
                else:
                    ret = port_mapper.DeletePortMapping(
                        NewRemoteHost='',
                        NewExternalPort=port,
                        NewProtocol='TCP')
                    if ret:
                        self.logger.critical(
                            "return of port forward" + str(ret))
                    ret = port_mapper.DeletePortMapping(
                        NewRemoteHost='',
                        NewExternalPort=port,
                        NewProtocol='UDP')
                    if ret:
                        self.logger.critical(
                            "return of port forward" + str(ret))
            except Exception as err:
                self.logger.error("Port forward operation failed: " + str(err))
                failed += 1

        # if we failed, check to see if max-fails has passed
        fails = int(self.status.get_field('port-fwd', 'fails'))
        if failed > 0:
            self.logger.error("PORT MAP FAILED")
            if fails >= int(self.status.get_field('port-fwd', 'fails-max')):
                # if passed limit, reset fail count,
                self.status.set_field('port-fwd', 'fails', 0)
                # indicate next one is going to be skip
                self.status.set_field('port-fwd', 'skipping', 1)
            else:
                # failed, but has not passed the threshold
                fails += failed
                self.status.set_field('port-fwd', 'fails', str(fails))

    def get_local_ip(self):
        ip = "127.0.0.1"
        try:
            if netifaces.AF_INET in netifaces.ifaddresses(self.iface):
                ip = netifaces.ifaddresses(self.iface)[
                    netifaces.AF_INET][0]['addr']
            else:
                interfaces = netifaces.interfaces()
                for inf in interfaces:
                    if inf == "lo" or inf == "tun0":
                        continue
                    if netifaces.AF_INET in netifaces.ifaddresses(inf):
                        ip = netifaces.ifaddresses(inf)[
                            netifaces.AF_INET][0]['addr']
            return ip
        except Exception as error_exception:
            self.logger.error("Error happened in getting my IP")
            self.logger.error("Error details:\n" + str(error_exception))
            return '127.0.0.1'

    def get_local_mac(self):
        try:
            mac = netifaces.ifaddresses(
                self.iface)[netifaces.AF_LINK][0]['addr']
        except KeyError:
            pass
            mac = ""
        return mac

    def get_default_gw_ip(self):
        try:
            gws = netifaces.gateways()
            return gws['default'][netifaces.AF_INET][0]
        except Exception as error_exception:
            self.logger.error("Error happened in getting gateway IP")
            self.logger.error("Error details:\n" + str(error_exception))
            return '127.0.0.1'

    def get_default_gw_mac(self):
        gw_ip = self.get_default_gw_ip()
        try:
            gw_mac = get_mac_address(ip=gw_ip)
            return gw_mac
        except Exception as error_exception:
            self.logger.error("Error happened in getting gateway IP")
            self.logger.error("Error details:\n" + str(error_exception))
            return ['127.0.0.1']

    def get_default_gw_vendor(self):
        return self.get_default_gw_mac()[:8]

    def update_dns(self, ip_address):
        if not self.config.has_section("dyndns"):
            return
        if not self.config.getboolean('dyndns', 'enabled'):
            return
        # NOIP code from https://github.com/quleuber/no-ip-updater/blob/master/no_ip_updater/noip.py
        messages = {
            "good": "[SUCCESS] Host updated sucsessfully.",
            "nochg": "[SUCCESS] No update needed to host.",
            "nohost": "[ERROR] Host doesn't exist.",
            "badauth": "[ERROR] Username or password is invalid.",
            "badagent": "[ERROR] Client disabled. Client should exit and not perform any more updates without user intervention.",  # noqa: B950
            "!donator": "[ERROR] An update request was sent including a feature that is not available to that particular user such as offline options.",  # noqa: B950
            "abuse": "[ERROR] Username is blocked due to abuse.",
            "911": "[ERROR] A fatal error on our side such as a database outage. Retry the update no sooner than 30 minutes"  # noqa: B950
        }
        r = requests.get(self.config.get('dyndns', 'url').format(
            self.config.get('dyndns', 'username'),
            self.config.get('dyndns', 'password'),
            self.config.get('dyndns', 'hostname'), ip_address))
        if r.status_code != requests.codes.ok:
            self.logger.debug(r.content)
            for key in messages.keys():
                message = messages[key]
                if r.find(key.encode('utf-8')) == 0:
                    self.logger.error(message)

    def wait_for_internet(self, retries=100, timeout=10):
        tries = 0
        self.reached_repo = False
        while tries < retries:
            try:
                if self.get_repo_package_version() is not None:
                    self.reached_repo = True
                    return True
                else:
                    tries += 1
                    time.sleep(timeout)
            except Exception:
                self.logger.exception("Exception met")
                tries += 1
                time.sleep(timeout)
        return False

    def get_installed_package_version(self):
        version = None
        pkg_name = "pproxy-rpi"
        result = self.execute_cmd_output("dpkg -l " + pkg_name)
        r = str(result[0]).split("\\n")
        for i in r:
            if pkg_name in i:
                res = re.findall(".*" + pkg_name + r"\s+((\d+)\.(\d+)\.(\d+))\S*", i)
                if len(res) > 0 and len(res[0]) > 0:
                    version = res[0][0]
                    return version

    def get_repo_package_version(self):
        self.repo_pkg_version = None
        dist = "bullseye"
        url = "https://repo.we-pn.com/debian/dists/" + dist + "/main/binary-armhf/Packages"
        resp = requests.get(url)
        res = re.findall(r"Version: ((\d+)\.(\d+)\.(\d+)).*", resp.text)
        if len(res) > 0 and len(res[0]) > 0:
            self.repo_pkg_version = res[0][0]
            return self.repo_pkg_version

    def needs_package_update(self):
        needs = True
        current = self.get_installed_package_version()
        if self.wait_for_internet(10, 10):
            # only gets here is internet is connected
            # and could get the repo version
            # repo package version is checked there
            if self.repo_pkg_version is not None and current == self.repo_pkg_version:
                needs = False
        return needs

    def software_update_from_git(self):
        # first, the git pull in /var/local/pproxy/git/
        cmd_normal = "/bin/bash /usr/local/pproxy/setup/sync.sh"
        self.execute_cmd_output(cmd_normal, True)
        # part that should run as root:
        # copies system files, changes permissions, ...
        cmd_sudo = SRUN + " 1 5"
        self.execute_cmd_output(cmd_sudo, True)  # nosec static input (go.we-pn.com/waiver-1)
