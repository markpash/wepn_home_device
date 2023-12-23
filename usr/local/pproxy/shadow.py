import atexit
import base64
import hashlib
import json
import logging
import os
import shlex
import socket
import sqlite3 as sqli
import tempfile
import time
from datetime import datetime
from random import randrange  # nosec: not used for cryptography

import dataset
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from device import Device
from diag import WPDiag
from ipw import IPW
from service import Service

ipw = IPW()

CONFIG_FILE = '/etc/pproxy/config.ini'


class Shadow(Service):
    def __init__(self, logger):
        Service.__init__(self, "shadowsocks", logger)

        self.diag = WPDiag(logger)
        atexit.register(self.cleanup)
        fd, self.socket_path = tempfile.mkstemp()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(self.socket_path)
        except OSError:
            self.clear()
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(self.socket_path)
        try:
            self.sock.connect(self.config.get('shadow', 'server-socket'))
        except Exception as err:
            self.logger.error("Caught exception socket.error : %s" % err)

    def cleanup(self):
        self.clear()

    def clear(self):
        if os.path.isfile(self.socket_path):
            self.sock.shutdown(0)
            self.sock.close()
            os.remove(self.socket_path)

    def add_user(self, cname, ip_address, password, unused_port, lang):
        is_new_user = False
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        # get max of assigned ports, new port is 1+ that.
        # if no entry in DB, copy from config default port start
        servers = local_db['servers']
        server = servers.find_one(certname=cname)
        # if already exists, use same port
        # else assign a new port, 1+laargest existing
        if server is None:
            is_new_user = True
            try:
                results = local_db.query(
                    'select max(server_port) from servers')
                row = list(results)[0]
                max_port = row['max(server_port)']
            except:
                max_port = None
            if max_port is None:
                max_port = int(self.config.get('shadow', 'start-port'))
            port = max_port + 1
            port, err = self.diag.find_next_good_port(port)
            if err != 0:
                self.logger.error("Error while finding next good port: " + str(err))
        else:
            port = server['server_port']
            # also reuse the same password, making it easier for end user
            # to update the app manually if needed
            password = server['password']

        cmd = 'add : {"server_port": ' + \
            str(port) + ' , "password" : "' + str(password) + '" } '
        self.shadow_conf_file_save(port, password)
        self.sock.send(str.encode(cmd))
        self.shadow_conf_file_save(port, password)
        self.logger.debug("socket return: " + str(self.sock.recv(1056)))
        # open the port for this now
        self.logger.info('enabling port forwarding to port ' + str(port))
        device = Device(self.logger)
        device.open_port(port, 'ShadowSocks ' + cname)

        # add certname, port, password to a json list to use at delete/boot
        servers.upsert({'certname': cname, 'server_port': port, 'password': password, 'language': lang},
                       ['certname'])
        # retrun success or failure if file doesn't exist
        for a in local_db['servers']:
            self.logger.debug("server: " + str(a))
        local_db.commit()
        local_db.close()
        return is_new_user

    def del_user_usage(self, certname):
        conn = sqli.connect(self.config.get('usage', 'db-path'))
        cur = conn.cursor()
        if certname:
            try:
                cur.execute("delete from servers where certname like ?", [certname])
                cur.execute("delete from daily where certname like ?", [certname])
            except:
                self.logger.exception("Some error in deleting from usage")
        conn.commit()
        conn.close()

    def delete_user(self, cname):
        # stop the service for that cert
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        server = servers.find_one(certname=cname)
        if server is not None:

            port = server['server_port']
            cmd = 'remove : {"server_port": ' + str(server['server_port']) + ' } '
            self.sock.send(str.encode(cmd))
            self.logger.info("socket response to delete:"
                             + str(self.sock.recv(1056)))
            # add certname, port, password to a json list to ues at delete/boot
            servers.delete(certname=cname)
            self.logger.info('disabling port forwarding to port ' + str(port))
            device = Device(self.logger)
            device.close_port(port)
        self.del_user_usage(cname)
        # retrun success or failure if file doesn't exist
        if 0 and local_db is not None:
            for a in local_db['servers']:
                self.logger.debug("servers for delete: " + str(a))
        local_db.commit()
        local_db.close()
        return

    def shadow_conf_file_save(self, server_port, password):
        conf_json = ' {"server_port": ' + str(server_port) + ' ,\r\n "password" : "' +\
            str(password) + \
            '" , \r\n"mode":"tcp_and_udp", \r\n"nameserver":"8.8.8.8", \r\n"method":"' +\
            str(self.config.get('shadow', 'method')) +\
            '", \r\n "timeout":300, \r\n "workers":10} '
        shadow_file = '/usr/local/pproxy/.shadowsocks/.shadowsocks_' + \
            str(server_port) + '.conf'
        with open(shadow_file, 'w') as shadow_conf:
            shadow_conf.write(conf_json)
            shadow_conf.close()

    def start_server(self, server):
        device = Device(self.logger)
        device.open_port(server['server_port'],
                         'ShadowSocks ' + server['certname'])
        cmd = 'add : {"server_port": ' + \
            str(server['server_port']) + ' , "password" : "' + \
            str(server['password']) + '"} '
        # this is a workaround for the ss-manager/ss-server mismatch.
        # we force the mode in conf to be string, not int
        # once the ss-manager is updated from source, remove this workaround
        self.shadow_conf_file_save(
            server['server_port'], server['password'])
        self.sock.send(str.encode(cmd))
        self.shadow_conf_file_save(
            server['server_port'], server['password'])
        self.logger.debug(cmd + ' >> ' + str(self.sock.recv(1056)))

    def start_all(self):
        # used at boot time
        # loop over cert files, start each
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        if len(servers) == 0:
            return
        for server in local_db['servers']:
            time.sleep(1)
            self.start_server(server)
        return

    def stop_all(self):
        # used at service stop time
        # loop over cert files, stop all
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        try:
            if not servers:
                self.logger.info('no servers')
                return
            for server in local_db['servers']:
                cmd = 'remove : {"server_port": ' + str(server['server_port']) + ' } '
                self.sock.send(str.encode(cmd))
                self.logger.debug(
                    server['certname'] + ' >>' + cmd + ' >> ' + str(self.sock.recv(1056)))
            return
        except Exception:
            return
    # forward_all is used with cron to make sure port forwardings stay active
    # if service is stopped, forwardings can stay active. there will be no ss server to serve

    def forward_all(self):
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        device = Device(self.logger)
        try:
            if not servers:
                self.logger.info('no servers')
                return
            for server in local_db['servers']:
                self.logger.debug(
                    'forwaring ' + str(server['server_port']) + ' for ' + server['certname'])
                device.open_port(server['server_port'],
                                 'ShadowSocks ' + server['certname'])
            return
        except Exception:
            return

    def start(self):
        self.start_all()
        return

    def stop(self):
        self.stop_all()
        return

    def get_service_creds_summary(self, ip_address):
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        creds = {}
        if not servers or not self.is_enabled():
            self.logger.debug("No servers found for access creds")
            return {}
        for server in local_db['servers']:
            if server['certname'] == "''" or not server['certname']:
                self.logger.error("Certname is empty, skipping")
                continue
            self.logger.debug("creds for " + server['certname'])
            uri = str(self.config.get('shadow', 'method')) + ':' + str(
                server['password']) + '@' + str(ip_address) + ':' + str(server['server_port'])
            uri64 = 'ss://' + \
                base64.urlsafe_b64encode(str.encode(uri)).decode(
                    'utf-8') + "#WEPN-" + str(server['certname'])
            creds[server['certname']] = hashlib.sha256(
                uri64.encode()).hexdigest()[:10]
        return creds

    # TODO: this function is still a copy of creds, and needs work
    def get_usage_json(self):
        self.logger = logging.getLogger(__name__)
        # get usage statistics from ss-manager
        cmd = 'ping'
        self.logger.debug(cmd)
        self.sock.send(str.encode(cmd))
        # ping response has some text, remove it
        raw_str = str(self.sock.recv(1056)).replace(
            "b'stat:", "").replace("'", "")
        self.logger.debug(raw_str)
        response = json.loads(raw_str)
        return response

    def get_access_link(self, cname):
        local_db = dataset.connect('sqlite:///' + self.config.get('shadow', 'db-path'))
        ipw = IPW()
        ip_address = shlex.quote(ipw.myip())
        if self.config.has_section("dyndns") and self.config.getboolean('dyndns', 'enabled'):
            # we have good DDNS, lets use it
            server_address = self.config.get("dyndns", "hostname")
        else:
            server_address = ip_address
        servers = local_db['servers']
        server = servers.find_one(certname=cname)
        uri = "unknown"
        uri64 = "empty"
        digest = ""
        link = None
        if server is not None:
            uri = str(self.config.get('shadow', 'method')) + ':' + \
                str(server['password']) + '@' + str(server_address) + ':' + str(server['server_port'])
            uri64 = 'ss://' + \
                base64.urlsafe_b64encode(str.encode(uri)).decode(
                    'utf-8') + "#WEPN-" + str(server['certname'])
            digest = hashlib.sha256(uri64.encode()).hexdigest()[:10]
            link = "{\"type\":\"shadowsocks\", \"link\":\"" \
                + uri64 + "\", \"digest\": \"" + str(digest) + "\" }"
        local_db.close()
        return link

    def get_usage_status_summary(self):
        self.logger = logging.getLogger(__name__)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        self.logger.addHandler(ch)

        self.logger.debug("---summary -----")
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        usage_results = {}
        if not servers or not self.is_enabled():
            self.logger.debug("No servers found for usage")
            return {}
        # get usage statistics from ss-manager
        cmd = 'ping'
        self.logger.debug(cmd)
        self.sock.send(str.encode(cmd))
        # ping response has some text, remove it
        raw_str = str(self.sock.recv(1056)).replace(
            "b'stat:", "").replace("'", "")
        self.logger.debug(raw_str)
        response = json.loads(raw_str)
        usage_db = dataset.connect(
            'sqlite:///' + self.config.get('usage', 'db-path'))

        usage_servers = usage_db['servers']
        usage_daily = usage_db['daily']
        usage_status = -1
        for server in servers:
            if server['certname'] == "''" or not server['certname']:
                self.logger.error("Certname is empty, skipping")
                continue
            self.logger.debug("current server name is " + server['certname'])
            try:
                usage_value = -1
                usage_server = None
                usage_status = -1
                current_usage = 0
                server_name = str(server['server_port'])
                if server_name in response:
                    current_usage = response[server_name]
                    self.logger.debug("port=" + str(server['server_port']) +
                                      " usage=" + str(response[str(server['server_port'])]))
                    usage_server = usage_servers.find_one(
                        certname=server['certname'])
                if usage_server is None or usage_server['usage'] is None or 'usage' not in usage_server:
                    # not yet in the database
                    usage_value = current_usage
                    self.logger.debug(
                        "Usage not in db yet. value=" + str(usage_value))
                else:
                    self.logger.debug(
                        "Current usage in db = " + str(usage_server['usage']))

                    # already has some value in usage db
                    if usage_server['usage'] > current_usage:
                        # wrap around, device recently rebooted?
                        print("usage value has gone down!!")
                        usage_value = current_usage + usage_server['usage']
                        # some of the data usage is lost, but we get the estimate
                    else:
                        # not a wrap around, just replace
                        usage_value = current_usage
                        # how many bytes used since last update
                        # delta = current_usage - usage_server['usage']
                self.logger.debug("usage value = " + str(usage_value))
                if usage_value > 0:
                    usage_status = 1
                self.logger.debug('certname:' + server['certname'] +
                                  ' server_port:' + str(server['server_port']) +
                                  ' usage:' + str(usage_value) +
                                  ' status:' + str(usage_status))
                today = datetime.today().strftime('%Y-%m-%d')
                usage_today = usage_daily.find_one(
                    certname=server['certname'], date=today)
                if usage_today is None:
                    self.logger.info("New day")
                    # this is a new day, start is 0
                    usage_daily.upsert({'certname': server['certname'],
                                        'date': today,
                                        'start_usage': usage_value,
                                        'server_port': server['server_port'],
                                        'type': 'shadow',
                                        'end_usage': usage_value}, ['certname', 'date'])
                else:
                    # wrap around/restart has happened
                    if usage_today['end_usage'] < usage_value:
                        # we have lost some data probably, don't overwrite
                        # the last end with this one.
                        # set start to 0, end to a fake adjustment
                        past_delta = usage_today['end_usage'] - \
                            usage_today['start_usage']
                        fake_start = usage_value - past_delta
                        usage_daily.upsert({'certname': server['certname'],
                                            'date': today,
                                            'server_port': server['server_port'],
                                            'start_usage': fake_start,
                                            'type': 'shadow',
                                            'end_usage': usage_value}, ['certname', 'date'])
                        print("wrap around: " + str(fake_start))
                    else:
                        # all is normal, just update the end
                        usage_daily.upsert({'certname': server['certname'],
                                            'date': today,
                                            'server_port': server['server_port'],
                                            'type': 'shadow',
                                            'end_usage': usage_value}, ['certname', 'date'])
                # this one is for the overall usage, used for "usage status"
                usage_servers.upsert({'certname': server['certname'],
                                      'server_port': server['server_port'],
                                      'usage': usage_value,
                                      'status': usage_status}, ['certname'])
                usage_results[server['certname']] = usage_status

            except KeyError as e:
                self.logger.error("Port not found in ping stats: " + str(e))
        return usage_results

    def get_usage_daily(self):
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        usage_db = dataset.connect(
            'sqlite:///' + self.config.get('usage', 'db-path'))
        usage_daily = usage_db['daily']
        days = {}
        for server in servers:
            usage_days = usage_daily.find(certname=server['certname'])
            for day in usage_days:
                try:
                    if day['end_usage'] < day['start_usage']:
                        # some information is lost here, better than negative
                        if day['end_usage'] == 0:
                            # we lost the ending data
                            use = day['start_usage']
                        else:
                            use = day['end_usage']
                    else:
                        use = day["end_usage"] - day["start_usage"]
                except:
                    use = 0
                    pass
                if day['certname'] not in days:
                    days[day['certname']] = []
                days[day['certname']].append({  # "certname":day["certname"],
                    "date": day["date"],
                    "usage": use})
        local_db.close()
        return days

    def get_short_link_text(self, cname, ip_address):
        uri64 = ""
        count = 0
        while count < 5:
            local_db = dataset.connect(
                'sqlite:///' + self.config.get('shadow', 'db-path'))
            servers = local_db['servers']
            server = servers.find_one(certname=cname)
            if server is not None:
                uri = str(self.config.get('shadow', 'method')) + ':' + str(
                    server['password']) + '@' + str(ip_address) + ':' + str(server['server_port'])
                uri64 = 'ss://' + \
                        base64.urlsafe_b64encode(str.encode(uri)).decode(
                            'utf-8') + "#WEPN-" + str(cname)
                return uri64
            else:
                count += 1
        return uri64

    def get_add_email_text(self, cname, ip_address, lang, tunnel="all", is_new_user=False):
        txt = ''
        html = ''
        manuals = []
        subject = ''
        if self.is_enabled() and self.can_email():
            uri64 = self.get_short_link_text(cname, ip_address)
            if uri64 is not None:
                manuals = ['/usr/local/pproxy/ui/' + lang + '/outline.png',
                           '/usr/local/pproxy/ui/' + lang + '/potatso.png']
                subject = "Your New VPN Access Details"
                if not is_new_user:
                    txt = "You have been granted access to a private VPN server. "
                    txt += 'This VPN server uses Shadowsocks server. To start using this service:'
                    html = "<h2>You have been granted access to a private VPN server.</h2>"
                    html += 'This VPN server uses Shadowsocks server. To start using this service, '
                else:
                    txt = "Your access link to the private VPN server is updated."
                    txt += "This might be due to an IP change, among other reasons."
                    html = "<h2>Your access link to the private VPN server is updated.</h2>"
                    html += "This might be due to an IP change, among other reasons."
                    subject = "Update to  Your VPN Access Details"
                txt += '\n\n1. Copy the below text, \n2. Open Outline or ShadowSocks apps on your phone \n3. '
                txt += 'Import this link as a new server. \n\n'
                txt += uri64
                txt += '\n\n You can use either the Outline app (Android/iPhone/Windows) or'
                txt += ' Potatso (iPhone). These apps are independent and not affiliated with WEPN team.'
                txt += '\nGraphical manuals are attached to this email.'
                html += '<ul> <li>Copy the below text, </li><li> Open Outline or ShadowSocks apps on '
                html += 'your phone </li><li> Import this link as a new server. </li></ul><br /><br/>'
                html += "<center><b>" + uri64 + "</b></center>"
                html += '<p>You can use either the Outline app (Android/iPhone/Windows) or Potatso (iPhone). '
                html += 'These apps are independent and not affiliated with WEPN team.<br/>'
                html += 'Graphical manuals are attached to this email.</p>'
            else:
                # Error: User not found in shadowsocks?
                txt = ""
                html = txt
        return txt, html, manuals, subject

    def get_removal_email_text(self, certname, ip_address, lang):
        txt = ''
        html = ''
        if self.is_enabled() and self.can_email():
            txt = "Access to VPN server IP address " + ip_address + " is revoked.",
            html = "Access to VPN server IP address " + ip_address + " is revoked.",
        return txt, html

    def get_max_port(self):
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        # get max of assigned ports
        # if no entry in DB, copy from config default port start
        try:
            results = local_db.query('select max(server_port) from servers')
            row = list(results)[0]
            max_port = row['max(server_port)']
        except:
            max_port = None
        if max_port is None:
            max_port = int(self.config.get('shadow', 'start-port'))
        return max_port

    def recover_missing_servers(self):
        pid_missing = True
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        if not servers:
            self.logger.debug('no servers for recovery')
            return True
        device = Device(self.logger)
        for server in local_db['servers']:
            self.logger.debug("recovery checking server:" + str(server['server_port']))
            pid_file_ = '/usr/local/pproxy/.shadowsocks/.shadowsocks_' + \
                str(server['server_port']) + '.pid'
            try:
                pid_file = open(pid_file_, 'r')
                pid = int(pid_file.read())
                pid_file.close()
                pid_missing = False
            except:
                pid = -1
                pid_missing = True
            if pid_missing or not device.is_process_running_pid(pid):
                self.logger.debug("recovery starting server:" + str(server['server_port']))
                self.start_server(server)

    def self_test(self):
        success = True
        local_port = 10000 + randrange(10)  # nosec: not used for cryptography
        local_db = dataset.connect(
            'sqlite:///' + self.config.get('shadow', 'db-path'))
        servers = local_db['servers']
        if not servers:
            # if no entry in DB, just return true. No fail is a pass
            self.logger.info('no servers for self test')
            return True
        device = Device(self.logger)
        try:

            local_down = False
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
            try:
                res = requests.get('https://127.0.0.1:5000/',
                                   verify=False, timeout=3)  # nosec: local cert, http://go.we-pn.com/waiver-3
            except requests.exceptions.SSLError:
                local_down = True
                pass
            except requests.exceptions.ReadTimeout:
                local_down = True
                pass
            if res.status_code != 200 or local_down:
                # the local flask API server is down, so all of these tests will fail
                # TODO: this is not a real shadowsocks error, so need a way to convey and recover
                self.logger.error("Local server is down")
                return False
        except:
            return False
        for server in local_db['servers']:
            self.logger.debug("testing :" + str(server['server_port']))
            local_port += 1
            ss_client_cmd = "ss-local -s 127.0.0.1 -p {} -l {} -k {} -m {} ".format(
                server['server_port'],
                str(local_port),
                server['password'],
                self.config.get('shadow', 'method'))
            proxies = {'https': "socks5://localhost:" + str(local_port)}
            try:
                ss_out, err, failed, ss_process = device.execute_cmd_output(
                    ss_client_cmd, True)
                time.sleep(3)
                if int(failed) == 0:
                    r = requests.get('http://connectivity.we-pn.com/',
                                     timeout=5,
                                     proxies=proxies)
                    success &= (r.status_code == 200)
            except requests.exceptions.ReadTimeout:
                self.logger.info("Timedout: \t" + str(server))
                success = False
            except:
                self.logger.info("Error in self test:>\t:" + str(server))
                success = False
            if ss_process:
                ss_process.kill()
        return success
