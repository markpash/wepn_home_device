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
from flask_api import status as http_status

sys.path.insert(1, '..')
try:
    from configparser import configparser
except ImportError:
    import configparser
#from diag import WPDiag
CONFIG_FILE='test_config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
import shlex
#from ipw import IPW
#from wstatus import WStatus

#This is set if this API is externally exposed, blocking responses
exposed = False

def sanitize_str(str_in):
    return (shlex.quote(str_in))


class WStatus:
    def __init__(self):
        self.variables = {} 
        self.variables['status']={'claimed':'0', 'temporary_key':"ABC1DEF2GH3", 'local_token':'888888888'}
        pass

    def get_field(self, section, item):
        try:
            ret = self.variables[section][item]
            return ret
        except:
            print("ERROR: get_Field" + section + " - " + item)


def return_link(cname):
        server = {'password':"conn_PASSWORD", 'server_port':"conn_PORT"}
        ip_address = "123.456.789.001"
        uri="unknown"
        uri64 = "empty"
        if server is not None:
                uri = str(config.get('shadow','method')) + ':' + str(server['password']) + '@' + str(ip_address) + ':' + str(server['server_port'])
                print(uri)
                uri64 = 'ss://'+ base64.urlsafe_b64encode(str.encode(uri)).decode('utf-8')+"#WEPN-"+str(server['certname'])
        return uri64

def valid_token(incoming):
    status = WStatus() 
    return sanitize_str(incoming)==status.get_field('status','local_token')


app = flask.Flask(__name__)
app.config["DEBUG"] = True 


@app.route('/', methods=['GET'])
def home():
        return "Hello world"

@app.route('/api/v1/friends/access_links/', methods=['GET', 'POST'])
def api_all():
    if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
    status = WStatus() 
    if valid_token(request.args.get('local_token')):
        return str(return_link(sanitize_str(request.args.get('certname'))))
    else:
        return "Not allowed", http_status.HTTP_401_UNAUTHORIZED

@app.route('/api/v1/claim/info', methods=['GET'])
def claim_info():
    if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
    status = WStatus()
    serial_number = config.get('django','serial_number')
    is_claimed = status.get_field('status','claimed')
    if int(is_claimed)==1:
        dev_key="CLAIMED"
    else:
        dev_key = status.get_field('status', 'temporary_key')
    return "{\"claimed\":\""+is_claimed+"\", \"serial_number\": \"" + str(serial_number) + "\", \"device_key\":\"" + dev_key + "\"}"


@app.route('/api/v1/diagnostics/info', methods=['GET'])
def run_diag():
      if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
      if not valid_token(request.args.get('local_token')):
          return "Not accessible", http_status.HTTP_401_UNAUTHORIZED
      WPD = WPDiag()
      local_ip = WPD.get_local_ip()
      port = 4091

      print('local ip='+WPD.get_local_ip())
      
      internet = WPD.is_connected_to_internet()
      print('internet: '+str(internet))
      service = WPD.is_connected_to_service()
      print('service: '+str(service))
      WPD.open_test_port(port)
      iport = WPD.can_connect_to_external_port(port)  
      print('port test:' + str(iport))
      error_code = WPD.get_error_code(port)
      print('device status code: '+str(error_code))

      s_resp = WPD.get_server_diag_analysis(error_code)
      WPD.close_test_port(port)
      return str(s_resp)

@app.route('/api/v1/port_exposure/check', methods=['GET','POST'])
def check_port_available_externally():
    # A cron tries to access this path
    # if it is accessible from external IP then shut down
    # This API is not supposed to be externally accessible
    if not valid_token(request.form.get('local_token')):
        return "Not accessible", http_status.HTTP_401_UNAUTHORIZED
    global exposed
    exposed = True
    return "ERROR: Exposure detected! APIs are closed now.", http_status.HTTP_503_SERVICE_UNAVAILABLE

if __name__=='__main__':
    app.run(host= '0.0.0.0', ssl_context='adhoc')

