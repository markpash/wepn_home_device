import sys
import os
import logging.config

LOG_CONFIG = "/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG, disable_existing_loggers=False)
logger = logging.getLogger("periodic-ports")


up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)

from shadow import Shadow
from wstatus import WStatus

s = Shadow(logger)
s.forward_all()

# Check that the API is not externally exposed.
# If so, APIs should shut down
from ipw import IPW
import requests
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
