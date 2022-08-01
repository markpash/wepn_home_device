import sys
sys.path.insert(1, '..')
from wstatus import WStatus
from ipw import IPW
import shlex
from services import Services
from device import Device
from diag import WPDiag
import json
import dataset
import base64
import flask
from flask import request
from flask_api import status as http_status
import hashlib
import logging.config

try:
    from configparser import configparser
except ImportError:
    import configparser
ERROR_LOG_FILE = "/var/local/pproxy/error.log"
CONFIG_FILE = '/etc/pproxy/config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
logger = logging.getLogger("local-api")

# This is set if this API is externally exposed, blocking responses
exposed = False


def sanitize_str(str_in):
    return (shlex.quote(str_in))


def return_link(cname):
    local_db = dataset.connect('sqlite:///' + config.get('shadow', 'db-path'))
    ipw = IPW()
    ip_address = sanitize_str(ipw.myip())
    if config.has_section("dyndns") and config.getboolean('dyndns', 'enabled'):
        # we have good DDNS, lets use it
        server_address = config.get("dyndns", "hostname")
    else:
        server_address = ip_address
    servers = local_db['servers']
    server = servers.find_one(certname=cname)
    uri = "unknown"
    uri64 = "empty"
    digest = ""
    if server is not None:
        uri = str(config.get('shadow', 'method')) + ':' + \
            str(server['password']) + '@' + str(server_address) + ':' + str(server['server_port'])
        print(uri)
        uri64 = 'ss://' + \
            base64.urlsafe_b64encode(str.encode(uri)).decode(
                'utf-8') + "#WEPN-" + str(server['certname'])
        digest = hashlib.sha256(uri64.encode()).hexdigest()[:10]
    link = "{\"link\":\"" + uri64 + "\", \"digest\": \"" + str(digest) + "\" }"
    return link


def valid_token(incoming):
    status = WStatus(logger)
    valid_token = status.get_field('status', 'local_token')
    print(incoming)
    print(valid_token)
    return sanitize_str(incoming) == str(valid_token)


app = flask.Flask(__name__)
# app.config["DEBUG"] = False
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    return "Hello world"


@app.route('/api/v1/friends/usage/', methods=['GET', 'POST'])
def usage():
    if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
    if not valid_token(request.args.get('local_token')):
        return "Not allowed", http_status.HTTP_401_UNAUTHORIZED
    from flask import make_response
    from flask import jsonify

    services = Services(logger)
    usage_status = services.get_usage_daily()
    if request.args.get('certname'):
        try:
            usage_status = usage_status[request.args.get('certname')]
        except:
            usage_status = {}
            pass
    # print(usage_status)
    response = make_response(
        jsonify(usage_status),
        200,
    )
    response.headers["Content-Type"] = "application/json"
    return response


@app.route('/api/v1/friends/access_links/', methods=['GET', 'POST'])
def api_all():
    if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
    if valid_token(request.args.get('local_token')):
        return str(return_link(sanitize_str(request.args.get('certname'))))
    else:
        return "Not allowed", http_status.HTTP_401_UNAUTHORIZED


@app.route('/api/v1/claim/info', methods=['GET'])
def claim_info():
    if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
    status = WStatus(logger)
    serial_number = config.get('django', 'serial_number')
    is_claimed = status.get_field('status', 'claimed')
    if int(is_claimed) == 1:
        dev_key = "CLAIMED"
    else:
        dev_key = status.get_field('status', 'temporary_key')
    return "{\"claimed\":\"" + is_claimed + "\", \"serial_number\": \"" + str(serial_number) + \
        "\", \"device_key\":\"" + dev_key + "\"}"


@app.route('/api/v1/claim/progress', methods=['GET'])
def claim_progress():
    if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
    status = WStatus(logger)
    WPD = WPDiag(logger)
    wepn_available = WPD.is_connected_to_service()
    vpn_ready = WPD.services_self_test()
    is_claimed = status.get_field('status', 'claimed')
    if is_claimed == 1:
        WPD.perform_server_port_check(9999)
    port = False
    if status.get_field('port_check', 'result') == "True":
        port = True
    is_claimed = status.get_field('status', 'claimed')
    result = {"Can talk with WEPN Server": wepn_available,
              "Can forward ports": port,
              "VPN is ready": vpn_ready}
    return json.dumps(result)


@app.route('/api/v1/diagnostics/info', methods=['GET'])
def run_diag():
    if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
    if not valid_token(request.args.get('local_token')):
        return "Not accessible", http_status.HTTP_401_UNAUTHORIZED
    WPD = WPDiag(logger)
    device = Device(logger)
    local_ip = device.get_local_ip()
    port = 4091

    print('local ip=' + local_ip)

    internet = WPD.is_connected_to_internet()
    print('internet: ' + str(internet))
    service = WPD.is_connected_to_service()
    print('service: ' + str(service))
    error_code = WPD.get_error_code(port)
    print('device status code: ' + str(error_code))

    s_resp = WPD.get_server_diag_analysis(error_code)
    WPD.close_test_port(port)
    return str(s_resp)


@app.route('/api/v1/port_exposure/check', methods=['GET', 'POST'])
def check_port_available_externally():
    # A cron tries to access this path
    # if it is accessible from external IP then shut down
    # This API is not supposed to be externally accessible
    if not valid_token(request.args.get('local_token')):
        return "Not accessible", http_status.HTTP_401_UNAUTHORIZED
    global exposed
    exposed = True
    print("EXPOSED!!!!")
    return "ERROR: Exposure detected! APIs are closed now.", http_status.HTTP_503_SERVICE_UNAVAILABLE


@app.route('/api/v1/diagnostics/error_log', methods=['GET', 'POST'])
def get_error_log():
    # read the last two error logs
    # Note: while we emphasize not logging PII with logger.error(),
    # we can also add a regex based PII scanner like scrubadub here
    if exposed:
        return "Not accessible: API exposed to internet", http_status.HTTP_503_SERVICE_UNAVAILABLE
    # if not claimed, then just print the logs out
    # if claimed, then check credentials
    status = WStatus(logger)
    is_claimed = status.get_field('status', 'claimed')
    if int(is_claimed) == 1:
        if not valid_token(request.args.get('local_token')):
            return "Not accessible", http_status.HTTP_401_UNAUTHORIZED
    contents = ""
    try:
        with open(ERROR_LOG_FILE, 'r') as error_log:
            contents = error_log.read()
        with open(ERROR_LOG_FILE + ".1", 'r') as error_log:
            contents += error_log.read()
    except FileNotFoundError as err:
        print("Not enough logs, returning what was there" + str(err))
        pass
    return(contents)


if __name__ == '__main__':
    app.run(host='0.0.0.0',  # nosec: need all, https://go.we-pn.com/waiver-2
            ssl_context='adhoc')
