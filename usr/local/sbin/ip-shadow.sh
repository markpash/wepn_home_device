iptables -F SHADOWSOCKS
iptables -N SHADOWSOCKS
iptables -t filter -A SHADOWSOCKS -d 192.168.1.1 -j ACCEPT
iptables -t filter -A SHADOWSOCKS -d 127.0.0.0/8 -j REJECT
iptables -t filter -A SHADOWSOCKS -d 10.0.0.0/8 -j REJECT
iptables -t filter -A SHADOWSOCKS -d 169.254.0.0/16 -j REJECT
iptables -t filter -A SHADOWSOCKS -d 172.16.0.0/12 -j REJECT
iptables -t filter -A SHADOWSOCKS -d 192.168.0.0/16 -j REJECT
iptables -t filter -A SHADOWSOCKS -d 224.0.0.0/4 -j REJECT
iptables -t filter -A SHADOWSOCKS -d 240.0.0.0/4 -j REJECT
iptables -t filter -A SHADOWSOCKS -d 0.0.0.0/0 -j ACCEPT
iptables -t filter -A SHADOWSOCKS -d 192.168.1.1 -j ACCEPT
iptables -A OUTPUT -m owner --uid-owner shadowsocks -j SHADOWSOCKS
