IP=0
PORT=1194

#apt-get update
#apt-get install openvpn iptables openssl ca-certificates -y

if [[ ! -d /etc/openvpn/easy-rsa/ ]]; then
	# Get easy-rsa
        if [[ ! -f ./EasyRSA-3.0.4.tgz ]]; then
		wget -O ./EasyRSA-3.0.4.tgz https://github.com/OpenVPN/easy-rsa/releases/download/v3.0.4/EasyRSA-3.0.4.tgz
	fi
        tar xzf ./EasyRSA-3.0.4.tgz -C ./
	mv ./EasyRSA-3.0.4/ /etc/openvpn/
	mv /etc/openvpn/EasyRSA-3.0.4/ /etc/openvpn/easy-rsa/
	chown -R root:root /etc/openvpn/easy-rsa/
	rm -rf ~/EasyRSA-3.0.4.tgz
fi
cd /etc/openvpn/easy-rsa/
# Create the PKI, set up the CA, the DH params and the server + client certificates
echo "init pki"
./easyrsa init-pki
echo "build ca in progress"
./easyrsa --batch build-ca nopass
echo "generating DH params"
./easyrsa gen-dh
echo "building server confs"
./easyrsa build-server-full server nopass
echo "generating CRL"
./easyrsa gen-crl
echo "moving configs"
# Move the stuff we need
cp pki/ca.crt pki/private/ca.key pki/dh.pem pki/issued/server.crt pki/private/server.key /etc/openvpn/easy-rsa/pki/crl.pem /etc/openvpn


echo "generating server.conf"
# Generate server.conf
echo "port $PORT
proto udp
dev tun
sndbuf 0
rcvbuf 0
ca ca.crt
cert server.crt
key server.key
dh dh.pem
topology subnet
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist ipp.txt" > /etc/openvpn/server.conf


echo 'push "redirect-gateway def1 bypass-dhcp"' >> /etc/openvpn/server.conf
# DNS
echo 'push "dhcp-option DNS 8.8.8.8"' >> /etc/openvpn/server.conf
echo 'push "dhcp-option DNS 8.8.4.4"' >> /etc/openvpn/server.conf
echo 'push "dhcp-option DNS 208.67.222.222"' >> /etc/openvpn/server.conf
echo 'push "dhcp-option DNS 208.67.220.220"' >> /etc/openvpn/server.conf

echo "keepalive 10 120
comp-lzo
persist-key
persist-tun
status openvpn-status.log
verb 3
crl-verify crl.pem" >> /etc/openvpn/server.conf


# Enable net.ipv4.ip_forward for the system
	sed -i 's|#net.ipv4.ip_forward=1|net.ipv4.ip_forward=1|' /etc/sysctl.conf
# Avoid an unneeded reboot
echo 1 > /proc/sys/net/ipv4/ip_forward
# And finally, restart OpenVPN
	# Little hack to check for systemd
	if pgrep systemd-journal; then
		systemctl restart openvpn@server.service
	else
		/etc/init.d/openvpn restart
	fi
# Try to detect a NATed connection and ask about it to potential LowEndSpirit users
EXTERNALIP=$(wget -qO- ipv4.icanhazip.com)
if [[ "$IP" != "$EXTERNALIP" ]]; then
#	echo ""
#	echo "Looks like your server is behind a NAT!"
#	echo ""
#	echo "If your server is NATed (e.g. LowEndSpirit), I need to know the external IP"
#	echo "If that's not the case, just ignore this and leave the next field blank"
#	read -p "External IP: " -e USEREXTERNALIP
	if [[ "$USEREXTERNALIP" != "" ]]; then
		IP=$USEREXTERNALIP
	fi
fi


# client-common.txt is created so we have a template to add further users later
echo "client
dev tun
proto udp
sndbuf 0
rcvbuf 0
remote $IP $PORT
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
comp-lzo
verb 3" > /etc/openvpn/client-common.txt


echo "Done with initializing the OpenVPN service"
