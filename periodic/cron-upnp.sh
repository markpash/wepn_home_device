IP=` ifconfig eth0 | perl -nle 's/dr:(\S+)/print $1/e'`
iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -j SNAT --to $IP
/bin/bash /usr/local/pproxy/periodic/ip-shadow.sh
#forward OpenVPN ports
/usr/bin/upnpc -e 'plain OpenVPN server' -r 1194  TCP
/usr/bin/upnpc -e 'plain OpenVPN server' -r 3074  TCP
/usr/bin/upnpc -e 'reverse proxy' -r 8888  TCP
#/usr/bin/hts --max-connection-age 2000 --forward-port localhost:1194 8888
#forward all shadowsocks ports
/usr/bin/python3 /usr/local/pproxy/periodic/forward_ports.py
