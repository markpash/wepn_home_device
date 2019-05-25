from shadow import Shadow
from openvpn import OpenVPN
try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'

class Services:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.services = []
        self.services.append({'name':'openvpn', 'obj': OpenVPN() })
        self.services.append({'name':'shadow', 'obj': Shadow() })
        self.shadow = Shadow()
        #self.dante = Dante()
        return


    def start_all(self):
        for service in self.services:
            print("Starting "+service['name'])
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
            print("Stopping "+service['name'])
            service['obj'].stop()
        return

    def restart_all(self):
        self.openvpn.restart()
        self.shadow.restart()
        return

    def reload_all(self):
        self.openvpn.reload()
        self.shadow.reload()
        return

    def can_email(self, service_name):
        return

    def is_enanbled(self, service_name):
        return
    
    def add_user(self, certname, ip_address, password, port):
        for service in self.services:
            service['obj'].add_user(certname, ip_address, password, port)
        return

    def delete_user(self,certname):
        for service in self.services:
            service['obj'].delete_user(certname)
        return
    def get_add_email_text(self, certname, ip_address):
        txt = '\n'
        html = ''
        for service in self.services:
            ttxt, thtml = service['obj'].get_add_email_text(certname, ip_address)
            txt += ttxt + '\n'
            html += thtml + '<br />'
        return txt, html
