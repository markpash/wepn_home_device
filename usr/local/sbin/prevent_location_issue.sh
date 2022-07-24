#!/bin/bash

# If remote VPN users use certain (unknown) service, their location data
# is used to mark this device's IP address. As a result, this IP might 
# get incorrectly marked as part of a different country.
# To prevent, we periodically get the list of servers who make this mistake,
# and traffic to them is routed through Tor.

# See https://go.we-pn.com/wrong-location


USER=pproxy
iptables -t nat -F
ip6tables -t nat -F
iptables -A OUTPUT -p icmp -j REJECT

wget https://www.gstatic.com/ipranges/goog.txt -O goog.txt
wget https://www.gstatic.com/ipranges/cloud.json -O cloud.json

do_iptables() {
	ip=$1
	if [ -z "$ip" ]; then
		exit
	fi

	if [[ ! $ip == *:* ]]; then
		iptables -t nat -A OUTPUT ! -o lo -p tcp -m owner --uid-owner $USER --dst $ip -m tcp -j REDIRECT --to-ports 9040
		#iptables -t nat -A OUTPUT ! -o lo -p tcp --dst $ip -m tcp -j REDIRECT --to-ports 9040
	else
		ip6tables -t nat -A OUTPUT ! -o lo -p tcp -m owner --uid-owner $USER --dst $ip -m tcp -j REDIRECT --to-ports 9040
		#ip6tables -t nat -A OUTPUT ! -o lo -p tcp  --dst $ip -m tcp -j REDIRECT --to-ports 9040

	fi
}

# google ones

for ip in `cat goog.txt`; do
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

