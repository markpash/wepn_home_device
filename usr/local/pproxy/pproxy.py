import atexit
import json
import logging.config
import os
import random
import re
import ssl
import time
from threading import Lock, Thread

try:
    from configparser import configparser
except ImportError:
    import configparser

import shlex
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from os.path import basename

import paho.mqtt.client as mqtt

from heartbeat import HeartBeat
from ipw import IPW
from led_client import LEDClient

try:
    import RPi.GPIO as GPIO
    from pad4pi import rpi_gpio
    gpio_up = True
except Exception as err:
    print("Error in GPIO: " + str(err))
    gpio_up = False

from constants import LOG_CONFIG
from device import Device
from diag import WPDiag
from lcd import LCD as LCD
from messages import Messages
from services import Services
from wstatus import WStatus

COL_PINS = [26]  # BCM numbering
ROW_PINS = [19, 13, 6]  # BCM numbering
KEYPAD = [
    ["1", ], ["2", ], ["3"],
]
CONFIG_FILE = '/etc/pproxy/config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)

ipw = IPW()


class PProxy():
    def __init__(self, logger=None):
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.mqtt_connected = 0
        self.mqtt_reason = 0
        self.mqtt_pending_notifications = []
        self.rest_not_pending_mqtt = []
        self.loggers = {}
        if logger is not None:
            self.logger = logger
            self.loggers["heartbeat"] = logger
            self.loggers["diag"] = logger
            self.loggers["services"] = logger
            self.loggers["wstatus"] = logger
            self.loggers["device"] = logger
        else:
            self.logger = logging.getLogger("pproxy")
            self.loggers["heartbeat"] = logging.getLogger("heartbeat")
            self.loggers["diag"] = logging.getLogger("diag")
            self.loggers["services"] = logging.getLogger("services")
            self.loggers["wstatus"] = logging.getLogger("wstatus")
            self.loggers["device"] = logging.getLogger("device")
        if gpio_up:
            GPIO.cleanup()
            if GPIO.getmode() != 11:
                GPIO.setmode(GPIO.BCM)
            self.factory = rpi_gpio.KeypadFactory()
        else:
            self.factory = None
        self.leds = LEDClient()
        atexit.register(self.cleanup)
        self.status = WStatus(self.loggers['wstatus'])
        self.device = Device(self.loggers['device'])
        self.mqtt_lock = Lock()
        self.lcd = None
        self.messages = Messages()
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

    def save_state(self, new_state, lcd_print=0, hb_send=True):
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
            diag = WPDiag(self.loggers['diag'])
            self.lcd.set_lcd_present(self.config.get('hw', 'lcd'))
            display_str = [(1, "Starting Diagnostics", 0, "green"),
                           (2, "please wait ...", 0, "green")]
            self.lcd.display(display_str, 15)
            diag.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
            test_port = int(self.config.get('openvpn', 'port')) + 1
            display_str = [(1, "Status Code", 0, "blue"), (2, str(
                diag.get_error_code(test_port)), 0, "blue")]
            self.lcd.display(display_str, 20)
            time.sleep(3)
            serial_number = self.config.get('django', 'serial_number')
            display_str = [(1, "Serial #", 0, "blue"),
                           (2, serial_number, 0, "white"), ]
            self.lcd.display(display_str, 19)
            time.sleep(5)
            display_str = [(1, "Local IP", 0, "blue"),
                           (2, self.device.get_local_ip(), 0, "white"), ]
            self.logger.info(display_str)
            self.lcd.display(display_str, 19)
            time.sleep(5)
            display_str = [(1, "MAC Address", 0, "blue"),
                           (2, self.device.get_local_mac(), 0, "white"), ]
            self.logger.debug(display_str)
            self.lcd.display(display_str, 19)
            time.sleep(5)
            heart_beat = HeartBeat(self.loggers["heartbeat"])
            heart_beat.set_mqtt_state(self.mqtt_connected, self.mqtt_reason)
            self.logger.debug('heartbeat from process_key 2')
            heart_beat.send_heartbeat()
        # Power off
        elif (key == "3"):
            services.stop()
            self.lcd.set_lcd_present(self.config.get('hw', 'lcd'))
            display_str = [(1, "Powering down", 0, "red"), ]
            self.lcd.display(display_str, 15)
            time.sleep(2)
            self.save_state("0", 0)
            self.lcd.show_logo()
            display_str = [(1, "", 0, "black"), ]
            time.sleep(2)
            self.lcd.display(display_str, 20)
            self.device.turn_off()

    def get_messages(self):
        self.logger.debug("getting messages")
        messages = Messages()

        # loop through the message array, process them one by one.
        for message in messages.get_messages():
            id = int(message["id"])
            self.logger.info("message ID processing: " + str(id))
            '''
            fake_msg = mqtt.MQTTMessage()
            fake_msg._topic = b"REST"
            fake_msg.payload = json.dumps(message["message_body"]).encode('utf-8')
            self.logger.debug(fake_msg.payload.decode("utf-8"))
            self.on_message("", "", fake_msg)
            '''
            if id in self.mqtt_pending_notifications:
                self.mqtt_pending_notifications.remove(id)
            else:
                self.logger.info("REST arrived earlier than MQTT")
                self.rest_not_pending_mqtt.append(id)
            self.logger.info(self.mqtt_pending_notifications)
            self.logger.info(self.rest_not_pending_mqtt)
            th = Thread(target=self.on_message_handler, args=(message["message_body"], self.mqtt_lock))
            th.start()
            messages.mark_msg_read(id)
            self.logger.info("message ID processed: " + str(id))

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
        self.leds.blink(color=(0, 255, 0), wait=500, repetitions=1)
        self.leds.blank()
        # if device has too many friends,
        # sending heartbeat might take too long and make MQTT fail
        # hence the False parameter for hb_send
        # self.save_state("2", 1, False)
        th = Thread(target=self.save_state, args=("2"))
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
        except BaseException:
            self.logger.exception("message was:" + msg + " + payload: " + msg.payload)
            data = json.loads(msg.payload.decode("utf-8"))
            self.logger.exception("on_message: except")
        th = Thread(target=self.on_message_handler, args=(data, self.mqtt_lock))
        th.start()
        self.logger.debug("after starting the thread for on_message")

    def on_message_handler(self, data, lock):
        services = Services(self.loggers['services'])
        unsubscribe_link = None
        send_email = True
        self.logger.debug(data)

        if ("uuid" in data and "subscribed" in data and "id" in data):
            us_id = self.sanitize_str(str(data['id']))
            if data['subscribed']:
                send_email = True
                us_flag = "false"
            else:
                send_email = False
                us_flag = "true"
            us_uuid = self.sanitize_str(data['uuid'])
            unsubscribe_link = self.config.get('django', 'url') + "/api/friend/" + us_id + "/subscribe/?uuid=" \
                + us_uuid + "&subscribe=" + us_flag
            # print(unsubscribe_link)

        if (data['action'] == 'add_user'):
            txt = None
            try:
                self.logger.debug("before lock acquired")
                # light up ring LEDs in blue with fill pattern
                self.leds.spinning_wheel(color=(0, 0, 255),
                                         length=1,
                                         repetitions=100)
                lock.acquire()
                self.logger.debug("lock acquired")
                username = self.sanitize_str(data['cert_name'])
                if "tunnel" in data["config"]:
                    tunnel = data["config"]["tunnel"]
                else:
                    tunnel = "all"
                try:
                    # extra sanitization to avoid path injection
                    lang = re.sub(r'\\\\/*\.?', "",
                                  self.sanitize_str(data['language']))
                except BaseException:
                    lang = 'en'
                self.logger.debug("Adding user: " + username +
                                  " with language:" + lang + " to " + tunnel)
                ip_address = self.sanitize_str(ipw.myip())
                if self.config.has_section(
                        "dyndns") and self.config.getboolean('dyndns', 'enabled'):
                    # we have good DDNS, lets use it
                    server_address = self.config.get("dyndns", "hostname")
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
                        username, server_address, password, int(port), tunnel, lang)
                    if not is_new_user:
                        # getting an add for existing user? should be an ip change
                        self.logger.debug("Update IP")
                        self.device.update_dns(ip_address)
                    else:
                        # light up ring LEDs in blue with fill pattern
                        self.leds.fill_upto(color=(0, 0, 255),
                                            percentage=1,
                                            wait=50)
                    txt, html, attachments, subject = services.get_add_email_text(
                        username, server_address, lang, tunnel, is_new_user)
                except BaseException:
                    logging.exception("Error occured with adding user")
                    # blink led ring red for 6 times if add friend fails
                    self.leds.blink(color=(255, 0, 0),
                                    wait=200,
                                    repetitions=6)

                if txt is not None:
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
                    # alse send a message to the app via Messaging API
                    self.messages.send_msg(txt, cert_id=username, secure=True)

            except BaseException:
                self.logger.exception("Unhandled exception adding friend")
            finally:
                self.logger.debug("before lock released")
                lock.release()
                self.logger.debug("lock released")

        elif (data['action'] == 'delete_user'):
            username = self.sanitize_str(data['cert_name'])
            if not username:
                self.logger.error("username to be removed was empty")
                return
            self.logger.debug("Removing user: " + username)
            ip_address = ipw.myip()
            try:
                # show a blue led ring fill down pattern when
                # deleting a friend
                self.leds.fill_downfrom(color=(0, 0, 255),
                                        percentage=1,
                                        wait=50)
                services.delete_user(username)
            except BaseException:
                self.logger.exception("delete friend failed!")
                # blink led red for 5 times if exception happens
                # during delete friend
                self.leds.blink(color=(255, 0, 0),
                                wait=50,
                                repetitions=5)
            if send_email and 'email' in data.keys() and data['email'] is not None:
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

        elif (data['action'] == 'set_ddns'):
            for item in ['enabled', 'hostname', 'url', 'username', 'password']:
                if (item in data):
                    self.config.set('dyndns', item,
                                    self.sanitize_str(data[item]))
            with open(CONFIG_FILE, 'w') as configfile:
                self.config.write(configfile)
        elif (data['action'] == 'config_service'):
            # TODO: these might require sanitization
            service_name = self.sanitize_str(data["service_name"])
            config = data["config"]
            services.configure(service_name, config)
        elif (data['action'] == 'wipe_device'):
            # very important action: make sure all VPN/ShadowSocks are deleted, and stopped
            # now reset the status bits
            # set led ring color to solid yellow
            self.leds.blink(color=(255, 255, 0), wait=250, repetitions=6)
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
            id = data["message_id"]
            if id not in self.rest_not_pending_mqtt:
                self.mqtt_pending_notifications.append(data["message_id"])
                self.logger.info("MQTT arrived earlier than REST")
            else:
                self.rest_not_pending_mqtt.remove(id)
                self.logger.info("REST arrived earlier than MQTT")
            self.get_messages()

    # callback for diconnection of MQTT from server

    def on_disconnect(self, client, userdata, reason_code):
        self.logger.info("MQTT disconnected")
        # show solid yellow ring indicating MQTT has been
        # disconnected from server
        self.leds.pulse(color=(255, 255, 0),
                        wait=50,
                        repetitions=50)
        self.status.reload()
        self.mqtt_connected = 0
        self.mqtt_reason = reason_code
        self.status.set('mqtt', 0)
        self.status.set('mqtt-reason', reason_code)
        self.status.save()

    def start(self):
        self.lcd = LCD()
        self.lcd.set_lcd_present(self.config.get('hw', 'lcd'))
        # show a white spinning led ring
        # self.leds.set_all(color=(255, 255, 255))
        self.leds.spinning_wheel(color=(255, 255, 255),
                                 length=6,
                                 wait=50,
                                 repetitions=100)
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
            heart_beat.send_heartbeat()

        except Exception as error:
            self.logger.error("MQTT connect failed: " + str(error))
            self.lcd.long_text("Connection to server disrupted, please check cable.")
            if (int(self.config.get('hw', 'buttons')) == 1) and \
                    (int(self.config.get('hw', 'button-version')) == 1):
                keypad.cleanup()
                if gpio_up:
                    GPIO.cleanup()
            raise
        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        client.loop_forever()
        if (int(self.config.get('hw', 'buttons'))):
            keypad.cleanup()
