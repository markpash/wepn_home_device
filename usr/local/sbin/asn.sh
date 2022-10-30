#!/bin/bash
echo "-------------------------------------------------"
IPS=`ss -n | grep 400 | awk '{ print $6}' | awk -F: '{print $1}' | sort -n | uniq `
for ip in $IPS; do
	echo $ip
	whois -h v4.whois.cymru.com " -c -p $ip"
done

echo "-------------------------------------------------"

