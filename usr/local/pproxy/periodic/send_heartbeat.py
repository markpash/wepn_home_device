import sys
import os
import logging.config
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
from heartbeat import HeartBeat
from wstatus import WStatus
status = WStatus()
claimed=status.get('claimed')
LOG_CONFIG="/etc/pproxy/logging.ini"
logging.config.fileConfig(log_config,
            disable_existing_loggers=False)
logger = logging.getLogger("periodic-heartbeat")

HEARTBEAT_PROCESS = HeartBeat(logger)
HEARTBEAT_PROCESS.send_heartbeat(int(claimed)==1)
