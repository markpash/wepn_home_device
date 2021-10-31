import shlex
import subprocess  # nosec: sanitized with shlex, go.we-pn.com/waiver-1
import sys as system
try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE = '/etc/pproxy/config.ini'


class OpenVPN:
    def __init__(self, logger):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.logger = logger
        return

    def add_user(self, certname, ip_address, password, port, lang):
        cmd = '/bin/sh ./add_user.sh ' + certname + ' ' + \
            ip_address + ' ' + str(self.config.get('openvpn', 'port'))
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
        return False

    def delete_user(self, certname):
        cmd = '/bin/sh ./delete_user.sh ' + certname
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
        return

    def start(self):
        cmd = "sudo /etc/init.d/openvpn start"
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
        return

    def stop(self):
        cmd = "sudo /etc/init.d/openvpn stop"
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
        return

    def restart(self):
        cmd = "sudo /etc/init.d/openvpn restart"
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
        return

    def reload(self):
        cmd = "sudo /etc/init.d/openvpn reload"
        self.logger.debug(cmd)
        self.execute_cmd(cmd)
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

    def execute_cmd(self, cmd):
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
