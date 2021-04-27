import logging.config
from shadow import Shadow
from openvpn import OpenVPN
try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'

class Services:
    def __init__(self, logger):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.services = []
        self.services.append({'name':'openvpn', 'obj': OpenVPN(logger) })
        self.services.append({'name':'shadow', 'obj': Shadow(logger) })
        self.logger = logger
        #self.dante = Dante()
        return


    def start_all(self):
        for service in self.services:
            self.logger.info("Starting "+service['name'])
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
            self.logger.info("Stopping "+service['name'])
            service['obj'].stop()
        return

    def restart_all(self):
        for service in self.services:
            self.logger.info("Restarting "+service['name'])
            service['obj'].restart()
        return

    def reload_all(self):
        for service in self.services:
            self.logger.info("Reloading "+service['name'])
            service['obj'].reload()
        return

    def can_email(self, service_name):
        return

    def is_enanbled(self, service_name):
        return
    
    def add_user(self, certname, ip_address, suggested_password, suggested_port, lang='en'):
        # Note: services may use another port (based on used ports) or password 
        # (if user already exists.
        for service in self.services:
            service['obj'].add_user(certname, ip_address, suggested_password,
                                    suggested_port, lang)
        return

    def delete_user(self,certname):
        for service in self.services:
            service['obj'].delete_user(certname)
        return
    def get_add_email_text(self, certname, ip_address, lang):
        txt = '\n'
        html = ''
        for service in self.services:
            ttxt, thtml = service['obj'].get_add_email_text(certname, ip_address, lang)
            txt += ttxt + '\n'
            html += thtml + '<br />'
        return txt, html

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
            res=service['obj'].get_usage_status_summary()
            if bool(res):   # check if there are any friends
                    self.logger.debug(res)
                    usage.update(res)
        return usage

    def get_usage_daily(self):
        usage = {}
        for service in self.services:
            res=service['obj'].get_usage_daily()
            print("res is = " + str(res))
            if bool(res):   # check if there are any friends
                    self.logger.debug(res)
                    for server in res:
                        if server not in usage:
                            # first service that has this server (certname)
                            usage[server] = res[server]
                        else:
                            #multiple services have the same server
                            user[server].update(res[server])
        print("usage is = " + str(usage))
        return usage


