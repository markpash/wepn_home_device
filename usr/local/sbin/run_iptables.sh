#!/bin/bash

PORT=9040

iptables -F
iptables -F -t nat
ip6tables -F
ip6tables -F -t nat

/usr/local/sbin/ip-shadow.sh
# we don't want to redirect traffic if Tor is not active
# TODO: need to replace this with flags. What if Tor fails?
if [[ $(netstat -tulpn | grep LISTEN | grep $PORT) ]]; then
	/usr/local/sbin/prevent_location_issue.sh
fi
