import re
from sanitize_filename import sanitize

from shadow import Shadow
from openvpn import OpenVPN
from wireguard import Wireguard
from tor import Tor

try:
    from configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE = '/etc/pproxy/config.ini'


class Services:
    def __init__(self, logger):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.services = []
        self.services.append({'name': 'openvpn', 'obj': OpenVPN(logger)})
        self.services.append({'name': 'shadowsocks', 'obj': Shadow(logger)})
        self.services.append({'name': 'wireguard', 'obj': Wireguard(logger)})
        self.services.append({'name': 'tor', 'obj': Tor(logger)})
        self.logger = logger
        return

    def santizie_service_filename(self, filename):
        s = sanitize(filename)
        s = re.sub(r'[^a-zA-Z0-9]', '', s)
        s = s.lower()
        return s

    def start_all(self):
        for service in self.services:
            self.logger.info("Starting " + service['name'])
            service['obj'].start()
        return

    def stop(self):
        self.stop_all()
        return

    def start(self):
        self.start_all()
        return

    def stop_all(self):
        for service in self.services:
            self.logger.info("Stopping " + service['name'])
            service['obj'].stop()
        return

    def restart_all(self):
        for service in self.services:
            self.logger.info("Restarting " + service['name'])
            service['obj'].restart()
        return

    def reload_all(self):
        for service in self.services:
            self.logger.info("Reloading " + service['name'])
            service['obj'].reload()
        return

    def can_email(self, service_name):
        return

    def is_enanbled(self, service_name):
        return

    def add_user(self, certname, ip_address, suggested_password, suggested_port, tunnel, lang='en'):
        # Note: services may use another port (based on used ports) or password
        # (if user already exists.
        is_new_user = False
        for service in self.services:
            if tunnel == "all" or tunnel == service["name"]:
                newly_added = service['obj'].add_user(certname, ip_address, suggested_password,
                                                      suggested_port, lang)
                is_new_user |= newly_added
        return is_new_user

    def delete_user(self, certname, tunnel="all"):
        for service in self.services:
            if tunnel == "all" or tunnel == service["name"]:
                service['obj'].delete_user(certname)
        return

    def get_short_link_text(self, cname, ip_address, tunnel="all"):
        links = ""
        for service in self.services:
            if tunnel == "all" or tunnel == service["name"]:
                links = links + str(service['obj'].get_short_link_text(cname, ip_address))
        return links

    def get_add_email_text(self, certname, ip_address, lang, tunnel="all", is_new_user=False):
        txt = '\n'
        html = ''
        attachments = []
        subject = ''
        for service in self.services:
            if tunnel == "all" or tunnel == service["name"]:
                ttxt, thtml, tattachments, tsubject = service['obj'].get_add_email_text(
                    certname, ip_address, lang, is_new_user)
                txt += ttxt + '\n'
                html += thtml + '<br />'
                attachments.extend(tattachments)
                # this would assume only one service has a subject
                subject += tsubject
        return txt, html, attachments, subject

    def get_service_creds_summary(self, ip_address):
        creds = {}
        for service in self.services:
            res = service['obj'].get_service_creds_summary(ip_address)
            self.logger.debug(res)
            if bool(res):   # check if there are any friends
                creds.update(res)
        return creds

    def get_usage_status_summary(self):
        usage = {}
        for service in self.services:
            res = service['obj'].get_usage_status_summary()
            if bool(res):   # check if there are any friends
                self.logger.debug(res)
                usage.update(res)
        return usage

    def get_usage_daily(self):
        usage = {}
        for service in self.services:
            res = service['obj'].get_usage_daily()
            if bool(res):   # check if there are any friends
                self.logger.debug(res)
                for server in res:
                    if server not in usage:
                        # first service that has this server (certname)
                        usage[server] = res[server]
                    else:
                        # multiple services have the same server
                        usage[server].update(res[server])
        return usage

    def get_access_link(self, cname):
        for service in self.services:
            link = service['obj'].get_access_link(cname)
            if link is not None:
                return link
        return "{\"type\":\"empty\", \"link\":\"\", \"digest\": \"\" }"

    def recover_missing_servers(self):
        for service in self.services:
            service['obj'].recover_missing_servers()

    def self_test(self):
        result = True
        for service in self.services:
            result &= service['obj'].self_test()
        return result

    def configure(self, service_name, config_data):
        for service in self.services:
            if service['name'] == service_name:
                service['obj'].configure(config_data)
