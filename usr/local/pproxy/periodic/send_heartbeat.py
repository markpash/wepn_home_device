import sys
import os
import logging.config
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)
# above line is needed for following classes:
from diag import WPDiag  # noqa E402 need up_dir first
from wstatus import WStatus  # noqa E402 need up_dir first
from heartbeat import HeartBeat  # noqa E402 need up_dir first
from device import random_cron_delay
from constants import LOG_CONFIG

logging.config.fileConfig(LOG_CONFIG, disable_existing_loggers=False)
logger = logging.getLogger("heartbeat")

port = 4099

random_cron_delay(sys.argv[1:])

status = WStatus(logger)
claimed = status.get('claimed')

diag = WPDiag(logger)


HEARTBEAT_PROCESS = HeartBeat(logger)
HEARTBEAT_PROCESS.send_heartbeat()
HEARTBEAT_PROCESS.record_hb_send()
