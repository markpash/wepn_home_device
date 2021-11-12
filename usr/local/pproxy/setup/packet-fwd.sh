EXTIF="eth0"
INTIF="eth1"
SS_SERVER_IP='1.2.3.4'
SS_SERVER_PORT='4001'
SS_LOCAL_PORT='1080'
iptables -F
iptables -t nat -F
iptables -t nat -X SHADOWSOCKS

iptables -t nat -A POSTROUTING -o $EXTIF -j MASQUERADE
iptables -A FORWARD -i $EXTIF -o $INTIF -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i $INTIF -o $EXTIF -j ACCEPT



iptables -t nat -N SHADOWSOCKS

iptables -t nat -A SHADOWSOCKS -d $SS_SERVER_IP -j RETURN

# lan
iptables -t nat -A SHADOWSOCKS -d 0.0.0.0/8 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 10.0.0.0/8 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 127.0.0.0/8 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 169.254.0.0/16 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 172.16.0.0/12 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 192.168.0.0/16 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 224.0.0.0/4 -j RETURN
iptables -t nat -A SHADOWSOCKS -d 240.0.0.0/4 -j RETURN


iptables -t nat -A SHADOWSOCKS -p tcp -j REDIRECT --to-ports $SS_LOCAL_PORT
iptables -t nat -I PREROUTING -p tcp -j SHADOWSOCKS
