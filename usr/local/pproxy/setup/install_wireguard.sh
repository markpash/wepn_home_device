# Until added as dependency to debian package
# or roll out package manager feature
# Next two lines should only run manually
# apt-get update && apt-get upgrade -y
# apt-get install wireguard

PORT=`cat /etc/pproxy/config.ini  | grep wireport | awk '{print $3}'`
PORT=${ORPORT:=6711}

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
ListenPort = $PORT

[Peer]
PublicKey = $PUB_SERVER
AllowedIPs = 10.0.0.2/32
EOF

wg-quick up wg0
wg show
systemctl enable wg-quick@wg0

rm -f publickey
rm -f privatekey

cd -
