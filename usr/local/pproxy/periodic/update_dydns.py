import requests
try:
    from self.configparser import configparser
except ImportError:
    import configparser
CONFIG_FILE = '/etc/pproxy/config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

if config.has_section("dyndns") and config.getboolean('dyndns', 'enabled'):
    # we have good DDNS, lets use it
    #self.logger.debug(self.config['dydns'])
    server_address = config.get("dyndns", "url")
    url = server_address.format(
            config.get("dyndns", "username"),
            config.get("dyndns", "password"),
            config.get("dyndns", "hostname"))

    headers = requests.utils.default_headers()

    headers.update(
        {
            'User-Agent': 'WEPN/3 support@we-pn.com',
        }
    )

    response = requests.get(url, headers=headers)
    print(response)
