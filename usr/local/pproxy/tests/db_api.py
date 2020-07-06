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
import sys
import flask
from flask import request
sys.path.insert(1, '..')
try:
    from configparser import configparser
except ImportError:
    import configparser
CONFIG_FILE='/etc/pproxy/config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
import shlex
from ipw import IPW
from wstatus import WStatus


def sanitize_str(str_in):
    return (shlex.quote(str_in))
def return_link(cname):
        #local_db = dataset.connect('sqlite:////var/local/pproxy/shadow.db')
        local_db = dataset.connect('sqlite:///'+config.get('shadow', 'db-path'))
        #TODO
        ipw =IPW()
        ip_address = sanitize_str(ipw.myip())
        servers = local_db['servers']
        server = servers.find_one(certname = cname)
        uri="unknown"
        if server is not None:
                uri = str(config.get('shadow','method')) + ':' + str(server['password']) + '@' + str(ip_address) + ':' + str(server['server_port'])
                uri64 = 'ss://'+ base64.urlsafe_b64encode(str.encode(uri)).decode('utf-8')+"#WEPN-"+str(server['certname'])
        return uri64


app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
        status = WStatus() 
        return "<h1>Distant Reading Archive</h1><p>This site is a prototype API for distant reading of science fiction novels.</p>"+status.get(status, pin)

@app.route('/api/v1/friends/access_links/', methods=['GET'])
def api_all():
    status = WStatus() 
    if sanitize_str(request.args.get('local_token'))==status.get_field('status','local_token'):
        return str(return_link(sanitize_str(request.args.get('certname'))))
    else:
        return "Not allowed"

app.run(host= '0.0.0.0')

