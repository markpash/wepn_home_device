import pytest
import time
try:
    from self.configparser import configparser
except ImportError:
    import configparser

TEST_CONFIG = 'local_test_config.ini'
config = configparser.ConfigParser()
config.read(TEST_CONFIG)

token=config.get('user', 'token')
user=config.get('user', 'user')
password=config.get('user', 'password')

authorization_base_url = config.get('app', 'authorization_base_url')
client_id= config.get('app', 'client_id')
client_secret=config.get('app', 'client_secret')

url=config.get('device', 'url')
key=config.get('device', 'key')
serial=config.get('device', 'serial')


import json
import requests

auth_token = "FF"
friend_id = None
device_id = None

# making HTML output pretty
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin('html')
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, 'extra', [])
    if report.when == 'call':
        # always add url to report
        extra.append(pytest_html.extras.url('https://www.we-pn.com/'))
        extra.append(pytest_html.extras.image('https://we-pn.com/img/logo.png'))
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
    #print(response.status_code)
    #print(jresponse['access_token'])
    auth_token = "Bearer " + jresponse['access_token']
    assert(response.status_code == 200)
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
    assert(response.status_code != 200)
    pass



@pytest.mark.dependency(depends=["test_login"])	
def test_claim():
    global device_id
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    payload = {"device_key":key,"serial_number":serial, "device_name":"Regression Device"}
    response = requests.post(url + '/device/claim/', json=payload, headers=headers)
    jresponse = response.json()
    #print (jresponse)
    #print(response.status_code)
    #print(payload)
    assert(response.status_code == 200)
    device_id = jresponse['id']

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
    assert(response.status_code == 200)

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
    assert(response.status_code == 200)

@pytest.mark.dependency(depends=["test_login"])	
def test_list_friends():

    headers = {
            "Authorization" : auth_token,
            }
    expected = [{"id":424,"email":"test-email@we-pn.com","telegram_handle":"no_handle","has_connected":True,"usage_status":-1,"passcode":"test pass code","cert_id":"1n.b4","language":"en"}]
    response = requests.get(url + '/friend/', headers=headers)
    jresponse = response.json()
    assert(response.status_code == 200)
    print (jresponse)
    assert(jresponse == expected)

@pytest.mark.dependency(depends=["test_login","test_claim", "test_heartbeat", "test_list_friends"])	
def test_heartbeat_change_usage_status():
    global friend_id
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    payload = {"serial_number": serial, "ip_address": "1.2.3.164", "status": "2", "pin": "6696941737", "local_token": "565656", "local_ip_address": "192.168.1.118", "device_key":key, "port": "3074", "software_version": "0.11.1", "diag_code": 119, "access_cred": {}, "usage_status": {"1n.b4":"1"}}
    response = requests.get(url + '/device/heartbeat/', json=payload, headers=headers)
    jresponse = response.json()
    assert(response.status_code == 200)
    expected = [{"id":424,"email":"test-email@we-pn.com","telegram_handle":"no_handle","has_connected":True,"usage_status":1,"passcode":"test pass code","cert_id":"1n.b4","language":"en"}]
    response = requests.get(url + '/friend/', headers=headers)
    jresponse = response.json()
    assert(response.status_code == 200)
    print (jresponse)
    assert(jresponse == expected)
    test_heartbeat() # reset the usge to -1


@pytest.mark.dependency(depends=["test_login"])	
def test_add_friend():
    global friend_id
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    payload = {'id': 457, 'email': 'regression_added@we-pn.com', 'telegram_handle': 'tlgrm_hndl', 'has_connected': False, 'usage_status': 0, 'passcode': 'test pass code', 'cert_id': 'zxcvb', 'language': 'cn'}
    response = requests.post(url + '/friend/', json=payload, headers=headers)
    jresponse = response.json()
    #print (jresponse)
    #print(response.status_code)
    assert(response.status_code == 201)
    payload['id'] = jresponse['id']
    friend_id = payload['id']
    #print(payload)
    assert(jresponse == payload)


@pytest.mark.dependency(depends=["test_add_friend"])	
def test_delete_friend():
    global friend_id
    #friend_id = "441"
    headers = {
            "Authorization" : auth_token,
            "content-type": "application/json"
            }
    response = requests.delete(url + '/friend/'+ str(friend_id), headers=headers)
    #print(response.status_code)
    #print(response.content)
    assert(response.status_code == 204)
    frien_id = None
#test_login()
#test_list()
#test_add()
#test_delete()
#test_list()
