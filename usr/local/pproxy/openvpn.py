import shlex
import subprocess  # nosec: sanitized with shlex, go.we-pn.com/waiver-1
import sys as system
try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE = '/etc/pproxy/config.ini'
# setuid command runner
SRUN = "/usr/local/sbin/wepn-run"


class OpenVPN:
    def __init__(self, logger):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.logger = logger
        return

    def add_user(self, certname, ip_address, password, port, lang):
        if not self.is_enabled():
            return False
        cmd = '/bin/bash ./add_user_openvpn.sh ' + certname + ' ' + \
            ip_address + ' ' + str(self.config.get('openvpn', 'port'))
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
        return False

    def delete_user(self, certname):
        if not self.is_enabled():
            return
        cmd = '/bin/bash ./delete_user_openvpn.sh ' + certname
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
        return

    def start(self):
        if not self.is_enabled():
            return
        cmd = "0 0 1 "
        self.logger.debug(cmd)
        self.execute_setuid(cmd)
        return

    def stop(self):
        cmd = "0 0 0 "
        self.logger.debug(cmd)
        self.execute_setuid(cmd)
        return

    def restart(self):
        if not self.is_enabled():
            self.stop()
            return
        cmd = "0 0 2 "
        self.logger.debug(cmd)
        self.execute_setuid(cmd)
        return

    def reload(self):
        if not self.is_enabled():
            return
        cmd = "0 0 3 "
        self.logger.debug(cmd)
        self.execute_setuid(cmd)
        return

    def is_enabled(self):
        return (int(self.config.get('openvpn', 'enabled')) == 1)

    def can_email(self):
        return (int(self.config.get('openvpn', 'email')) == 1)

    def get_service_creds_summary(self, ip_address):
        return {}

    def get_usage_status_summary(self):
        return {}

    def get_usage_daily(self):
        return {}

    def get_add_email_text(self, certname, ip_address, lang, is_new_user=False):
        txt = ''
        html = ''
        subject = ''
        attachments = []
        if self.is_enabled() and self.can_email():
            txt = "To use OpenVPN (" + ip_address + \
                ") \n\n1. download the attached certificate, \n 2. install OpenVPN for Android Client." + \
                "\n 3. Import the certificate you downloaded in step 1."
            html = "To use OpenVPN (" + ip_address + \
                ")<ul><li>download the attached certificate, \n <li>install OpenVPN for Android Client." + \
                "<li> Import the certificate you downloaded in step 1.</ul>"
        return txt, html, attachments, subject

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

    def self_test(self):
        # not implemented for OpenVPN
        return True
