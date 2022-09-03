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

def del_user_usage(certname):
        conn = sqli.connect('/var/local/pproxy/usage.db')
        cur = conn.cursor()
        if certname:
            #cmd=conn.prepare("delete from servers where certname like '?'", certname)
            #print(cmd)
            results = cur.execute("delete from servers where certname like ?", [certname])
            print(results)
        conn.commit()
        conn.close()


def delete_left_over_usage():
        usage_db = dataset.connect('sqlite:////var/local/pproxy/usage.db')
        usage_servers = usage_db['servers']
        shadow_db = dataset.connect('sqlite:////var/local/pproxy/shadow.db')
        shadow_servers = shadow_db['servers']
        if not usage_servers:
            print('no servers')
            return
        for server in usage_db['servers']:
            line = 'usage : {"server_port": '+str(server['server_port'])+', usage='+str(server['usage'])+', "certname": '+ str(server['certname'])+', status= '+ str(server['status'])+' }' 
            print(line)
            if len(list(filter(lambda shadow_server:shadow_server['certname'] == server['certname'], shadow_servers))) == 0:
                print("Need to delete " + server['certname'])
            else:
                print("retain :" + server['certname'])
        for server in usage_db['daily']:
            if len(list(filter(lambda shadow_server:shadow_server['certname'] == server['certname'], shadow_servers))) == 0:
                print("Need to delete " + str((server)))
            else:
                print("retain :" + server['certname'])
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
def print_all_usage():
        local_db = dataset.connect('sqlite:////var/local/pproxy/usage.db')
        servers = local_db['servers']
        if not servers:
            print('no servers')
            return
        print(">>------------------------------------------------------------------<<")
        for server in local_db['servers']:
            line = 'usage : {"server_port": '+str(server['server_port'])+', usage='+str(server['usage'])+', "certname": '+ str(server['certname'])+', status= '+ str(server['status'])+' }' 
            print(line)
        print("||------------------------daily usage-------------------------------||")
        for server in local_db['daily']:
            print(server)
        print("||------------------------------------------------------------------||")

# add_user('abcd','1.1.1.1','kjasas../.../da',999)
# del_user(1)
print_all()
print_all_usage()
del_user_usage("8i.vy; select * from usage")
delete_left_over_usage()
#print_all_usage()
