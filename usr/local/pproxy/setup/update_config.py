import apt
#########################################
## Fix old setup files
## add missing fileds, correct host
#########################################
import configparser
CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'
PORT_STATUS_FILE='/var/local/pproxy/port.ini'

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
status = configparser.ConfigParser()
status.read(STATUS_FILE)
port_status = configparser.ConfigParser()
port_status.read(PORT_STATUS_FILE)

if not config.has_option('mqtt','host'):
   config.set('mqtt','host','we-pn.com')
   config.set('mqtt','onboard-timeout','10')
else:
   # some configs incorrectly have this
   # as api.we-pn.com
   config.set('mqtt','host','we-pn.com')


host = config.get('django','host')
if host == "we-pn.com":
   config.set('django','host','api.we-pn.com')

url = config.get('django','url')
if url == "we-pn.com" or url == "https://we-pn.com":
   config.set('django','url','https://api.we-pn.com')

if not config.has_option('openvpn','enabled'):
   config.set('openvpn','enabled', '1')
   config.set('openvpn','email', '0')

if not config.has_section('shadow'):
   config.add_section('shadow')
   config.set('shadow','enabled', '1')
   config.set('shadow','email', '1')
   config.set('shadow','conf_dir', '/var/local/pproxy/shadow/')
   config.set('shadow','conf_json', '/var/local/pproxy/shadow.json')
   config.set('shadow','db-path', '/var/local/pproxy/shadow.db')
   config.set('shadow','server-socket', '/var/local/pproxy/shadow/shadow.sock')
   config.set('shadow','method', 'aes-256-gcm')
   config.set('shadow','start-port', '4000')

if not config.has_section('usage'):
   config.add_section('usage')
   config.set('usage','db-path', '/var/local/pproxy/usage.db')


if not status.has_section('status'):
    status.add_section('status')
    status.set('status','claimed','0')
    status.set('status','state','1')
    status.set('status','mqtt','0')
    status.set('status','pin','00000000')
    status.set('status','mqtt-reason','0')

if not status.has_section('port_check'):
    status.add_section('port_check')
    status.set('port_check','last_check','2020-02-02 18:00:00.680749')
    status.set('port_check','pending','False')
    status.set('port_check','experiment_number','0')
    status.set('port_check','result','False')


if not port_status.has_section('port-fwd'):
    port_status.add_section('port-fwd')
    port_status.set('port-fwd','fails','0')
    port_status.set('port-fwd','fails-max','3')
    port_status.set('port-fwd','skipping','0')
    port_status.set('port-fwd','skips','0')
    port_status.set('port-fwd','skips-max','20')

if status.has_section('port-fwd'):
    status.remove_section('port-fwd')

# temporary re-update for an earlier bug
if config.has_option('email','enabled'):
    if config.get('email','enabled') == 'text':
        config.set('email', 'enabled', '1')

if not config.has_option('email','enabled'):
    config.set('email', 'enabled', '1')

if not config.has_option('email','type'):
    config.set('email', 'type', 'text')


config.set('email','email',"WEPN Device<devices@we-pn.com>")

if not config.has_option('mqtt','onboard-timeout'):
    config.set('mqtt','onboard-timeout', '10')

if not status.has_section('previous_keys'):
    status.add_section('previous_keys')

if not config.has_option('hw','iface'):
    config.set('hw','iface', 'eth0')

if (not config.has_option('hw','led-version') and
    not config.has_option('hw','lcd-version')):
    config.set('hw','led-version', '1')

if config.has_option('hw','led-version'):
    v = config.get('hw','led-version')
    config.set('hw','lcd-version', v)
    config.remove_option('hw','led-version')

if config.has_option('hw','led'):
    v = config.get('hw','led')
    config.set('hw','lcd', v)
    config.remove_option('hw','led')

if not config.has_option('hw','button-version'):
    config.set('hw','button-version', '1')

if not config.has_option('hw','disable-reboot') or True:
    # 7/8/2021: an earlier mistake means all device
    # have this set to disable
    # change back once all restored
    # meant only for development devices
    config.set('hw','disable-reboot', '0')

if not config.has_section('usage'):
    config.add_section('usage')
    config.set('usage','db-path', "/var/local/pproxy/usage.db")


if not config.has_section('dyndns'):
    config.add_section('dyndns')
    config.set('dyndns','enabled', "0")
    config.set('dyndns','username', "")
    config.set('dyndns','password', "")
    config.set('dyndns','hostname', "")
    config.set('dyndns','url', "https://{}:{}@domains.google.com/nic/update?hostname={}&myip={}")
    #config.set('dyndns','url', "http://{}:{}@dynupdate.no-ip.com/nic/update?hostname={}&myip={}")

# GCM is required, but older shadowsocks doesn't support it
cache = apt.Cache()
shadowsocks_3 = False
if cache['shadowsocks-libev'].is_installed:
    for pkg in cache['shadowsocks-libev'].versions:
        if pkg.version.startswith("3"):
            shadowsocks_3 = True
if shadowsocks_3:
    config.set('shadow','method', 'aes-256-gcm')
else:
    config.set('shadow','method', 'aes-256-cfm')

status.set('status','sw','1.3.9')


with open(CONFIG_FILE, 'w') as configfile:
   config.write(configfile)
with open(STATUS_FILE, 'w') as statusfile:
   status.write(statusfile)
with open(PORT_STATUS_FILE, 'w') as statusfile:
   port_status.write(statusfile)
