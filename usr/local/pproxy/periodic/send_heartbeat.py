import sys
import os
import logging.config
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
LOG_CONFIG="/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)
logger = logging.getLogger("periodic-heartbeat")
from heartbeat import HeartBeat
from wstatus import WStatus
status = WStatus(logger)
claimed=status.get('claimed')

HEARTBEAT_PROCESS = HeartBeat(logger)
HEARTBEAT_PROCESS.send_heartbeat(int(claimed)==1)
