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
    """
    Add a new user to the database.

    Args:
    - cname (str): The certificate name.
    - ip_address (str): The IP address of the user.
    - password (str): The user's password.
    - port (int): The port to use for the user's connection.

    Returns:
    - None
    """
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

def del_user(port):
    """
    Delete a user from the database.

    Args:
    - port (int): The port to delete.

    Returns:
    - None
    """
    
    conn = sqli.connect('/var/local/pproxy/usage.db')
    cur = conn.cursor()
    results = cur.execute("delete from servers")
    conn.commit()
    conn.close()


def print_all():
    """
    Print all users.

    Args:
    - None

    Returns:
    - None
    """
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

def print_all_usage():
    """
    Print all usage.

    Args:
    - None

    Returns:
    - None
    """
    local_db = dataset.connect('sqlite:////var/local/pproxy/usage.db')
    servers = local_db['servers']
    if not servers:
        print('no servers')
        return
    for server in local_db['servers']:
        line = 'usage : {"server_port": '+str(server['server_port'])+', usage='+str(server['usage'])+', "certname": '+ str(server['certname'])+', status= '+ str(server['status'])+' }' 
        print(line)

# Start here

# add_user('abcd','1.1.1.1','kjasas../.../da',999)
# del_user(1)
print_all()
print_all_usage()
