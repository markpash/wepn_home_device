import pytest
import time
import sqlite3
import base64

try:
    from self.configparser import configparser
except ImportError:
    import configparser

TEST_CONFIG = 'dev_config.ini'
#TEST_CONFIG = 'prod_config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'

PPROXY_CONFIG='/etc/pproxy/config.ini'
config = configparser.ConfigParser()
config.read(TEST_CONFIG)
pproxy_config = configparser.ConfigParser()
pproxy_config.read(PPROXY_CONFIG)

token=config.get('user', 'token')
user=config.get('user', 'user')
password=config.get('user', 'password')

authorization_base_url = config.get('app', 'authorization_base_url')
client_id= config.get('app', 'client_id')
client_secret=config.get('app', 'client_secret')

url=config.get('device', 'url')
key=config.get('device', 'key')
#serial=config.get('device', 'serial')
serial=pproxy_config.get('django', 'serial_number')
shadow_db=pproxy_config.get('shadow', 'db-path')

status = configparser.ConfigParser()
status.read(STATUS_FILE)

static_friend_id=config.get('friend','static_id')
friend_access_key = ""
local_api_url = "https://127.0.0.1:5000"
local_api_url = "http://127.0.0.1:5000"


import json
import requests

auth_token = "#nosec:JUSTAPLACEHOLDER" #nosec: not a real token
friend_id = None
device_id = None


def util_iterate_apis(expected_code):
    result = True
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    local_token = status.get('status','local_token')
    headers = {
            "content-type": "application/json"
            }
    apis = [ "/api/v1/friends/usage/", 
                "/api/v1/friends/access_links/",
                "/api/v1/claim/info",
                "/api/v1/claim/progress",
                "/api/v1/diagnostics/info",
                "/api/v1/diagnostics/error_log"]
    for api in apis:
        payload = {
                'local_token':str(local_token),
                #'certname':'cf.9q'}
                'certname':'zxcvb'}
        response = requests.get(url=local_api_url + api,
                params= payload)
        print(response.content)
        result = result and (response.status_code == expected_code)
        time.sleep(2)
    return result


# making HTML output pretty
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin('html')
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, 'extra', [])
    extra.append(pytest_html.extras.url('https://www.we-pn.com/'))
    extra.append(pytest_html.extras.image('https://we-pn.com/img/logo.png'))
    if report.when == 'call':
        # always add url to report
        xfail = hasattr(report, 'wasxfail')
        if (report.skipped and xfail) or (report.failed and not xfail):
            # only add additional html on failure
            extra.append(pytest_html.extras.html('<div>Failed Instance</div>'))
    report.extra = extra


@pytest.mark.dependency()
def test_login():
    global auth_token
    payload = {"grant_type":"password","username":user,"password":password,
            "client_id":client_id,
            "client_secret":client_secret}

    headers = {
            "content-type": "application/json"
            }
    #print(payload)
    response = requests.post(authorization_base_url, json=payload, headers=headers)
    jresponse = response.json()
    auth_token = "Bearer " + jresponse['access_token']
    assert(response.status_code == 200) #nosec: assert is a legit check for pytest
    pass

def test_login_fail():
    payload = {"grant_type":"password","username":user,"password":"clearlywrong",
            "client_id":client_id,
            "client_secret":client_secret}

    headers = {
            "content-type": "application/json"
            }
    response = requests.post(authorization_base_url, json=payload, headers=headers)
    jresponse = response.json()
    assert(response.status_code != 200) #nosec: assert is a legit check for pytest
    pass


@pytest.mark.dependency(depends=["test_login"])
def test_confirm_device_unclaimed():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    assert(status.get('status','claimed') == '0') #nosec: assert is a legit check for pytest

@pytest.mark.dependency(depends=["test_confirm_device_unclaimed"]) 
def test_api_returns_unclaimed():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    key = status.get('status','temporary_key')
    # get the key through the local API
    response = requests.get(local_api_url + "/api/v1/claim/info", verify = False)
    jresponse = response.json()
    assert(response.status_code == 200) #nosec: assert is a legit check for pytestv
    assert(int(jresponse['claimed']) == 0)
    assert(jresponse['device_key'] == key)


@pytest.mark.dependency(depends=["test_login"])	
#@pytest.mark.skip(reason="this blocks on prod")
def test_claim():
    global device_id
    global key
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    key = status.get('status','temporary_key')
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    payload = {"device_key":key, "serial_number":serial, "device_name":"Regression Device"}
    response = requests.post(url + '/device/claim/', json=payload, headers=headers)
    #print(payload)
    #print(response)
    jresponse = response.json()
    #print (jresponse)
    #print(response.status_code)
    #print(payload)
    assert(response.status_code == 200) #nosec: assert is a legit check for pytest
    device_id = jresponse['id']

@pytest.mark.dependency(depends=["test_login","test_claim"])
def test_claim_fail_serial():
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    payload = {"device_key":key,"serial_number":"BADBEEF", "device_name":"Regression Device"}
    response = requests.post(url + '/device/claim/', json=payload, headers=headers)
    #print(response)
    assert(response.status_code != 200) #nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login","test_claim","test_confirm_device_unclaimed"])
def test_check_device_connected():
    time.sleep(30) # assuming it takes x seconds for onboarding to kick-in
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    assert(status.get('status','claimed') == '1') #nosec: assert is a legit check for pytest

@pytest.mark.dependency(depends=["test_login","test_claim", "test_check_device_connected"]) 
def test_api_claim_info_redacted_post_claim():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    key = status.get('status','temporary_key')
    print(key)
    assert(key == 'CLAIMED')
    # get the key through the local API
    response = requests.get(local_api_url + "/api/v1/claim/info", verify = False)
    jresponse = response.json()
    print("This is the result:")
    assert(response.status_code == 200) #nosec: assert is a legit check for pytestv
    assert(jresponse['claimed'] == '1')
    assert(jresponse['device_key'] == 'CLAIMED')
    print(jresponse)


@pytest.mark.dependency(depends=["test_login","test_claim"])	
def test_heartbeat():
    global friend_id
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    payload = {"serial_number": serial, "ip_address": "1.2.3.164", "status": "2", "pin": "6696941737", "local_token": "565656", "local_ip_address": "192.168.1.118", "device_key":key, "port": "3074", "software_version": "0.11.1", "diag_code": 119, "access_cred": {}, "usage_status": {}}
    response = requests.get(url + '/device/heartbeat/', json=payload, headers=headers)
    jresponse = response.json()
    #print (jresponse)
    #print(response.status_code)
    assert(response.status_code == 200) #nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login"])	
def test_list_friends():
    headers = {
            "Authorization" : auth_token,
            }
    expected = [{"id":int(static_friend_id),"email":"test-email@we-pn.com","telegram_handle":"no_handle","has_connected":True,"usage_status":-1,"passcode":"test pass code","cert_id":"1n.b4","language":"en"}]
    response = requests.get(url + '/friend/', headers=headers)
    jresponse = response.json()
    assert(response.status_code == 200) #nosec: assert is a legit check for pytest
    #print (jresponse)
    assert(jresponse == expected) #nosec: assert is a legit check for pytest

@pytest.mark.dependency(depends=["test_login","test_claim", "test_heartbeat", "test_list_friends"])	
def test_heartbeat_change_usage_status():
    global friend_id
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    payload = {"serial_number": serial, "ip_address": "1.2.3.164", "status": "2", "pin": "6696941737", "local_token": "565656", "local_ip_address": "192.168.1.118", "device_key":key, "port": "3074", "software_version": "0.11.1", "diag_code": 119, "access_cred": {}, "usage_status": {"1n.b4":1}}
    response = requests.get(url + '/device/heartbeat/', json=payload, headers=headers)
    jresponse = response.json()
    assert(response.status_code == 200) #nosec: assert is a legit check for pytest
    expected = [{"id":int(static_friend_id),"email":"test-email@we-pn.com","telegram_handle":"no_handle","has_connected":True,"usage_status":1,"passcode":"test pass code","cert_id":"1n.b4","language":"en"}]
    response = requests.get(url + '/friend/', headers=headers)
    jresponse = response.json()
    assert(response.status_code == 200) #nosec: assert is a legit check for pytest
    #print (jresponse)
    assert(jresponse == expected) #nosec: assert is a legit check for pytest
    # reset the usge to -1
    payload = {"serial_number": serial, "ip_address": "1.2.3.164", "status": "2", "pin": "6696941737", "local_token": "565656", "local_ip_address": "192.168.1.118", "device_key":key, "port": "3074", "software_version": "0.11.1", "diag_code": 119, "access_cred": {}, "usage_status": {"1n.b4":-1}}
    response = requests.get(url + '/device/heartbeat/', json=payload, headers=headers)
    assert(response.status_code == 200) #nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login", "test_list_friends", "test_claim"])
def test_add_friend():
    global friend_id
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    payload = {"id":0, 'email': 'regression_added@we-pn.com', 'telegram_handle': 'tlgrm_hndl', 'has_connected': False, 'usage_status': 0, 'passcode': 'test pass code', 'cert_id': 'zxcvb', 'language': 'cn'}
    response = requests.post(url + '/friend/', json=payload, headers=headers)
    #print (response.content)
    assert(response.status_code == 201) #nosec: assert is a legit check for pytest
    jresponse = response.json()
    #print (jresponse)
    #print(response.status_code)
    payload['id'] = jresponse['id']
    friend_id = payload['id']
    #print(payload)
    assert(jresponse == payload) #nosec: assert is a legit check for pytest
    time.sleep(5)
    conn = sqlite3.connect(shadow_db)
    cursor = conn.cursor()
    cursor.execute('''SELECT * from servers where certname like "zxcvb" and language like "cn"''')
    result = cursor.fetchall()
    conn.close()
    assert(len(result)==1) #nosec: assert is a legit check for pytest

#@pytest.mark.dependency(depends=["test_add_friend"])
def test_api_gives_correct_key():
    '''get the key through the API server
    compare to firend_access_key'''
    conn = sqlite3.connect(shadow_db)
    cursor = conn.cursor()
    cursor.execute('''SELECT * from servers where certname like "zxcvb" and language like "cn"''')
    #cursor.execute('''SELECT server_port, password from servers where certname like "cf.9q"''')
    #cursor.execute('''SELECT * from servers''')
    result = cursor.fetchall()
    conn.close()
    real_ss_pass = result[0][1]
    real_port = result[0][0]
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    local_token = status.get('status','local_token')
    headers = {
            "content-type": "application/json"
            }
    payload = {
            'local_token':str(local_token),
            #'certname':'cf.9q'}
            'certname':'zxcvb'}
    response = requests.post(url=local_api_url + "/api/v1/friends/access_links/",
            params= payload)
    assert(response.status_code == 200)
    jresponse = response.json()
    split_resp = base64.b64decode(jresponse['link'][5:61]).decode('utf-8').replace('@',':').split(':')
    assert(int(real_ss_pass) == int(split_resp[1]))
    assert(int(real_port) == int(split_resp[3]))



#@pytest.mark.dependency(depends=["test_add_friend"])
def test_delete_friend():
    global friend_id
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    response = requests.delete(url + '/friend/'+ str(friend_id), headers=headers)
    assert(response.status_code == 204) #nosec: assert is a legit check for pytest
    friend_id = None
    # wait for server to send the command to device
    time.sleep(10)
    # check local database to see if the friend was removed
    conn = sqlite3.connect(shadow_db)
    cursor = conn.cursor()
    cursor.execute('''SELECT * from servers where certname like "zxcvb" and language like "cn"''')
    result = cursor.fetchall()
    conn.close()
    assert(len(result) == 0)
    # Now make sure the local API server is also empty
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    local_token = status.get('status','local_token')
    headers = {
            "content-type": "application/json"
            }
    payload = {
            'local_token':str(local_token),
            #'certname':'cf.9q'}
            'certname':'zxcvb'}
    response = requests.post(url=local_api_url + "/api/v1/friends/access_links/",
            params= payload)
    assert(response.status_code == 200)
    jresponse = response.json()
    assert(jresponse['link'] == "empty")
    assert(jresponse["digest"] == "")

def test_check_api_calls_access():
    '''
    loop through all api calls in flask
    make sure if provided an invalid key, it reject
    '''
    assert(util_iterate_apis(200))
    pass

def test_check_api_calls_valid():
    # probably more than one call: do apis work?
    pass

def test_simulate_web_exposure():
    '''
    fake an exposure by calling the protected api
    the same that heartbeat calls
    now check the subsequent calls to **ALL** apis are blocked
    '''
    local_token = status.get('status','local_token')
    headers = {
            "content-type": "application/json"
            }
    payload = { 'local_token':str(local_token) }
    # first, things should be normal
    assert(util_iterate_apis(200))
    response = requests.post(url=local_api_url + "/api/v1/port_exposure/check", params=payload)
    # now they should be blocked
    assert(util_iterate_apis(403))
    pass


@pytest.mark.dependency(depends=["test_login", "test_claim", "test_heartbeat"])
def test_unclaim():
    global device_id
    headers = {
            "Authorization" : auth_token,
            }
    response = requests.get(url + '/device/'+str(device_id)+'/unclaim/', headers=headers)
    jresponse = response.json()
    #print (jresponse)
    #print(response.status_code)
    assert(response.status_code == 200) #nosec: assert is a legit check for pytest


def test_api_updated_unclaim():
    '''
    depends on unclaim (if not rebooting)
        check API is not leaking incorrec info after 5 seconds
    '''
    pass
#test_login()
#test_list()
#test_add()
#test_delete()
#test_list()
