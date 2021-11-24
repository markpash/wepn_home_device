# Until added as dependency to debian package
# or roll out package manager feature
apt-get update && apt-get upgrade -y
apt-get install wireguard

cd /etc/wireguard

umask 077
wg genkey | tee privatekey | wg pubkey > publickey

PUB_SERVER=`cat publickey`
PRIV_SERVER=`cat privatekey`

cat > /etc/wireguard/wg0.conf << EOF

[Interface]
PrivateKey = $PRIV_SERVER
Address = 10.0.0.1/24
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
ListenPort = 51820

[Peer]
PublicKey = $PUB_SERVER
AllowedIPs = 10.0.0.2/32
EOF

wg-quick up wg0
wg show
systemctl enable wg-quick@wg0
cd -
