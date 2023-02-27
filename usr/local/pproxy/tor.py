from device import Device
import atexit

try:
    from self.configparser import configparser
except ImportError:
    import configparser

from ipw import IPW
ipw = IPW()

CONFIG_FILE = '/etc/pproxy/config.ini'


class Tor:
    def __init__(self, logger):
        self.config = configparser.ConfigParser()
        self.config.read('/etc/pproxy/config.ini')
        self.logger = logger

        atexit.register(self.cleanup)

    def cleanup(self):
        self.clear()

    def clear(self):
        pass

    def add_user(self, cname, ip_address, password, unused_port, lang):
        # really no action is needed for Tor
        return True

    def del_user_usage(self, certname):
        # really no action is needed for Tor
        pass

    def delete_user(self, cname):
        # really no action is needed for Tor
        return

    def start_all(self):
        return

    def stop_all(self):
        return

    def forward_all(self):
        port = self.config.get('tor', 'orport')
        device = Device(self.logger)
        device.open_port(port, "Tor")
        return

    def start(self):
        device = Device(self.logger)
        self.start_all()
        # add tor redirects for go.we-pn.com/wrong-location
        device.execute_setuid("1 8")
        device.execute_setuid("1 9")
        return

    def stop(self):
        self.stop_all()
        return

    def restart(self):
        self.stop_all()
        self.start_all()

    def reload(self):
        return

    def is_enabled(self):
        return (int(self.config.get('tor', 'enabled')) == 1)

    def can_email(self):
        return (int(self.config.get('tor', 'email')) == 1)

    def get_service_creds_summary(self, ip_address):
        return ""

    def get_usage_status_summary(self):
        return {}

    def get_usage_daily(self):
        return ""

    def get_add_email_text(self, cname, ip_address, lang, is_new_user=False):
        txt = ''
        html = ''
        manuals = []
        subject = ''
        if self.is_enabled() and self.can_email():
            manuals = []
            subject = "Your New Tor Bridge Access Details"
            txt = "You have been granted access to a private Tor bridge. "
            txt += "Install Onion Browser, and enter the below link as Tor Bridge address"
            html = "<h2>You have been granted access to a private Tor.</h2>"
            html += "Install Onion Browser, and enter the below link as Tor Bridge address"
            txt += ip_address + ":" + self.config.get('tor', 'orport')
            html += "<center><b>" + ip_address + ":" + \
                self.config.get('tor', 'orport') + "</b></center>"
        return txt, html, manuals, subject

    def get_removal_email_text(self, certname, ip_address, lang):
        txt = ''
        html = ''
        if self.is_enabled() and self.can_email():
            txt = "Access to Tor Bridge IP address " + ip_address + " is revoked.",
            html = "Access to Tor Bridge IP address " + ip_address + " is revoked.",
        return txt, html

    def recover_missing_servers(self):
        return

    def self_test(self):
        # TODO: some good testing is really needed here
        success = True
        return success
