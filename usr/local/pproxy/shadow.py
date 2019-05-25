
import json
from time import gmtime, strftime
import time
import ssl
import socket 
import struct
import os
import dataset
import sqlite3 as sqli
import base64
import device

try:
    from self.configparser import configparser
except ImportError:
    import configparser

from os.path import basename
import subprocess
import shlex
from ipw import IPW
ipw= IPW()
from diag import WPDiag
import tempfile
from device import Device

CONFIG_FILE='/etc/pproxy/config.ini'

class Shadow:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('/etc/pproxy/config.ini')
        fd, self.socket_path = tempfile.mkstemp()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(self.socket_path)
        except OSError:
            self.clear()
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(self.socket_path)
        self.sock.connect(self.config.get('shadow','server-socket'))


    def __del__(self):
        self.clear()

    def clear(self):
        if os.path.isfile(self.socket_path):
            self.sock.shutdown(0)
            self.sock.close()
            os.remove(self.socket_path)

    def add_user(self, cname, ip_address, password, port):
        local_db = dataset.connect('sqlite:///'+self.config.get('shadow', 'db-path'))
        #get max of assigned ports, new port is 1+ that. 
        #if no entry in DB, copy from config default port start
        servers = local_db['servers']
        server = servers.find_one(certname = cname)
        #if already exists, use same port
        #else assign a new port, 1+laargest existing
        if server is None:
            try:
                results = local_db.query('select max(server_port) from servers')
                row = list(results)[0]
                max_port = row['max(server_port)'] 
            except:
                max_port = None
            if max_port is None:
                max_port = int(self.config.get('shadow','start-port'))
            print("New port assigned is " + str(max_port+1) + " was " + str(port))
            port=max_port + 1 

        cmd = 'add : {"server_port": '+str(port)+' , "password" : "'+str(password)+'" } '
        self.sock.send(str.encode(cmd))
        print(self.sock.recv(1056))
        #open the port for this now
        print('enabling port forwarding to port ' + str(port))
        device = Device()
        device.open_port(port, 'ShadowSocks '+cname)

        #add certname, port, password to a json list to ues at delete/boot
        servers.upsert({'certname':cname, 'server_port':port, 'password':password},['certname'])
        #retrun success or failure if file doesn't exist
        for a in local_db['servers']:
            print(a)
        return


    def delete_user(self, cname):
        #stop the service for that cert
        local_db = dataset.connect('sqlite:///'+self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        server = servers.find_one(certname = cname)
        if server is not None:

            port = server['server_port']
            print (server['server_port'])
            cmd = 'remove : {"server_port": '+str(server['server_port'])+' } '
            self.sock.send(str.encode(cmd))
            print(self.sock.recv(1056))
            #add certname, port, password to a json list to ues at delete/boot
            servers.delete(certname=cname)
            print('disabling port forwarding to port ' + str(port))
            device = Device()
            device.close_port(port)
        #retrun success or failure if file doesn't exist
        if 0 and local_db is not None:
            for a in local_db['servers']:
                print(a)
        return
        return


    def start_all(self):
        #used at boot time
        #loop over cert files, start each
        local_db = dataset.connect('sqlite:///'+self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        if not servers:
            return
        for server in local_db['servers']:
            cmd = 'add : {"server_port": '+str(server['server_port'])+' , "password" : "'+str(server['password'])+'" } '
            self.sock.send(str.encode(cmd))
            print(cmd + ' >> '+ str(self.sock.recv(1056)))
            device = Device()
            device.open_port(server['server_port'], 'ShadowSocks '+server['certname'])
        return

    def stop_all(self):
        #used at service stop time
        #loop over cert files, stop all 
        local_db = dataset.connect('sqlite:///'+self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        if not servers:
            print('no servers')
            return
        for server in local_db['servers']:
            cmd = 'remove : {"server_port": '+str(server['server_port'])+' } '
            self.sock.send(str.encode(cmd))
            print(server['certname'] + ' >>' + cmd + ' >> '+ str(self.sock.recv(1056)))
        return 
    #forward_all is used with cron to make sure port forwardings stay active
    #if service is stopped, forwardings can stay active. there will be no ss server to serve
    def forward_all(self):
        local_db = dataset.connect('sqlite:///'+self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        if not servers:
            print('no servers')
            return
        for server in local_db['servers']:
            print('forwaring '+ str(server['server_port'])+' for '+ server['certname'])
            device = Device()
            device.open_port(server['server_port'], 'ShadowSocks '+server['certname'])
        return
    def start(self):
        self.start_all()
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
        return (int(self.config.get('shadow','enabled')) is 1 ) 

    def can_email(self):
        return (int(self.config.get('shadow','email')) is 1)

    def get_add_email_text(self, cname, ip_address):
        txt = ''
        html = ''
        if self.is_enabled() and self.can_email() :
            local_db = dataset.connect('sqlite:///'+self.config.get('shadow', 'db-path'))
            servers = local_db['servers']
            server = servers.find_one(certname = cname)
            if server is not None:
                uri = str(self.config.get('shadow','method')) + ':' + str(server['password']) + '@' + str(ip_address) + ':' + str(server['server_port'])
                print(uri + '\n\n')
                uri64 = 'ss://'+ base64.urlsafe_b64encode(str.encode(uri)).decode('utf-8')
                print(uri64)

                txt = 'To use ShadowSocks: \n\n1.Copy the below text, \n2. Open Outline or ShadowSocks apps on your phone \n3. Import this link as a new server. \n'
                txt += uri64
                html = 'For ShadowSocks: <ul> <li>Copy the below text, </li><li> Open Outline or ShadowSocks apps on your phone </li><li> Import this link as a new server. </li></ul><br /><br/>'
                html += uri64 
        return txt, html

    def get_removal_email_text(self, certname, ip_address):
        txt = ''
        html = ''
        if self.is_enabled() and self.can_email() :
            txt  = "Access to VPN server IP address " +  ip_address + " is revoked.",
            html = "Access to VPN server IP address " +  ip_address + " is revoked.",
        return txt, html
