#!/bin/bash
#

PPROXY_HOME=/usr/local/pproxy
PPROXY_VENV=/var/local/pproxy/wepn-env
PIP_CACHE=/var/local/pproxy/pip-cache
REMOTE_KEY=/var/local/pproxy/shared_remote_key.priv

chown pproxy:pproxy /var/local/pproxy/config.bak
chmod 0600 /var/local/pproxy/config.bak
chown pproxy:pproxy /var/local/pproxy/status.bak
chmod 0600 /var/local/pproxy/status.bak
chown pproxy:pproxy $PPROXY_HOME
chown -R pproxy:pproxy $PPROXY_HOME/*
chown -R pproxy:pproxy $PPROXY_HOME/.*
mkdir -p /var/local/pproxy
mkdir -p /var/local/pproxy/shadow/
touch /var/local/pproxy/status.ini
chown pproxy:pproxy /var/local/pproxy
chown pproxy:pproxy /var/local/pproxy/*
chown pproxy:pproxy /var/local/pproxy/.*
chown pproxy:pproxy /var/local/pproxy/shadow/*

echo -e "correcting scripts that run as sudo"
for SCRIPT in ip-shadow restart-pproxy update-pproxy update-system wepn_git prevent_location_issue iptables-flush check-venv
do
	chown root:root /usr/local/sbin/$SCRIPT.sh
	chmod 755 /usr/local/sbin/$SCRIPT.sh
done
chown root:root $PPROXY_HOME/system_services/led_manager.py
chown pproxy:pproxy $PPROXY_VENV
chown pproxy:pproxy $PPROXY_VENV/* -R
chown pproxy:pproxy $PIP_CACHE
chown pproxy:pproxy $PIP_CACHE/* -R
chown pproxy:pproxy /etc/pproxy/*
chmod 644 /etc/pproxy/*
chown pproxy:pproxy $REMOTE_KEY
chmod 0600 $REMOTE_KEY
chown pproxy:shadow-runners /var/local/pproxy/shadow.db*
chmod 664 /var/local/pproxy/shadow.db*
touch /var/local/pproxy/tor.db
chown pproxy:shadow-runners /var/local/pproxy/tor.db*
chmod 664 /var/local/pproxy/tor.db*
chown pproxy:shadow-runners /var/local/pproxy/shadow/shadow.sock
chown pproxy:shadow-runners /var/local/pproxy/
chown wepn-api $PPROXY_HOME/local_server/wepn-local.*
chgrp wepn-web $PPROXY_HOME/local_server/wepn-local.*
chgrp wepn-web $PPROXY_HOME/local_server/
chmod g+r $PPROXY_HOME/local_server/wepn-local.*
chmod g+r $PPROXY_HOME/local_server/.
chown shadowsocks:shadow-runners /etc/shadowsocks-libev/config.json
chmod 775 /etc/shadowsocks-libev/config.json
chown pproxy:shadow-runners /var/local/pproxy/shadow/shadow.sock
chmod 775 /var/local/pproxy/shadow/shadow.sock
chown pproxy:shadow-runners /var/local/pproxy/shadow/
chmod 775 /var/local/pproxy/shadow/
touch /var/local/pproxy/error.log
touch /var/local/pproxy/error.log.1
touch /var/local/pproxy/error.log.2
touch /var/local/pproxy/error.log.3
chown pproxy:wepn-api /var/local/pproxy/error.log*
chmod 650 /var/local/pproxy/error.log*
