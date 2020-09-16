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

def add_user(cname, ip_address, password, port):
    local_db = dataset.connect('sqlite:////var/local/pproxy/shadow.db')
    #get max of assigned ports, new port is 1+ that. 
    #if no entry in DB, copy from config default port start
    servers = local_db['servers']
    server = servers.find_one(certname = cname)
    #if already exists, use same port
    #else assign a new port, 1+laargest existing
    if server is None:
        try:
            #results = local_db.query('select max(server_port) from servers where certname!= ?', (cname))
            conn = sqli.connect('/var/local/pproxy/shadow.db')
            cur = conn.cursor()
            results = cur.execute('select max(server_port) from servers where certname!= ?', (cname,))
            row = cur.fetchone()
            max_port = row[0] 
            conn.close()
        except Exception as e:
            print(e)
            max_port = None
        if max_port is None:
            max_port = 90000;#int(self.config.get('shadow','start-port'))
        print("New port assigned is " + str(max_port+1) + " was " + str(port))
        port=max_port + 1 

    cmd = 'add : {"server_port": '+str(port)+' , "password" : "'+str(password)+'" } '
    print("cmd="+cmd)

def print_all():
        #used at service stop time
        #loop over cert files, stop all 
        local_db = dataset.connect('sqlite:////var/local/pproxy/shadow.db')
        servers = local_db['servers']
        if not servers:
            print('no servers')
            return
        for server in local_db['servers']:
            cmd = 'list : {"server_port": '+str(server['server_port'])+', '+str(server['password'])+', "certname": '+ str(server['certname'])+'}' 
            print(cmd)

#add_user('abcd','1.1.1.1','kjasas../.../da',999)
print_all()
