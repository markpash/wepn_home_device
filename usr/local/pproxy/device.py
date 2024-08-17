import atexit
from json import JSONDecodeError
import json
import getopt
from getmac import get_mac_address
import netifaces
import os
from packaging import version
from packaging.version import Version
import platform
import psutil
from pystemd.systemd1 import Unit
import random
import requests
import re
import sys
import time
import upnpclient as upnp

try:
    from configparser import configparser
except ImportError:
    import configparser

import subprocess  # nosec shlex split used for sanitization go.we-pn.com/waiver-1
import shlex
from wstatus import WStatus as WStatus
from constants import SKIP_OTA_CHECK
from constants import DEFAULT_UPNP_TIMEOUT

GET_TIMEOUT = 10

COL_PINS = [26]  # BCM numbering
ROW_PINS = [19, 13, 6]  # BCM numbering
KEYPAD = [
    ["1", ], ["2", ], ["3"],
]
CONFIG_FILE = '/etc/pproxy/config.ini'
PORT_STATUS_FILE = '/var/local/pproxy/port.ini'
MAX_UPDATE_RETRIES = 5


# setuid command runner
SRUN = "/usr/local/sbin/wepn-run"

# Static function to add random delay to cron jobs


def random_cron_delay(args):
    max_delay = 5 * 60
    min_delay = 20
    use_delay = False
    try:
        opts, args = getopt.getopt(args, "d", ["random-delay"])
        for o, a in opts:
            if o in ("-d", "--random-delay"):
                use_delay = True
    except getopt.GetoptErrori:
        use_delay = False
    if use_delay:
        time.sleep(random.randrange(min_delay, max_delay, 1))  # nosec not security


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
                    self.igd_names.append(d.friendly_name)
                    print("Type: %s name: %s manufacturer:%s model:%s model:%s model:%s serial:%s" % (
                        d.device_type, d.friendly_name, d.manufacturer, d.model_description, d.model_name, d.model_number, d.serial_number))
                except Exception as e:
                    # mainly if friendly name is not there
                    self.logger.debug(
                        "InternetGatewayDevice likely did not have proper UPnP fields")
                    self.logger.exception("Error: " + str(e))
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
            if "Layer3Forwarding" in service.service_id or "L3Forwarding" in service.service_id:
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
                    self.logger.critical("IGD found, missing attributes: " + str(err))
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

    def open_port(self, port, text, outside_port=None, timeout=DEFAULT_UPNP_TIMEOUT):
        result = True
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
            result = self.set_port_forward("open", port, text, outside_port, timeout)
        self.logger.info("skipping? " + str(skip) +
                         " count=" + str(skip_count) + " result=" + str(result))
        return result

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

    def get_all_port_mappings(self):
        still_counting = True
        index = 0
        ports = []
        while still_counting:
            try:
                port_candidate = self.get_port_mapping_by_index(index)
                if port_candidate is not None:
                    if "NewPortMappingDescription" in port_candidate:
                        if "wepn" in port_candidate["NewPortMappingDescription"].lower():
                            # to avoid collecting unnecessary information,
                            # only collect port mappings we have opened ourselves
                            ports.append((port_candidate["NewExternalPort"],
                                          port_candidate["NewPortMappingDescription"]))
                    index += 1
                else:
                    still_counting = False
            except upnp.soap.SOAPError:
                # UPNP is weird, and instead of having statevars.PortMappingNumberOfEntries
                # we have to keep looking until we hit an error
                still_counting = False
                self.logger.debug("Number of port forwardings: " + str(index))
            except Exception as err:
                self.logger.exception(err)
                still_counting = False
        return ports, index

    def get_port_mapping_by_port(self, port_num, protocol="TCP"):
        if not self.igds:
            self.find_igds()
        if not self.igds:
            self.logger.error("No IGDs found in retry")
        if not self.port_mappers:
            self.logger.error("No port mappers found in retry")
        for port_mapper in self.port_mappers:
            try:
                for action in port_mapper.actions:
                    if "GetSpecificPortMappingEntry" in action.name:
                        return port_mapper.GetSpecificPortMappingEntry(
                            NewProtocol=protocol,
                            NewExternalPort=port_num,
                            NewRemoteHost='')
            except Exception as err:
                self.logger.exception("Port forward listing operation failed: " + str(err))
                raise err

    def get_port_mapping_by_index(self, index_num):
        if not self.igds:
            self.find_igds()
        if not self.igds:
            self.logger.error("No IGDs found in retry")
        if not self.port_mappers:
            self.logger.error("No port mappers found in retry")
        for port_mapper in self.port_mappers:
            for action in port_mapper.actions:
                if "GetGenericPortMappingEntry" in action.name:
                    return port_mapper.GetGenericPortMappingEntry(
                        NewPortMappingIndex=index_num,)

    def set_port_forward(self, open_close, port, text, outside_port=None, timeout=DEFAULT_UPNP_TIMEOUT):
        result = True
        if outside_port is None:
            outside_port = port
        failed = 0
        local_ip = self.get_local_ip()
        if "wepn" not in text.lower():
            text = "WEPN " + text
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
                result = False

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
        return result

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
            self.config.get('dyndns', 'hostname'), ip_address), timeout=GET_TIMEOUT)
        if r.status_code != requests.codes.ok:
            self.logger.debug(r.content)
            try:
                for key in messages.keys():
                    message = messages[key]
                    if r.find(key.encode('utf-8')) == 0:
                        self.logger.error(message)
            except AttributeError:
                print(r.content)
                self.logger.error(r.content)

    def wait_for_internet(self, retries=100, timeout=10):
        tries = 0
        self.reached_repo = False
        while tries < retries:
            try:
                if self.get_min_ota_version() is not None:
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
        pkg_version_ = None
        pkg_name = "pproxy-rpi"
        result = self.execute_cmd_output("dpkg -l " + pkg_name)
        r = str(result[0]).split("\\n")
        for i in r:
            if pkg_name in i:
                res = re.findall(".*" + pkg_name + r"\s+((\d+)\.(\d+)\.(\d+))\S*", i)
                if len(res) > 0 and len(res[0]) > 0:
                    pkg_version_ = res[0][0]
                    return pkg_version_
        return "0.0.0"

    def get_repo_package_version(self):
        self.repo_pkg_version = None
        dist = "bullseye"
        url = "https://repo.we-pn.com/debian/dists/" + dist + "/main/binary-armhf/Packages"
        try:
            resp = requests.get(url, timeout=GET_TIMEOUT)
            res = re.findall(r"Version: ((\d+)\.(\d+)\.(\d+)).*", resp.text)
            if len(res) > 0 and len(res[0]) > 0:
                self.repo_pkg_version = res[0][0]
                return self.repo_pkg_version
        except requests.exceptions.ConnectionError:
            self.logger.debug("Connection error in getting OTA version")
            return None
        except:
            return None

    def get_min_ota_version(self):
        self.repo_pkg_version = None
        url = "https://repo.we-pn.com/ota.json"
        try:
            resp = requests.get(url, timeout=GET_TIMEOUT)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    self.repo_pkg_version = data["min"]
                    return self.repo_pkg_version
                except JSONDecodeError:
                    self.logger.debug('Response could not be serialized')
                    return "0.0.0"
                except:
                    # malformed JSON, invalid HTTPS cert, ...
                    self.logger.debug("Some unknown error happend in getting OTA")
                    return None
        except requests.exceptions.ConnectionError:
            self.logger.debug("Connection error in getting OTA version")
            return None
        except:
            return None

    def needs_package_update(self, use_latest=False):
        if SKIP_OTA_CHECK:
            return False
        needs = True
        self.logger.debug("checking package to see if OTA is needed right now")
        current = self.get_installed_package_version()
        if self.wait_for_internet(10, 10):
            # only gets here is internet is connected
            # and could get the repo version
            # repo package version is checked there
            if use_latest:
                # this will rewrite repo_pkg_version to latest instead of ota.json
                self.get_repo_package_version()
            if self.repo_pkg_version is not None \
                    and version.parse(current) >= version.parse(self.repo_pkg_version):
                needs = False
            self.logger.debug("VERSION is " + str(current) +
                              " but needs " + str(self.repo_pkg_version))
            # this fixes the case that at the end of upgrade, service is restarted which
            # will trigger another upgrade
            # essentially: if update is still in progress, then don't trigger another update
            # problem: if we change the update process name, this will fail
            if self.is_process_running("update-pproxy"):
                self.logger.debug("update already running, not going to start another OTA")
                needs = False
            self.logger.debug("Needs OTA = " + str(needs))
        return needs

    def is_process_running(self, process_name):
        self.logger.debug("checking for process: " + process_name)
        for proc in psutil.process_iter():
            try:
                for c in proc.cmdline():
                    if process_name.lower() in c.lower():
                        self.logger.debug("Found process: " + str(proc.cmdline()))
                        return True
            # except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            except:
                self.logger.exception("Exception handling processes")
                return False
        return False

    def is_process_running_pid(self, pid):
        return psutil.pid_exists(pid)

    def get_process_cmd_by_pid(self, pid):
        self.logger.debug("checking for pid: " + str(pid))
        for proc in psutil.process_iter():
            try:
                if (proc.pid == pid):
                    return proc.cmdline()
            except:
                self.logger.exception("Exception in finding process cmd from pid")
                return [""]
        return [""]

    def software_update_blocking(self, lcd=None, leds=None, use_latest_sw=False):
        # if on a git build, use git
        # if on release branch, do via apt
        retries = 0
        update_was_needed = False
        try:
            while self.needs_package_update(use_latest_sw) and retries < MAX_UPDATE_RETRIES:
                self.logger.error("Entering OTA mode")
                update_was_needed = True
                retries += 1
                if leds is not None and lcd is not None:
                    leds.rainbow(20000, 2)
                    lcd.long_text("Do not unplug. Searching for updates.", "i", "red")
                    if self.get_local_ip() == "127.0.0.1":
                        # network has not local IP?
                        lcd.long_text(
                            "Is network cable connected? Searching for updates.", "M", "red")
                    elif not self.reached_repo:
                        lcd.long_text(
                            "Device cannot reach the internet. Are cables plugged in?", "X", "red")
                self.execute_setuid("1 3")  # run pproxy-update detached
                time.sleep(30)

            if leds is not None and lcd is not None:
                if update_was_needed:
                    if retries == MAX_UPDATE_RETRIES:
                        lcd.long_text("Could not finish update. Booting regardless.", "i", "orange")
                    else:
                        lcd.long_text("Software updated to " +
                                      self.get_installed_package_version(), "O", "green")
                        # let the service restart
                        time.sleep(15)
                    leds.blank()
        except:
            # this is meant to catch all unhandled exceptions
            # this function can block WEPN boot, so cannot keep failing
            return

    def software_update_from_git(self):
        # first, the git pull in /var/local/pproxy/git/
        cmd_normal = "/bin/bash /usr/local/pproxy/setup/sync.sh"
        self.execute_cmd_output(cmd_normal, True)
        # part that should run as root:
        # copies system files, changes permissions, ...
        cmd_sudo = SRUN + " 1 5"
        self.execute_cmd_output(cmd_sudo, True)  # nosec static input (go.we-pn.com/waiver-1)

    def get_serial_from_eeprom(self):
        try:
            with open("/proc/device-tree/hat/custom_0", "r") as f:
                data = json.load(f)
                return data["serial_number"]
        except (KeyError, TypeError, FileNotFoundError, json.JSONDecodeError):
            return None

    def config_matches_serial(self, config_path, serial_number):
        if serial_number is None:
            return True
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        try:
            s = cfg.get('django', 'serial_number')
            if s == serial_number:
                return True
            else:
                return False
        except:
            return False

    def generate_new_config(self):
        # umount all USB drives first
        cmd_sudo = SRUN + " 1 12"
        self.execute_cmd_output(cmd_sudo, True)
        time.sleep(5)
        try:
            # now mount USB drive
            cmd_sudo = SRUN + " 1 11"
            self.execute_cmd_output(cmd_sudo, True)  # nosec static input (go.we-pn.com/waiver-1)
            time.sleep(5)

            preset_config = "/mnt/wepn.ini"
            previous_config = "/mnt/etc/pproxy/config.ini"
            new_config_str = None
            # read serial number that is written on eeprom
            board_serial = self.get_serial_from_eeprom()
            # This allows us to force overriding the serial number match
            if os.path.isfile("/mnt/ignore-serial-match.txt"):
                board_serial = None

            # priority 1: SD card has wepn.ini in root folder and serial matches device
            if os.path.isfile(preset_config) and self.config_matches_serial(preset_config, board_serial):
                with open(preset_config) as f:
                    new_config_str = f.read()
            # priority 2: SD card is a previous WEPN SD card and serial matches device
            elif os.path.isfile(previous_config) and self.config_matches_serial(previous_config, board_serial):
                with open(previous_config) as f:
                    new_config_str = f.read()
            else:
                # use the setup file there to generate the config, get contents
                sys.path.append("/mnt/device_setup/")
                # write to the current config
                from setup_mod import create_config  # noqa: setup_mod is defined on the USB drive just mounted
                new_config_str = create_config()
            if new_config_str is not None:
                config_file = open("/etc/pproxy/config.ini", 'w')
                config_file.write(new_config_str)
                config_file.close()
            else:
                self.logger.error("new config str is empty")
        except Exception:
            self.logger.exception("Error generating new config file")
        finally:
            # umount USB drive
            cmd_sudo = SRUN + " 1 12"
            self.execute_cmd_output(cmd_sudo, True)

    def generate_ssh_host_keys(self):
        cmd_sudo = SRUN + " 1 13"
        self.execute_cmd_output(cmd_sudo, True)

    def set_sshd_service(self, enabled=True):
        common = SRUN + " 0 4 "
        if enabled:
            # enable service
            cmd_sudo = common + "4"
            self.execute_cmd_output(cmd_sudo, True)
            # restart it on too
            cmd_sudo = common + "2"
            self.execute_cmd_output(cmd_sudo, True)
        else:
            # disable service
            cmd_sudo = common + "5"
            self.execute_cmd_output(cmd_sudo, True)
            # turn it off too
            cmd_sudo = common + "0"
            self.execute_cmd_output(cmd_sudo, True)

    # This routine SSHs out to remote server, open a reverse
    # tunnel to the device. Helps bypass network issues.
    def set_remote_ssh_session(self, enabled=True):
        if enabled:
            server = "remote@relay.we-pn.com"
            key = "/var/local/pproxy/shared_remote_key.priv"
            port = 9000 + int(self.config.get('django', 'id'))
            cmd = "ssh -R *:" + str(port) + ":localhost:22 -i " + key + " " + server
            cmd += " -fTN -o StrictHostKeyChecking=accept-new"
            print(cmd)
            self.execute_cmd_output(cmd, True)
        else:
            for proc in psutil.process_iter():
                try:
                    if "ssh" in proc.name():
                        for c in proc.cmdline():
                            if c == "remote@relay.we-pn.com":
                                proc.kill()
                except psutil.ZombieProcess:
                    pass

    def is_remote_session_running(self):
        found = False
        for i in psutil.process_iter():
            if i.name() == "ssh":
                try:
                    for c in i.cmdline():
                        if c == "remote@relay.we-pn.com":
                            found = True
                except psutil.ZombieProcess:
                    pass
        return found

    def set_vnc_service(self, enabled=True):
        common = SRUN + "0 4 "
        if enabled:
            # disable service
            cmd_sudo = common + "5"
            self.execute_cmd_output(cmd_sudo, True)
            # turn it off too
            cmd_sudo = common + "0"
            self.execute_cmd_output(cmd_sudo, True)
        else:
            # disable service
            cmd_sudo = common + "4"
            self.execute_cmd_output(cmd_sudo, True)
            # turn it off too
            cmd_sudo = common + "2"
            self.execute_cmd_output(cmd_sudo, True)

    def is_service_active(self, service_name):
        unit = Unit(service_name)
        unit.load()
        if unit.Unit.ActiveState == b'active':
            return True
        else:
            return False

    def get_os_info(self):
        os_release = {}
        with open("/etc/os-release") as os_file:
            for line in os_file:
                name, var = line.partition("=")[::2]
                os_release[name.strip()] = str(var)
        return os_release

    def get_os_codename(self):
        os_info = self.get_os_info()
        return os_info["VERSION_CODENAME"]

    # kernel 6.6.x removed support for debugfs
    # which broke older GPIO interface
    # this return is OS is legacy model or updated
    def is_legacy_gpio(self):
        release = platform.release().split("-")[0]
        return Version(release) < Version("6.6.0")
