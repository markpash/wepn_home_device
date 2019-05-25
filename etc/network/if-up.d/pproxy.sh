#block access to local IP ranges
/bin/bash /usr/local/sbin/ip-shadow.sh

#send heartbeat/correct the LCD status
/usr/bin/python3 /usr/local/pproxy/periodic/send_heartbeat.py

