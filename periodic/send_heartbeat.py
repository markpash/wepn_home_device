import sys
import os
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
from heartbeat import HeartBeat
from wstatus import WStatus
status = WStatus()
claimed=status.get('claimed')

HEARTBEAT_PROCESS = HeartBeat()
HEARTBEAT_PROCESS.send_heartbeat(int(claimed)==1)
