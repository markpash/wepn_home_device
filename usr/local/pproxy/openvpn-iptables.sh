PORT="3074"
IP=` ifconfig eth0 | perl -nle 's/dr:(\S+)/print $1/e'`
if [[ -z $IP ]]; then
	IP=` ifconfig wlan0 | perl -nle 's/dr:(\S+)/print $1/e'`
fi
if [[ -z $IP ]]; then
	echo "Cannot get Local IP address"
	exit 4
fi
PROTO="tcp"
iptables -t nat -F
if [[ -e /etc/debian_version ]]; then
	OS=debian
	RCLOCAL='/etc/rc.local'
elif [[ -e /etc/centos-release || -e /etc/redhat-release ]]; then
	OS=centos
	RCLOCAL='/etc/rc.d/rc.local'
	# Needed for CentOS 7
	chmod +x /etc/rc.d/rc.local
else
	echo "Looks like you aren't running this installer on a Debian, Ubuntu or CentOS system"
	exit 4
fi
echo 1 > /proc/sys/net/ipv4/ip_forward
# Set NAT for the VPN subnet
iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -j SNAT --to $IP
echo iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -j SNAT --to $IP
sed -i "1 a\iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -j SNAT --to $IP" $RCLOCAL
if pgrep firewalld; then
	# We don't use --add-service=openvpn because that would only work with
	# the default port. Using both permanent and not permanent rules to
	# avoid a firewalld reload.
	firewall-cmd --zone=public --add-port=$PORT/$PROTO
	firewall-cmd --zone=trusted --add-source=10.8.0.0/24
	firewall-cmd --permanent --zone=public --add-port=$PORT/$PROTO
	firewall-cmd --permanent --zone=trusted --add-source=10.8.0.0/24
fi
if iptables -L | grep -qE 'REJECT|DROP'; then
	# If iptables has at least one REJECT rule, we asume this is needed.
	# Not the best approach but I can't think of other and this shouldn't
	# cause problems.
	iptables -t nat -F
	iptables -I INPUT -p $PROTO --dport $PORT -j ACCEPT
	iptables -I FORWARD -s 10.8.0.0/24 -j ACCEPT
	iptables -I FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
	sed -i "1 a\iptables -I INPUT -p $PROTO --dport $PORT -j ACCEPT" $RCLOCAL
	sed -i "1 a\iptables -I FORWARD -s 10.8.0.0/24 -j ACCEPT" $RCLOCAL
	sed -i "1 a\iptables -I FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT" $RCLOCAL
fi
# If SELinux is enabled and a custom port was selected, we need this
if hash sestatus 2>/dev/null; then
	if sestatus | grep "Current mode" | grep -qs "enforcing"; then
		if [[ "$PORT" != '1194' ]]; then
			# semanage isn't available in CentOS 6 by default
			if ! hash semanage 2>/dev/null; then
				yum install policycoreutils-python -y
			fi
			semanage port -a -t openvpn_port_t -p $PROTO $PORT
		fi
	fi
fi
#Added for STUNNEL
sudo iptables -A INPUT -p tcp --dport 993 -j ACCEPT
sudo iptables -t nat -A PREROUTING -i tun+ -p tcp --dport 80 -j REDIRECT --to-port 8080

