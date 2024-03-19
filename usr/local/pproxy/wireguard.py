import base64
import hashlib
import os
import re
import shlex
import subprocess  # nosec: sanitized with shlex, go.we-pn.com/waiver-1
import sys as system

from sanitize_filename import sanitize

from device import Device
from service import Service

CONFIG_FILE = '/etc/pproxy/config.ini'
USERS_DIR = "/var/local/pproxy/users/"
# setuid command runner
SRUN = "/usr/local/sbin/wepn-run"


class Wireguard(Service):
    def __init__(self, logger):
        Service.__init__(self, "wireguard", logger)
        return

    def santizie_service_filename(self, filename):
        s = sanitize(filename)
        s = re.sub(r'[^a-zA-Z0-9\.]', '', s)
        s = s.lower()
        return s

    def add_user(self, certname, ip_address, password, port, lang):
        try:
            if not os.path.isdir(USERS_DIR):
                os.mkdir(USERS_DIR)
            if self.is_user_registered(certname):
                old_ip, old_port = self.get_external_ip_port_in_conf(certname)
                if old_ip == ip_address and old_port == int(port):
                    # nothing has changed, do nothing
                    return False
            cmd = '/bin/bash ./add_user_wireguard.sh '
            cmd += self.santizie_service_filename(certname)
            cmd += " " + self.config.get("wireguard", "wireport")
            self.logger.debug(cmd)
            self.execute_cmd(cmd)
            return self.is_user_registered(certname)
        except Exception as e:
            self.logger.exception(e)
            return False

    def delete_user(self, certname):
        cmd = '/bin/bash ./delete_user_wireguard.sh '
        cmd += self.santizie_service_filename(certname)
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
        return

    def forward_all(self):
        port = self.config.get('wireguard', 'wireport')
        device = Device(self.logger)
        device.open_port(port, "Wireguard")
        return

    def start(self):
        cmd = "0 2 1"
        self.logger.debug(cmd)
        self.execute_setuid(cmd)
        return

    def stop(self):
        cmd = "0 2 0"
        self.logger.debug(cmd)
        self.execute_setuid(cmd)
        return

    def restart(self):
        cmd = "0 2 2"
        self.logger.debug(cmd)
        self.execute_setuid(cmd)
        return

    def reload(self):
        cmd = "0 2 3"
        self.logger.debug(cmd)
        self.execute_setuid(cmd)
        return

    def get_users_list(self):
        users = []
        try:
            if os.path.isdir(USERS_DIR):
                for d in os.listdir(USERS_DIR):
                    if (os.path.isdir(USERS_DIR + d) and os.path.isfile(USERS_DIR + d + "/wg.conf")):
                        users.append(d)
            else:
                os.mkdir(USERS_DIR)
        except Exception as e:
            self.logger.exception(e)
        return users

    def get_service_creds_summary(self, ip_address):
        creds = {}
        for d in self.get_users_list():
            creds[d] = hashlib.sha256(self.get_short_link_text(d, ip_address).encode()).hexdigest()[:10]
        return creds

    def get_usage_status_summary(self):
        usage = {}
        for d in self.get_users_list():
            usage[d] = -1
        return usage

    def get_usage_daily(self):
        return {}

    def get_external_ip_port_in_conf(self, certname):
        config_file_path = self.get_user_config_file_path(certname)
        if config_file_path is None:
            return None, None

        with open(config_file_path, "r") as f:
            contents = f.read()
            endpoint_match = re.search(r"^Endpoint\s*=\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)\s*$", contents, re.MULTILINE)
        if endpoint_match:
            return endpoint_match.group(1), int(endpoint_match.group(2))
        else:
            return None, None

    def is_user_registered(self, certname):
        try:
            cert_dir = self.santizie_service_filename(certname)
            self.logger.debug("checking for user: " + cert_dir)
            return os.path.exists(USERS_DIR + cert_dir + "/wg.conf")
        except Exception:
            self.logger.exception("Could not check if wireguard registered")
            return False

    def get_user_config_file_path(self, certname):
        if self.is_user_registered(certname):
            cert_dir = self.santizie_service_filename(certname)
            return USERS_DIR + cert_dir + "/wg.conf"
        else:
            return None

    def get_short_link_text(self, cname, ip_address):
        encoded_string = ""
        filename = self.get_user_config_file_path(cname)
        if filename is not None:
            with open(filename, "rb") as file:
                encoded_string = "wg://" + str(base64.b64encode(file.read()).decode('utf-8'))
        return encoded_string

    def get_add_email_text(self, certname, ip_address, lang, is_new_user=False):
        txt = ''
        html = ''
        subject = "Your New VPN Access Details"
        attachments = []
        if self.is_enabled() and self.can_email() and self.is_user_registered(certname):
            txt = "To use Wireguard (" + ip_address + \
                  "): \n\n1. Download the attached certificate, \n2. Install Wireguard Client." + \
                  "\n3. Import the certificate you downloaded in the first step."
            html = "To use Wireguard (" + ip_address + \
                ")<ul><li>Download the attached certificate, \n <li>Install Wireguard Client." + \
                "<li> Import the certificate you downloaded in the first step.</ul>"
            attachments.append(self.get_user_config_file_path(certname))
        return txt, html, attachments, subject

    def get_access_link(self, cname):
        if self.is_user_registered(cname):
            try:
                conf = open(self.get_user_config_file_path(cname), "r").read().encode("utf-8")
                conf64 = base64.urlsafe_b64encode(conf)
                digest = hashlib.sha256(conf64).hexdigest()[:10]
                return "{\"type\":\"wireguard\", \"link\":\"" + \
                    "wg://" + conf64.decode('utf-8') + \
                    "\", \"digest\": \"" + str(digest) + "\"}"
            except Exception:
                self.logger.exception("Wireguard link crashing")
        return None

    def get_removal_email_text(self, certname, ip_address):
        txt = ''
        html = ''
        subject = ''
        attachments = []
        if self.config.get('openvpn', 'enabled') == 1 and self.config.get('openvpn', 'email') == 1:
            txt = "Access to VPN server IP address " + ip_address + " is revoked.",
            html = "Access to VPN server IP address " + ip_address + " is revoked.",

        return txt, html, attachments, subject

    def execute_setuid(self, cmd):
        return self.execute_cmd(SRUN + " " + cmd)

    def execute_cmd(self, cmd):
        self.logger.debug(cmd)
        try:
            args = shlex.split(cmd)
            process = subprocess.Popen(args)  # nosec: sanitized above, go.we-pn.com/waiver-1
            process.wait()
        except Exception as error_exception:
            self.logger.error(args)
            self.logger.error("Error happened in running command:" + cmd)
            self.logger.error("Error details:\n" + str(error_exception))
            system.exit()

    def recover_missing_servers(self):
        return

    def self_test(self):
        # not implemented for Wireguard
        return True
