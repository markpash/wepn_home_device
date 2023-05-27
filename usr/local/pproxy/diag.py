import socket
import sys as system
import shlex
import subprocess  # nosec: shlex is used, go.we-pn.com/waiver-1
import json
import requests
import random
import threading
from device import Device
import time
import atexit
import datetime as datetime
from datetime import timedelta
import dateutil.parser
import os

try:
    from self.configparser import configparser
except ImportError:
    import configparser
from ipw import IPW
from wstatus import WStatus

ipw = IPW()

CONFIG_FILE = '/etc/pproxy/config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'


class WPDiag:

    def __init__(self, logger):
        self.logger = logger
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = WStatus(logger)
        self.claimed = self.status.get('claimed')
        self.iface = str(self.config.get('hw', 'iface'))
        self.port = 987
        self.mqtt_connected = 0
        self.mqtt_reason = 0
        self.device = Device(logger)
        self.listener = None
        self.shutdown_listener = False
        atexit.register(self.cleanup)

    def cleanup(self):
        self.shutdown_listener = True

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))

    def execute_cmd(self, cmd):
        try:
            args = shlex.split(cmd)
            subprocess.Popen(args)  # nosec: sanitized above, go.we-pn.com/waiver-1
        except Exception as error_exception:
            self.logger.error("Error happened in running command:" + cmd)
            self.logger.error("Error details:" + str(error_exception))
            system.exit()

    def open_listener(self, host, port):
        self.logger.debug("listener starting..." + str(port))
        start = int(time.time())
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)
        try:
            s.bind((host, int(port)))
        except OSError as err:
            self.logger.error("OSError in openning diag listener: " + str(err))
            return

        # this listener should die after one connection
        # if port forwarding does not work, it will stay alive, so
        # destructor will stop this thread
        s.listen(1)
        while not self.shutdown_listener:
            if int(time.time()) - start > 120:
                self.shutdown_listener = True
            self.logger.info('waiting ... ')
            conn, addr = s.accept()
            self.logger.info('Connected by ' + str(addr[0]))
            data = conn.recv(8)
            conn.sendall(data)
            conn.close()

    def open_test_port(self, port):
        self.shutdown_listener = False
        self.listener = threading.Thread(
            target=self.open_listener, args=['', port])
        self.listener.setDaemon(True)
        self.listener.start()
        return self.device.open_port(port=port,
                                     text='pproxy test port', timeout=1000)

    def close_test_port(self, port):
        self.shutdown_listener = True
        self.device.close_port(port)

    def is_connected_to_internet(self):
        urls = [
            "https://status.we-pn.com",
            "https://twitter.com",
            "https://google.com",
            "https://www.speedtest.net/",
            "https://www.cnn.com/",
            "https://bbc.co.uk",
        ]

        random.shuffle(urls)
        for url in urls:
            try:
                # connect to the host -- tells us if the host is actually
                # reachable
                requests.get(url)
                return True
            except:
                self.logger.exception("Could not connect to the internet")
        return False

    def is_connected_to_service(self):
        try:
            socket.create_connection(("www.we-pn.com", 443), 10)
            return True
        except OSError:
            return False
            pass

    # DEPRECATED
    # Getting to the extrenal port from the device itself is not reliable,
    # and many consumer routers lack the "route back" capability.
    # As a result, we use the server to run a test for us now
    def can_connect_to_external_port(self, port):
        try:
            external_ip = str(ipw.myip())
            self.logger.debug('Diag: external ip is ' + str(external_ip))
            s = socket.create_connection((external_ip, port), 10)
            s.sendall(b'test\n')
            return True
        except OSError as err:
            print(err)
            pass
            return False

    def request_port_check(self, port):
        experiment_num = 0
        headers = {"Content-Type": "application/json"}
        data = {
            "serial_number": self.config.get('django', 'serial_number'),
            "device_key": self.config.get('django', 'device_key'),
            "input": {"port": str(port), "experiment_name": "port_test",
                      "debug": str(self.device.igd_names)},
        }
        data_json = json.dumps(data)
        self.logger.debug("Port check data to send: " + data_json)
        url = self.config.get('django', 'url') + "/api/experiment/"
        try:
            response = requests.post(url, data=data_json, headers=headers)
            self.logger.debug(
                "Response to port check request" + str(response.status_code))
            resp = response.json()
            self.logger.error("response: \r\n\t" + str(resp))
            experiment_num = resp['id']
        except requests.exceptions.RequestException as exception_error:
            self.logger.error(
                "Error in sending portcheck request: \r\n\t" + str(exception_error))
            self.logger.error("response: \r\n\t" + str(resp))
        except KeyError as key_missing_err:
            self.logger.error(
                "Error in gettin the resonse: \r\n\t" + str(key_missing_err))
            self.logger.error("response: \r\n\t" + str(resp))
        return experiment_num

    def fetch_port_check_results(self, experiment_number):
        headers = {"Content-Type": "application/json"}
        data = {
            "serial_number": self.config.get('django', 'serial_number'),
            "device_key": self.config.get('django', 'device_key'),
        }
        data_json = json.dumps(data)
        url = self.config.get('django', 'url') + \
            "/api/experiment/" + str(experiment_number) + "/result/"
        try:
            response = requests.post(url, data=data_json, headers=headers)
            self.logger.info("server experiment results"
                             + str(response.status_code))
            self.logger.info(response.json())
            return response.json()
        except requests.exceptions.RequestException as exception_error:
            self.logger.error(
                "Error is parsing experiment results: " + str(exception_error))
            pass
        return

    # Method to get the results of a pending experiment from the server
    # True: keep waiting
    # False: got it done
    def get_results_from_server(self, port):
        result = self.fetch_port_check_results(
            self.status.get_field("port_check", "experiment_number"))
        try:
            if result['finished_time'] is not None:
                self.logger.info("test results are in")
                self.close_test_port(port)
                self.status.set_field("port_check", "pending", False)
                try:
                    self.status.set_field(
                        "port_check", "result", result['result']['experiment_result'])
                    self.status.set_field(
                        "port_check", "last_check", str(result['finished_time']))
                except:
                    self.logger.error(
                        "result from server did not contain actual results")
                    self.status.set_field("port_check", "result", False)
                    pass
                self.status.save()
                return False
            else:
                self.logger.info("still waiting for test results")
                return True
        except KeyError as key_err:
            self.logger.error(
                "Error in the results parsing: \t\r\n" + str(key_err))
            return False

    # This method is a big wrapper to take care of all port testing aspects
    # If a recent result is available, just skips doing anything
    # If an experiment is ongoing (pending), just try fetching results of that
    # If neither of above, try starting a new one
    def perform_server_port_check(self, port):

        if self.status.has_section("port_check"):
            last_port_check = self.status.get_field("port_check", "last_check")
            self.logger.info("last port check was " + str(last_port_check))
            last_check_date = dateutil.parser.parse(last_port_check)
            self.logger.info("last port check was " + str(last_check_date))

            long_term_expired = (last_check_date.replace(tzinfo=None) <
                                 (datetime.datetime.now().replace(tzinfo=None) + timedelta(days=-1)))
            short_term_expired = (last_check_date.replace(tzinfo=None) <
                                  (datetime.datetime.now().replace(tzinfo=None) + timedelta(hours=-2)))
            previous_failed = self.status.get_field(
                "port_check", "result") == "False"

            self.logger.info("pending test results? " +
                             self.status.get_field("port_check", "pending"))
            if not long_term_expired and self.status.get_field("port_check", "pending") == "True":
                # even if there is a pending one, but it's too old
                # then run a new experiment
                # if pending experiment is recent, just wait
                self.logger.debug(
                    "A test has been initiated previously, getting the results")
                self.get_results_from_server(port)
            elif long_term_expired or (previous_failed and short_term_expired):
                # results are too old, request a new one
                self.logger.info(
                    "port test results too old recently failed, retesting")
                # please note that the port opened here will be closed by either
                # (1) server successfully making a connection to it, or
                # (2) timing out
                # (3) a call to get_results_from_server. In theory 1 covers this too.
                self.open_test_port(port)
                time.sleep(2)
                experiment_number = self.request_port_check(port)
                if experiment_number > 0:
                    self.logger.debug(
                        "requesting new port check: " + str(experiment_number))
                    self.status.set_field("port_check", "pending", True)
                    self.status.set_field(
                        "port_check", "experiment_number", experiment_number)
                    self.status.save()
                else:
                    self.logger.error(
                        "HB request to start port check returned bad id 0")

                time.sleep(15)
                attempts = 0
                while self.get_results_from_server(port):
                    time.sleep(5)
                    attempts += 1
                    if attempts > 5:
                        # it is taking too long, let a future call retreive it
                        # the 'pending' status variable is used for this
                        break

    def can_connect_to_internal_port(self, port):
        # NOTE: if this is used, make sure there is an extra port listener
        # running. By default, only one connection will be handled.
        try:
            internal_ip = str(self.device.get_local_ip())
            self.logger.debug(
                'Diag connect internet: local ip is ' + str(internal_ip))
            s = socket.create_connection((internal_ip, port), 10)
            s.sendall(b'test\n')
            return True
        except OSError:
            pass
            return False

    # Each service runs its own selft test, this is true (=pass) if all services pass
    # for VPN services, it means connecting
    # to itself using the internal port and fetching a webpage
    def services_self_test(self):
        try:
            from services import Services
            services = Services(self.logger)
            return services.self_test()
        except:
            self.logger.exception("services self test error")
            return False

    def set_mqtt_state(self, is_connected, reason):
        self.mqtt_connected = is_connected
        self.mqtt_reason = reason

    # if you make changes here to the order of the flags, please
    # make sure the server side is also updated to reflect that
    def get_error_code(self, port_no):
        local_ip = self.device.get_local_ip()
        internet = self.is_connected_to_internet()
        service_connected = self.is_connected_to_service()
        service_test = self.services_self_test()
        mqtt = int(self.status.get('mqtt'))
        claimed = int(self.status.get('claimed'))
        # port check doesn't work when not claimed
        if claimed == 1:
            self.perform_server_port_check(port_no)
        port = 0
        if self.status.get_field('port_check', 'result') == "True":
            port = 1
        error_code = (local_ip != "" and local_ip != "127.0.0.1") + (internet << 1) + (service_connected << 2) + \
            (port << 3) + (mqtt << 4) + (service_test << 5) + (claimed << 6)
        # print(error_code)
        return error_code

    def get_server_diag_analysis(self, error_code):
        headers = {"Content-Type": "application/json"}
        data = {
            "device_code": error_code,
        }
        data_json = json.dumps(data)
        url = self.config.get('django', 'url') + "/api/device/diagnosis/"
        try:
            response = requests.post(url, data=data_json, headers=headers)
            self.logger.info("server diag analysis:" +
                             str(response.status_code))
            return response.json()
        except requests.exceptions.RequestException as exception_error:
            self.logger.error(
                "Error is parsing server's diag analysis: " + str(exception_error))
            pass

    def check_port_locally_in_use(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ret = sock.connect_ex(("127.0.0.1", port))
        if ret == 0:
            print("Port " + str(port) + " is open")  # Connected successfully
        else:
            # Failed to connect because port is in use (or bad host)
            print("Port " + str(port) + " is closedi: " + os.strerror(ret))
        sock.close()
        return (ret == 0)

    def check_port_in_blocked(self, port):
        # List of ports we do not want to be used,
        # even if they are currently free
        # This is useful for known "bad" ports, etc.
        # Later can turn into a separate list

        blocked = [5000, 9050, 9051, 9040, 8991]
        return (port in blocked)

    # this returns port, status.
    # status will be 0 if all is well, an integer if not

    def find_next_good_port(self, in_port):
        rport, errno = in_port, 0
        print(rport)
        self.logger.error("-----" + str(rport))
        retries = 0
        undecided = True
        # if no UPnP, then just return port
        if not self.device.check_port_mapping_igd():
            # don't bother
            return in_port, 404

        # if tried more than 10 ports and failed, just return port
        while retries < 10 and undecided:
            if retries == 5:
                # 5 blocked, skip 50
                rport += 50
            # if next port is in blocked, skip
            if self.check_port_in_blocked(rport):
                self.logger.error("Port %d is not allowed" % rport)
                rport += 1
                retries += 1
                errno = 1
                continue

            # if port is already open locally, skip
            if self.check_port_locally_in_use(rport):
                self.logger.error("Port %d is in use" % rport)
                rport += 1
                retries += 1
                errno = 2

            # if port is already forwarded for someone else, skip
            # if port cannot be forwarded, skip
            res = False
            pending = True
            fwd_result = self.open_test_port(rport)
            if fwd_result is False:
                self.logger.error("Error in port forwarding, skipping this port: " + str(rport))
                rport += 1
                retries += 1
                errno = 3
                continue

            experiment_number = self.request_port_check(rport)
            attempts = 0
            while pending:
                self.logger.error("Pending ..." + str(rport))
                result = self.fetch_port_check_results(experiment_number)
                if 'completed' in result.keys() and (str(result["completed"]) == "True"):
                    self.logger.info("Got results ..." + str(result))
                    pending = False
                    result = result["result"]
                    if 'experiment_result' in result.keys():
                        res = ("True" == str(result['experiment_result']))
                        # it could forward this port
                        if res:
                            self.logger.error("Success for port ..." + str(rport))
                            pending = False
                            undecided = False
                            errno = 0
                        else:
                            self.logger.error("Failed remote test for " + str(rport))
                            rport += 1
                            # go to the very beginnging of these tests for next port
                            # so exit this While loop
                            retries += 1
                            break
                attempts += 1
                if pending:
                    time.sleep(5)
                if attempts > 10:
                    rport += 1
                    retries += 1
                    pending = False
                    errno = 3
            self.logger.error("Closing port " + str(rport))
            self.close_test_port(rport)
        if retries > 10:
            # tried 10 different ports
            errno = 1010
            rport = in_port

        self.logger.error("Port: " + str(rport))
        return rport, errno
