import apt
#########################################
## Fix old setup files
## add missing fileds, correct host
#########################################
try:
    from self.configparser import configparser
except ImportError:
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


if not port_status.has_section('port-fwd'):
    port_status.add_section('port-fwd')
    port_status.set('port-fwd','fails','0')
    port_status.set('port-fwd','fails-max','3')
    port_status.set('port-fwd','skipping','0')
    port_status.set('port-fwd','skips','0')
    port_status.set('port-fwd','skips-max','20')

if status.has_section('port-fwd'):
    status.remove_section('port-fwd')


if not config.has_option('email','enabled'):
    config.set('email', 'enabled', '1')

if not config.has_option('email','type'):
    config.set('email', 'enabled', 'text')

config.set('email','email',"WEPN Device<devices@we-pn.com>")

if not config.has_option('mqtt','onboard-timeout'):
    config.set('mqtt','onboard-timeout', '10')

if not self.status.has_section('previous_keys'):
    self.status.add_section('previous_keys')

if not config.has_option('hw','iface'):
    config.set('hw','iface', 'eth0')

if not config.has_section('usage'):
    config.add_section('usage')
    config.set('usage','db-path', "/var/local/pproxy/usage.db")


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

status.set('status','sw','0.15.0')


with open(CONFIG_FILE, 'w') as configfile:
   config.write(configfile)
with open(STATUS_FILE, 'w') as statusfile:
   status.write(statusfile)
with open(PORT_STATUS_FILE, 'w') as statusfile:
   port_status.write(statusfile)
