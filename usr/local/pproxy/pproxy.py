import json
import time
import ssl
import random
import requests
import os
import re
import atexit
import logging.config
import threading


try:
    from self.configparser import configparser
except ImportError:
    import configparser

import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import shlex
from ipw import IPW
import paho.mqtt.client as mqtt
from heartbeat import HeartBeat
from led_client import LEDClient
try:
    import RPi.GPIO as GPIO
    from pad4pi import rpi_gpio
    gpio_up = True
except Exception as err:
    print("Error in GPIO: " + str(err))
    gpio_up = False

from lcd import LCD as LCD
from diag import WPDiag
from services import Services
from device import Device
from wstatus import WStatus

COL_PINS = [26]  # BCM numbering
ROW_PINS = [19, 13, 6]  # BCM numbering
KEYPAD = [
    ["1", ], ["2", ], ["3"],
]
CONFIG_FILE = '/etc/pproxy/config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'
LOG_CONFIG = "/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)

ipw = IPW()


class PProxy():
    def __init__(self, logger=None):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.mqtt_connected = 0
        self.mqtt_reason = 0
        if gpio_up:
            GPIO.cleanup()
            if GPIO.getmode() != 11:
                GPIO.setmode(GPIO.BCM)
            self.factory = rpi_gpio.KeypadFactory()
        else:
            self.factory = None
        self.loggers = {}
        self.loggers["heartbeat"] = logging.getLogger("heartbeat")
        self.loggers["diag"] = logging.getLogger("diag")
        self.loggers["services"] = logging.getLogger("services")
        self.loggers["wstatus"] = logging.getLogger("wstatus")
        self.loggers["device"] = logging.getLogger("device")
        self.leds = LEDClient()
        atexit.register(self.cleanup)
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger("pproxy")
        self.status = WStatus(self.loggers['wstatus'])
        self.device = Device(self.loggers['device'])
        return

    def cleanup(self):
        self.logger.debug("PProxy shutting down.")
        self.leds.blank()
        if gpio_up:
            GPIO.cleanup()

    def set_logger(self, logger):
        self.logger = logger

    def set_loggers(self, index, logger):
        self.loggers[index] = logger

    def sanitize_str(self, str_in):
        return (shlex.quote(str_in))

    def save_state(self, new_state, lcd_print=1, hb_send=True):
        self.status.reload()
        self.status.set('state', new_state)
        self.status.save()
        if hb_send:
            self.logger.debug('heartbeat from save_state ' + new_state)
            heart_beat = HeartBeat(self.loggers["heartbeat"])
            heart_beat.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
            heart_beat.send_heartbeat(lcd_print)

    def process_key(self, key):
        services = Services(self.loggers['services'])
        if (key == "1"):
            current_state = self.status.get('state')
            if (current_state == "2"):
                new_state = "1"
                services.stop()
            else:
                new_state = "2"
                services.start()
            self.save_state(str(new_state))
        # Run Diagnostics
        elif (key == "2"):
            lcd = LCD()
            diag = WPDiag(self.loggers['diag'])
            lcd.set_lcd_present(self.config.get('hw', 'lcd'))
            display_str = [(1, "Starting Diagnostics", 0, "green"),
                           (2, "please wait ...", 0, "green")]
            lcd.display(display_str, 15)
            diag.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
            test_port = int(self.config.get('openvpn', 'port')) + 1
            display_str = [(1, "Status Code", 0, "blue"), (2, str(
                diag.get_error_code(test_port)), 0, "blue")]
            lcd.display(display_str, 20)
            time.sleep(3)
            serial_number = self.config.get('django', 'serial_number')
            display_str = [(1, "Serial #", 0, "blue"),
                           (2, serial_number, 0, "white"), ]
            lcd.display(display_str, 19)
            time.sleep(5)
            display_str = [(1, "Local IP", 0, "blue"),
                           (2, self.device.get_local_ip(), 0, "white"), ]
            self.logger.info(display_str)
            lcd.display(display_str, 19)
            time.sleep(5)
            display_str = [(1, "MAC Address", 0, "blue"),
                           (2, self.device.get_local_mac(), 0, "white"), ]
            self.logger.debug(display_str)
            lcd.display(display_str, 19)
            time.sleep(5)
            heart_beat = HeartBeat(self.loggers["heartbeat"])
            heart_beat.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
            self.logger.debug('heartbeat from process_key 2')
            heart_beat.send_heartbeat()
        # Power off
        elif (key == "3"):
            services.stop()
            lcd = LCD()
            lcd.set_lcd_present(self.config.get('hw', 'lcd'))
            display_str = [(1, "Powering down", 0, "red"), ]
            lcd.display(display_str, 15)
            time.sleep(2)
            self.save_state("0", 0)
            lcd.show_logo()
            display_str = [(1, "", 0, "black"), ]
            time.sleep(2)
            lcd.display(display_str, 20)
            self.device.turn_off()

    def get_messages(self):
        print("getting messages")
        url = "https://api.we-pn.com/api/message/"
        data = {
            "serial_number": self.config.get('django', 'serial_number'),
            "device_key": self.config.get('django', 'device_key'),
            "is_read": False,
            "destination": "DEVICE",
            "is_expired": False,
        }
        headers = {"Content-Type": "application/json"}
        data_json = json.dumps(data)
        print(data_json)
        response = requests.get(url, data=data_json, headers=headers)
        print(response.content)
        print(response.json())

    def send_mail(self, send_from, send_to,
                  subject, text, html, files_in,
                  server="127.0.0.1",
                  unsubscribe_link=None):
        if int(self.config.get('email', 'enabled')) == 0:
            # email is completely disabled
            self.logger.debug("Email feature is completely off.")
            return

        html_option = False
        if (self.config.has_option('email', 'type') and
                self.config.get('email', 'type') == 'html'):
            html_option = True
        self.logger.info("preparing email")
        if not isinstance(files_in, list):
            files_in_list = [files_in]
        else:
            files_in_list = files_in

        if html_option:
            msg = MIMEMultipart('alternative')
        else:
            msg = MIMEMultipart()

        msg['From'] = send_from
        msg['To'] = send_to
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        if unsubscribe_link is not None:
            msg.add_header('List-Unsubscribe',
                           '<' + unsubscribe_link + '>')
            msg.add_header('List-Unsubscribe-Post',
                           'List-Unsubscribe=One-Click')
            template = open("ui/emails_template.txt", "r")
            email_txt = template.read()
            template.close()
            email_txt = email_txt.replace("{{text}}", text)
            email_txt = email_txt.replace("{{unsubscribe_link}}", unsubscribe_link)
            part1 = MIMEText(email_txt, 'plain')
        else:
            part1 = MIMEText(text, 'plain')

        msg.attach(part1)

        if html_option:
            template = open("ui/emails_template.html", "r")
            email_html = template.read()

            template.close()
            email_html = email_html.replace("{{text}}", html)
            email_html = email_html.replace("{{unsubscribe_link}}", unsubscribe_link)

            part2 = MIMEText(email_html, 'html')
            msg.attach(part2)

        if files_in_list is not None:
            for file_in in files_in_list:
                # TODO: security check: check if file_in is safe
                if (file_in is not None):
                    with open(file_in, "rb") as current_file:
                        part = MIMEApplication(
                            current_file.read(),
                            Name=basename(file_in)
                        )
                        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(
                            file_in)
                        msg.attach(part)

        try:
            server = smtplib.SMTP(self.config.get('email', 'host'),
                                  self.config.get('email', 'port'))
            server.ehlo()
            server.starttls()
            server.login(self.config.get('email', 'username'),
                         self.config.get('email', 'password'))
            server.sendmail(send_from, send_to, msg.as_string())
            server.close()
            self.logger.info('successfully sent the mail')
        except Exception as error_exception:
            self.logger.error("failed to send mail: " + str(error_exception))

    # The callback for when the client receives a CONNACK response from the server.
    # if save_state takes too long, MQTT will disconnect so keep this function fast
    # and not blocking too long
    def on_connect(self, client, userdata, flags, result_code):
        self.logger.info("Connected with result code " + str(result_code))
        self.mqtt_connected = 1
        self.mqtt_reason = result_code
        self.status.reload()
        self.status.set('mqtt', 1)
        self.status.set('mqtt-reason', result_code)
        self.status.save()

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        # client.subscribe("$SYS/#")
        topic = "devices/" + self.config.get('mqtt', 'username') + "/#"
        self.logger.info('subscribing to: ' + topic)
        client.subscribe(topic, qos=1)
        self.logger.info('connected to service MQTT, saving state')
        self.leds.blank()
        # if device has too many friends,
        # sending heartbeat might take too long and make MQTT fail
        # hence the False parameter for hb_send
        # self.save_state("2", 1, False)
        th = threading.Thread(target=self.save_state, args=("2", 1))
        th.start()

    # prevent directory traversal attacks by checking final path

    def get_vpn_file(self, username):
        basedir = "/var/local/pproxy/"
        vpn_file = basedir + username + ".ovpn"
        if os.path.abspath(vpn_file).startswith(basedir):
            return vpn_file
        else:
            return None

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        self.logger.debug("on_message: " + msg.topic + " " + str(msg.payload))
        try:
            data = json.loads(msg.payload)
        except:
            data = json.loads(msg.payload.decode("utf-8"))
        th = threading.Thread(target=self.on_message_handler, args=(data,))
        th.start()

    def on_message_handler(self, data):
        services = Services(self.loggers['services'])
        unsubscribe_link = None
        send_email = True

        if ("uuid" in data and "subscribed" in data and "id" in data):
            us_id = self.sanitize_str(str(data['id']))
            if data['subscribed']:
                send_email = True
                us_flag = "false"
            else:
                send_email = False
                us_flag = "true"
            us_uuid = self.sanitize_str(data['uuid'])
            unsubscribe_link = "https://api.we-pn.com/api/friend/" + us_id + "/subscribe/?uuid=" \
                + us_uuid + "&subscribe=" + us_flag
            # print(unsubscribe_link)

        if (data['action'] == 'add_user'):
            username = self.sanitize_str(data['cert_name'])
            try:
                # extra sanitization to avoid path injection
                lang = re.sub(r'\\\\/*\.?', "",
                              self.sanitize_str(data['language']))
            except:
                lang = 'en'
            self.logger.debug("Adding user: " + username +
                              " with language:" + lang)
            ip_address = self.sanitize_str(ipw.myip())
            if self.config.has_section("dyndns") and self.config.getboolean('dyndns', 'enabled'):
                # we have good DDNS, lets use it
                self.logger.debug(self.config['dydns'])
                server_address = self.config.get("dydns", "hostname")
            else:
                server_address = ip_address
            password = random.SystemRandom().randint(1111111111, 9999999999)
            if 'passcode' in data and 'email' in data:
                if data['passcode'] and data['email']:
                    # TODO why re cannot remove \ even with escape?
                    # print("data=" + str(data))
                    data['passcode'] = re.sub(
                        r'[\\\\/*?:"<>|.]', "", data['passcode'][:25].replace("\n", ''))
                else:
                    send_email = False
            else:
                # if email not present or familiar phrase not set, no email!
                send_email = False
            port = self.config.get('shadow', 'start-port')
            try:
                is_new_user = services.add_user(
                    username, server_address, password, int(port), lang)
                if not is_new_user:
                    # getting an add for existing user? should be an ip change
                    self.logger.debug("Update IP")
                    self.device.update_dns(ip_address)
                txt, html, attachments, subject = services.get_add_email_text(
                    username, ip_address, lang, is_new_user)
            except:
                logging.exception("Error occured with adding user")

            self.logger.debug("add_user: " + txt)
            self.logger.debug("send_email?" + str(send_email))
            if send_email:
                self.send_mail(send_from=self.config.get('email', 'email'),
                               send_to=data['email'],
                               subject=subject,
                               text='The familiar phrase you have arranged with your friend is: ' +
                               data['passcode'] + '\n' + txt,
                               html='<p>The familiar phrase you have arranged with your friend is: <b>' +
                               data['passcode'] + '</b></p>' + html,
                               files_in=attachments,
                               unsubscribe_link=unsubscribe_link)

        elif (data['action'] == 'delete_user'):
            username = self.sanitize_str(data['cert_name'])
            if not username:
                self.logger.error("username to be removed was empty")
                return
            self.logger.debug("Removing user: " + username)
            ip_address = ipw.myip()
            services.delete_user(username)
            if send_email:
                self.send_mail(send_from=self.config.get('email', 'email'),
                               send_to=data['email'],
                               subject="Your VPN details",
                               # 'Familiar phrase is '+ data['passcode'] +
                               text='\nAccess to VPN server IP address ' + ip_address + ' is revoked.',
                               # '<p>Familiar phrase is <b>'+ data['passcode'] + '</b></p>'+
                               html="<p>Access to VPN server IP address <b>" + ip_address +
                                    "</b> is revoked.</p>",
                               files_in=None,
                               unsubscribe_link=None)  # at this point, friend is removed from backend db
        elif (data['action'] == 'reboot_device'):
            self.save_state("3")
            self.device.reboot()
        elif (data['action'] == 'start_service'):
            services.start_all()
            self.save_state("2")
        elif (data['action'] == 'stop_service'):
            services.stop_all()
            self.save_state("1")
        elif (data['action'] == 'restart_service'):
            services.restart_all()
        elif (data['action'] == 'reload_service'):
            services.reload_all()
        elif (data['action'] == 'update-pproxy'):
            self.device.update()
        elif (data['action'] == 'update-all'):
            self.device.update_all()
        elif (data['action'] == 'set_creds'):
            if (data['host']):
                self.config.set('email', 'host',
                                self.sanitize_str(data['host']))
            self.config.set('email', 'port', self.sanitize_str(data['port']))
            self.config.set('email', 'username',
                            self.sanitize_str(data['username']))
            self.config.set('email', 'email', self.sanitize_str(data['email']))
            self.config.set('email', 'password',
                            self.sanitize_str(data['password']))
            with open(CONFIG_FILE, 'w') as configfile:
                self.config.write(configfile)
        elif (data['action'] == 'wipe_device'):
            # very important action: make sure all VPN/ShadowSocks are deleted, and stopped
            # now reset the status bits
            self.status.reload()
            self.status.set('mqtt', 0)
            self.status.set('mqtt-reason', 0)
            self.status.set('claimed', 0)
            self.status.save()
            self.save_state("3")
            # reboot to go into onboarding
            self.device.reboot()
        elif (data['action'] == 'notification'):
            # get with serial and dev key from https://api.we-pn.com/api/message/
            # gives list of all messages for this device
            self.get_messages()

    # callback for diconnection of MQTT from server

    def on_disconnect(self, client, userdata, reason_code):
        self.logger.info("MQTT disconnected")
        self.leds.set_all(255, 145, 0)
        self.status.reload()
        self.mqtt_connected = 0
        self.mqtt_reason = reason_code
        self.status.set('mqtt', 0)
        self.status.set('mqtt-reason', reason_code)
        self.status.save()

    def start(self):
        lcd = LCD()
        lcd.set_lcd_present(self.config.get('hw', 'lcd'))
        lcd.show_logo()
        self.leds.set_all(0, 178, 16)
        services = Services(self.loggers['services'])
        services.start()
        time.sleep(5)
        client = mqtt.Client(self.config.get(
            'mqtt', 'username'), clean_session=False)
        self.logger.debug('HW config: button=' + str(int(self.config.get('hw', 'buttons'))) + '  LCD=' +
                          self.config.get('hw', 'lcd'))
        if (int(self.config.get('hw', 'buttons')) == 1 and
                int(self.config.get('hw', 'button-version')) == 1):
            try:
                keypad = self.factory.create_keypad(
                    keypad=KEYPAD, row_pins=ROW_PINS, col_pins=COL_PINS)
                keypad.registerKeyPressHandler(self.process_key)
            except RuntimeError as er:
                self.logger.critical("setting up keypad failed: " + str(er))
                if gpio_up:
                    GPIO.cleanup()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect
        client.tls_set("/etc/ssl/certs/ISRG_Root_X1.pem",
                       tls_version=ssl.PROTOCOL_TLSv1_2)
        client.username_pw_set(username=self.config.get('mqtt', 'username'),
                               password=self.config.get('mqtt', 'password'))
        self.logger.debug("mqtt host: " + str(self.config.get('mqtt', 'host')))
        try:
            client.connect(str(self.config.get('mqtt', 'host')),
                           int(self.config.get('mqtt', 'port')),
                           int(self.config.get('mqtt', 'timeout')))
            heart_beat = HeartBeat(self.loggers["heartbeat"])
            heart_beat.send_heartbeat(1)

        except Exception as error:
            self.logger.error("MQTT connect failed: " + str(error))
            display_str = [(1, chr(33) + '     ' + chr(33), 1, "red"),
                           (2, "Network error,", 0, "red"), (3, "check cable...", 0, "red")]
            lcd.display(display_str, 15)
            if (int(self.config.get('hw', 'buttons')) == 1):
                keypad.cleanup()
                if gpio_up:
                    GPIO.cleanup()
            raise
        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        client.loop_forever()
        if (int(self.config.get('hw', 'buttons'))):
            keypad.cleanup()
