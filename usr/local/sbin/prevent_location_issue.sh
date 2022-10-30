#!/bin/bash

# If remote VPN users use certain (unknown) service, their location data
# is used to mark this device's IP address. As a result, this IP might 
# get incorrectly marked as part of a different country.
# To prevent, we periodically get the list of servers who make this mistake,
# and traffic to them is routed through Tor.

# See https://go.we-pn.com/wrong-location

ORPORT=`cat /etc/pproxy/config.ini  | grep orport | awk '{print $3}'`
ORPORT=${ORPORT:=8991}
USER=pproxy

# we don't want to redirect traffic if Tor is not active
# TODO: need to replace this with flags. What if Tor fails?
#if ! [[ $(netstat -tulpn | grep LISTEN | grep $ORPORT) ]]; then
#	echo "Tor not running, no need to redirect traffic"
#	exit
#fi

wget https://www.gstatic.com/ipranges/goog.txt -O goog.txt
wget https://www.gstatic.com/ipranges/cloud.json -O cloud.json

do_iptables() {
	ip=$1
	if [ -z "$ip" ]; then
		exit
	fi

	for proto in tcp udp; do
		if [[ ! $ip == *:* ]]; then
			iptables -t nat -A OUTPUT ! -o lo -p $proto -m owner --uid-owner $USER --dst $ip -m $proto -j REDIRECT --to-ports $ORPORT
		else
			ip6tables -t nat -A OUTPUT ! -o lo -p $proto -m owner --uid-owner $USER --dst $ip -m $proto -j REDIRECT --to-ports $ORPORT

		fi
	done
}

# google ones

for ip in `cat goog.txt | grep -v 8\.8\.`; do
	do_iptables $ip
done

echo "doing cloud now"

# cloud ones
jq -c ".${str}" cloud.json | while read ip; do
	do_iptables $ip
done

jq ".prefixes[].ipv4Prefix" cloud.json  -c --raw-output | grep -v null | while read ip; do
	do_iptables $ip
done



jq ".prefixes[].ipv6Prefix" cloud.json  -c --raw-output | grep -v null | while read ip; do
	do_iptables $ip
done

