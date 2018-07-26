import shlex
import subprocess
from subprocess import call
try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'
class OpenVPN:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        return


    def add_user(self, certname, ip_address, password, port):
        cmd = '/bin/sh ./add_user.sh '+ certname + ' '+ ip_address + ' ' + str(self.config.get('openvpn', 'port'))
        print(cmd)
        self.execute_cmd(cmd)
        return

    def delete_user(self, certname):
        cmd = '/bin/sh ./delete_user.sh '+ certname
        print(cmd)
        self.execute_cmd(cmd)
        return

    def start(self):
        cmd = "sudo /etc/init.d/openvpn start"
        print(cmd)
        self.execute_cmd(cmd)
        return


    def stop(self):
        cmd = "sudo /etc/init.d/openvpn stop"
        print(cmd)
        self.execute_cmd(cmd)
        return

    def restart(self):
        cmd = "sudo /etc/init.d/openvpn restart"
        print(cmd)
        self.execute_cmd(cmd)
        return

    def reload(self):
        cmd = "sudo /etc/init.d/openvpn reload"
        print(cmd)
        self.execute_cmd(cmd)
        return 

    def is_enabled(self):
        return (int(self.config.get('openvpn','enabled')) is 1 ) 

    def can_email(self):
        return (int(self.config.get('openvpn','email')) is 1)

    def get_add_email_text(self, certname, ip_address):
        txt = ''
        html = ''
        if self.is_enabled() and self.can_email() :
            txt  = "To use OpenVPN ("+ip_address+") \n\n1. download the attached certificate, \n 2.install OpenVPN for Android Client. \n 3. Import the certificate you downloaded in step 1."
            html  = "To use OpenVPN ("+ip_address+") \n\n1. download the attached certificate, \n 2.install OpenVPN for Android Client. \n 3. Import the certificate you downloaded in step 1."
        return txt, html
                

    def get_removal_email_text(self, certname, ip_address):
        txt = ''
        html = ''
        if self.config.get('openvpn','enabled') is 1 and self.config.get('openvpn','email') is 1:
            txt  = "Access to VPN server IP address " +  ip_address + " is revoked.",
            html = "Access to VPN server IP address " +  ip_address + " is revoked.",

        return txt, html

    def execute_cmd(self, cmd):
        try:
            args = shlex.split(cmd)
            process = subprocess.Popen(args)
            process.wait()
        except Exception as error_exception:
            print(args)	
            print("Error happened in running command:" + cmd)
            print("Error details:\n"+str(error_exception))
            system.exit()



