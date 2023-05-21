import requests
import json
import pytest
import time
import sqlite3
import base64

try:
    from self.configparser import configparser
except ImportError:
    import configparser

# TEST_CONFIG = 'dev_config.ini'
TEST_CONFIG = 'prod_config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'

PPROXY_CONFIG = '/etc/pproxy/config.ini'
config = configparser.ConfigParser()
config.read(TEST_CONFIG)
pproxy_config = configparser.ConfigParser()
pproxy_config.read(PPROXY_CONFIG)

token = config.get('user', 'token')
user = config.get('user', 'user')
password = config.get('user', 'password')

authorization_base_url = config.get('app', 'authorization_base_url')
client_id = config.get('app', 'client_id')
client_secret = config.get('app', 'client_secret')

url = config.get('device', 'url')
key = config.get('device', 'key')
device_id = pproxy_config.get('mqtt', 'username')
serial = pproxy_config.get('django', 'serial_number')
shadow_db = pproxy_config.get('shadow', 'db-path')

static_friend_id = config.get('friend', 'static_id')
friend_access_key = ""
local_api_url = "https://127.0.0.1:5000"


auth_token = "#nosec:JUSTAPLACEHOLDER"  # nosec: not a real token
friend_id = None
device_id = None


def decode_base64(encoded_str):
    """
    This function decodes a base64 encoded string
    """
    missing_padding = len(encoded_str) % 4
    if missing_padding != 0:
        encoded_str += '=' * (4 - missing_padding)
    decoded_bytes = base64.b64decode(encoded_str)
    decoded_str = decoded_bytes.decode('utf-8')

    decoded_str = decoded_str.replace('@', ':')
    components = decoded_str.split(':')
    return components


def util_iterate_apis(local_token, expected_code, filter_auth=False):
    """
    a utility to process APIs
    """
    result = True
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)

    headers = {
        "content-type": "application/json"
    }
    apis = [
        {"url": "/api/v1/friends/usage/", "auth": True, },
        {"url": "/api/v1/friends/access_links/", "auth": True, },
        {"url": "/api/v1/claim/info", "auth": False, },
        {"url": "/api/v1/claim/progress", "auth": False},
        # if unclaimed, no auth needed
        {"url": "/api/v1/diagnostics/info", "auth": (status.get('status', 'claimed') == '0'), },
        {"url": "/api/v1/diagnostics/error_log", "auth": True, },
    ]
    for api in apis:
        if filter_auth:
            # if asked, skip testing APIs that don't need auth
            if not api['auth']:
                continue
        payload = {
            'local_token': str(local_token),
            'certname': 'zxcvb'}
        response = requests.get(url=local_api_url + api['url'],
                                params=payload, verify=False)
        result = result and (response.status_code == expected_code)
        time.sleep(2)
    return result


# making HTML output pretty
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    report prettyfier
    """
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

    payload = {"grant_type": "password",
               "username": user,
               "password": password,
               "client_id": client_id,
               "client_secret": client_secret
               }

    headers = {
        "content-type": "application/json"
    }
    response = requests.post(authorization_base_url, json=payload, headers=headers)
    jresponse = response.json()
    auth_token = "Bearer " + jresponse['access_token']

    assert (response.status_code == 200)  # nosec: assert is a legit check for pytest
    pass


@pytest.mark.dependency(depends=["test_login"])
def test_clean_friend():
    """
    """
    headers = {
        "Authorization": auth_token,
    }

    response = requests.get(url + '/friend/', headers=headers)
    jresponse = response.json()
    for item in jresponse:
        friend_id = item['id']
        response = requests.delete(url + '/friend/' + str(friend_id), headers=headers)
        assert (response.status_code == 200)  # nosec: assert is a legit check for pytest

    # nosec: assert is a legit check for pytest
    assert (response.status_code == 200 or response.status_code == 204)


def test_login_fail():
    payload = {"grant_type": "password",
               "username": user,
               "password": "clearlywrong",
               "client_id": client_id,
               "client_secret": client_secret
               }

    headers = {
        "content-type": "application/json"
    }
    response = requests.post(authorization_base_url, json=payload, headers=headers)
    jresponse = response.json()
    assert (response.status_code != 200)  # nosec: assert is a legit check for pytest
    pass


@pytest.mark.dependency(depends=["test_login"])
def test_confirm_device_unclaimed():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    assert (status.get('status', 'claimed') == '0')  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_confirm_device_unclaimed"])
def test_api_returns_unclaimed():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    key = status.get('status', 'temporary_key')

    # get the key through the local API
    response = requests.get(local_api_url + "/api/v1/claim/info", verify=False)
    jresponse = response.json()
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytestv
    assert (int(jresponse['claimed']) == 0)
    assert (jresponse['device_key'] == key)


@pytest.mark.dependency(depends=["test_login"])
def test_claim():
    global device_id
    global key
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    key = status.get('status', 'temporary_key')
    headers = {
        "Authorization": auth_token,
        "content-type": "application/json"
    }
    payload = {"device_key": key,
               "serial_number": serial,
               "device_name": "Regression Device"
               }
    response = requests.post(url + '/device/claim/', json=payload, headers=headers)
    jresponse = response.json()
    device_id = jresponse['id']
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login", "test_claim"])
def test_claim_fail_serial():
    headers = {
        "Authorization": auth_token,
        "content-type": "application/json"
    }
    payload = {"device_key": key,
               "serial_number": "BADBEEF",
               "device_name": "Regression Device"
               }
    response = requests.post(url + '/device/claim/', json=payload, headers=headers)
    assert (response.status_code != 200)  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login", "test_claim", "test_confirm_device_unclaimed"])
@pytest.mark.flaky(retries=4, delay=30)
def test_check_device_connected():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    assert (status.get('status', 'claimed') == '1')  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login", "test_claim"])
@pytest.mark.flaky(retries=3, delay=10)
def test_api_claim_info_redacted_post_claim():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    key = status.get('status', 'temporary_key')
    assert (key == 'CLAIMED')
    # get the key through the local API
    response = requests.get(local_api_url + "/api/v1/claim/info", verify=False)
    jresponse = response.json()
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytestv
    assert (jresponse['claimed'] == '1')
    assert (jresponse['device_key'] == 'CLAIMED')


@pytest.mark.dependency(depends=["test_login", "test_claim"])
def test_heartbeat():
    global friend_id
    headers = {
        "Authorization": auth_token,
        "content-type": "application/json"
    }
    payload = {"serial_number": serial,
               "ip_address": "1.2.3.164",
               "status": "2",
               "pin": "6696941737",
               "local_token": "565656",
               "local_ip_address": "192.168.1.118",
               "device_key": key,
               "port": "3074",
               "software_version": "0.11.1",
               "diag_code": 119,
               "access_cred": {},
               "usage_status": {}
               }
    response = requests.get(url + '/device/heartbeat/', json=payload, headers=headers)
    jresponse = response.json()
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login", "test_claim"])
def test_add_friend():
    global friend_id
    headers = {
        "Authorization": auth_token,
        "content-type": "application/json"
    }
    payload = {"id": 0,
               'email': 'regression_added@we-pn.com',
               'telegram_handle': 'tlgrm_hndl',
               'has_connected': False,
               'usage_status': 0,
               'passcode': 'test pass code',
               'cert_hash': None,
               'cert_id': 'zxcvb',
               'language': 'en',
               'config': {"tunnel": "shadowsocks"},
               'name': 'regression_added@we-pn.com',
               'subscribed': True
               }
    response = requests.post(url + '/friend/', json=payload, headers=headers)
    assert (response.status_code == 201)  # nosec: assert is a legit check for pytest
    jresponse = response.json()
    payload['id'] = jresponse['id']
    friend_id = payload['id']
    assert (jresponse == payload)  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login", "test_add_friend"])
def test_list_friends():
    headers = {
        "Authorization": auth_token,
    }
    expected = {"id": 0, 'email': 'regression_added@we-pn.com', 'telegram_handle': 'tlgrm_hndl', 'has_connected': False, 'usage_status': 0, 'passcode': 'test pass code',
                'cert_id': 'zxcvb', 'cert_hash': None, 'language': 'en', 'config': {"tunnel": "shadowsocks"}, 'name': 'regression_added@we-pn.com', 'subscribed': True}
    response = requests.get(url + '/friend/', headers=headers)
    jresponse = response.json()
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytest
    jresponse[0]['id'] = 0
    assert (jresponse == [expected])  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_add_friend"])
@pytest.mark.flaky(retries=3, delay=75)
def test_added_friend_in_local_db():
    global friend_id
    conn = sqlite3.connect(shadow_db)
    cursor = conn.cursor()
    cursor.execute('''SELECT * from servers where certname like "zxcvb" and language like "en"''')
    result = cursor.fetchall()
    conn.close()
    assert (len(result) == 1)  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_login", "test_claim", "test_heartbeat", "test_add_friend", "test_list_friends"])
@pytest.mark.flaky(retries=5, delay=15)
def test_heartbeat_change_usage_status():
    """
    """
    global friend_id
    headers = {
        "Authorization": auth_token,
        "content-type": "application/json"
    }
    payload = {"serial_number": serial,
               "ip_address": "1.2.3.164",
               "status": "2",
               "pin": "6696941737",
               "local_token": "565656",
               "local_ip_address": "192.168.1.118",
               "device_key": key,
               "port": "3074",
               "software_version": "0.11.1",
               "diag_code": 119,
               "access_cred": {},
               "usage_status": {"zxcvb": 1}
               }
    response = requests.get(url + '/device/heartbeat/', json=payload, headers=headers)
    jresponse = response.json()
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytest
    expected = [{"id": int(friend_id), 'email': 'regression_added@we-pn.com', 'telegram_handle': 'tlgrm_hndl', 'has_connected': True, 'usage_status': 1, 'passcode': 'test pass code',
                 'cert_id': 'zxcvb', 'cert_hash': None, 'language': 'en', 'name': 'regression_added@we-pn.com', 'config': {'tunnel': 'shadowsocks'}, 'subscribed': True}]

    response = requests.get(url + '/friend/', headers=headers)
    jresponse = response.json()
    expected[0]['cert_hash'] = jresponse[0]['cert_hash']
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytest
    assert (jresponse == expected)  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_add_friend"])
def test_api_gives_correct_key():
    '''
    get the key through the API server
    compare to friend_access_key
    '''
    conn = sqlite3.connect(shadow_db)
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT server_port, password from servers where certname like "zxcvb" and language like "en"''')
    result = cursor.fetchall()
    conn.close()
    assert (len(result) == 1)
    real_ss_pass = result[0][1]
    real_port = result[0][0]
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    local_token = status.get('status', 'local_token')
    headers = {
        "content-type": "application/json"
    }
    payload = {
        'local_token': str(local_token),
        'certname': 'zxcvb'}
    response = requests.post(url=local_api_url + "/api/v1/friends/access_links/",
                             params=payload, verify=False)
    assert (response.status_code == 200)
    jresponse = response.json()
    encoded_str = jresponse['link'][5:-11]
    components = decode_base64(encoded_str)

    assert (int(real_ss_pass) == int(components[1]))
    assert (int(real_port) == int(components[3]))


@pytest.mark.dependency(depends=["test_add_friend"])
def test_delete_friend():
    global friend_id
    headers = {
        "Authorization": auth_token,
        "content-type": "application/json"
    }
    response = requests.delete(url + '/friend/' + str(friend_id), headers=headers)
    assert (response.status_code == 204)  # nosec: assert is a legit check for pytest
    friend_id = None


@pytest.mark.dependency(depends=["test_delete_friend"])
@pytest.mark.flaky(retries=3, delay=75)
def test_deleted_friend_in_local_db():
    # wait for server to send the command to device
    time.sleep(5)
    # check local database to see if the friend was removed
    conn = sqlite3.connect(shadow_db)
    cursor = conn.cursor()
    cursor.execute('''SELECT * from servers where certname like "zxcvb" and language like "en"''')
    result = cursor.fetchall()
    conn.close()
    assert (len(result) == 0)


@pytest.mark.dependency(depends=["test_delete_friend"])
def test_deleted_friend_in_api():
    # Now make sure the local API server is also empty
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    local_token = status.get('status', 'local_token')
    headers = {
        "content-type": "application/json"
    }
    payload = {
        'local_token': str(local_token),
        'certname': 'zxcvb'
    }
    response = requests.post(url=local_api_url + "/api/v1/friends/access_links/",
                             params=payload, verify=False)
    assert (response.status_code == 200)
    jresponse = response.json()
    assert (jresponse['link'] == "empty")
    assert (jresponse["digest"] == "")


@pytest.mark.dependency(depends=["test_confirm_device_unclaimed"])
def test_check_api_calls_access():
    '''
    loop through all api calls in flask
    make sure if provided an invalid key, it reject
    '''
    assert (util_iterate_apis("BAD_TOKEN", 401, True))


@pytest.mark.dependency(depends=["test_api_gives_correct_key"])
def test_check_api_calls_valid():
    # first, things should be normal
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    local_token = status.get('status', 'local_token')
    assert (util_iterate_apis(local_token, 200, True))


@pytest.mark.dependency(depends=["test_login"])
def test_unclaim():
    device_id = pproxy_config.get('mqtt', 'username')
    headers = {
        "Authorization": auth_token,
    }
    response = requests.get(url + '/device/' + str(device_id) + '/unclaim/', headers=headers)
    jresponse = response.json()
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_unclaim"])
@pytest.mark.flaky(retries=2, delay=60)
def test_check_device_disconnected_unclaimed():
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)
    assert (status.get('status', 'claimed') == '0')  # nosec: assert is a legit check for pytest


@pytest.mark.dependency(depends=["test_unclaim"])
def test_api_updated_unclaim():
    '''
    depends on unclaim (if not rebooting)
        check API is not leaking incorrec info after 5 seconds
    '''
    time.sleep(5)
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)

    key = status.get('status', 'temporary_key')
    # get the key through the local API
    response = requests.get(local_api_url + "/api/v1/claim/info", verify=False)
    jresponse = response.json()
    assert (response.status_code == 200)  # nosec: assert is a legit check for pytestv
    assert (int(jresponse['claimed']) == 0)
    assert (jresponse['device_key'] == key)

# last test, since it will kill the api server


@pytest.mark.dependency(depends=["test_check_api_calls_valid", "test_api_updated_unclaim"])
def test_simulate_web_exposure():
    '''
    fake an exposure by calling the protected api
    the same that heartbeat calls
    now check the subsequent calls to **ALL** apis are blocked
    '''
    status = configparser.ConfigParser()
    status.read(STATUS_FILE)

    local_token = status.get('status', 'local_token')
    headers = {
        "content-type": "application/json"
    }
    response = requests.get(
        url=local_api_url + "/api/v1/port_exposure/check?local_token=" + local_token, verify=False)
    # now they should be blocked
    assert (util_iterate_apis(local_token, 503))
