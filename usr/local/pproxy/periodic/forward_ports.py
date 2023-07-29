import os
import logging.config
import sys

up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'  # nopep8 noqa
sys.path.append(up_dir)
from wstatus import WStatus  # nopep8 noqa

from device import random_cron_delay  # nopep8 noqa
random_cron_delay(sys.argv[1:])

LOG_CONFIG = "/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG, disable_existing_loggers=False)
logger = logging.getLogger("periodic-ports")

from shadow import Shadow  # nopep8 noqa
s = Shadow(logger)
s.forward_all()

from tor import Tor  # nopep8 noqa
t = Tor(logger)
t.forward_all()

from wireguard import Wireguard  # nopep8 noqa
w = Wireguard(logger)
w.forward_all()

# Check that the API is not externally exposed.
# If so, APIs should shut down
from ipw import IPW  # nopep8 noqa
import requests  # nopep8 noqa
ipw = IPW()
external_ip = str(ipw.myip())
status = WStatus(logger)
local_token = status.get_field('status', 'local_token')
url = "https://" + external_ip + ":5000/api/v1/port_exposure/check"

print(url)
try:
    r = requests.post(url,
                      data={'local_token': str(local_token)}, timeout=1, verify=False)  # nosec: local cert, http://go.we-pn.com/waiver-3

    print(r.text)
except:
    print("OK: API port is not reachable externally.")
