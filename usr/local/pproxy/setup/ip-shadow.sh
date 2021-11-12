DEFAULT_GW=`ip route | grep default | awk '{print $3}'`
iptables -F
iptables -N SHADOWSOCKS
iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -d 0.0.0.0/8 -j REJECT
iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -d 10.0.0.0/8 -j REJECT
iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -d 169.254.0.0/16 -j REJECT
iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -d 172.16.0.0/12 -j REJECT
iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -d 192.168.0.0/16 -j REJECT
iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -d 224.0.0.0/4 -j REJECT
iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -d 240.0.0.0/4 -j REJECT

iptables -t filter -m owner --uid-owner pproxy -A  SHADOWSOCKS -d 0.0.0.0/8 -j REJECT
iptables -t filter -m owner --uid-owner pproxy -A  SHADOWSOCKS -d 10.0.0.0/8 -j REJECT
iptables -t filter -m owner --uid-owner pproxy -A  SHADOWSOCKS -d 169.254.0.0/16 -j REJECT
iptables -t filter -m owner --uid-owner pproxy -A  SHADOWSOCKS -d 172.16.0.0/12 -j REJECT
iptables -t filter -m owner --uid-owner pproxy -A  SHADOWSOCKS -d 192.168.0.0/16 -j REJECT
iptables -t filter -m owner --uid-owner pproxy -A  SHADOWSOCKS -d 224.0.0.0/4 -j REJECT
iptables -t filter -m owner --uid-owner pproxy -A  SHADOWSOCKS -d 240.0.0.0/4 -j REJECT
#SS existing works

iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -t filter -m owner --uid-owner pproxy -A SHADOWSOCKS -m state --state ESTABLISHED,RELATED -j ACCEPT

iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -d $DEFAULT_GW -j ACCEPT
iptables -t filter -m owner --uid-owner pproxy -A SHADOWSOCKS -d $DEFAULT_GW -j ACCEPT

#iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -p tcp -j REJECT --reject-with tcp-reset 
#iptables -t filter -m owner --uid-owner shadowsocks -A SHADOWSOCKS -p udp -j REJECT --reject-with tcp-reset 


iptables -A OUTPUT -j SHADOWSOCKS
