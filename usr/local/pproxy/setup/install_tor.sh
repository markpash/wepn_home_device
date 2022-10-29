apt update
apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" install tor obfs4proxy

cat > /etc/tor/torrc <<EOF

BridgeRelay 0
ExitRelay 0
ORPort 8991
ServerTransportPlugin obfs4 exec /usr/bin/obfs4proxy
ServerTransportListenAddr obfs4 0.0.0.0:8992
ExtORPort auto

PublishServerDescriptor 0
BridgeDistribution none
ExitPolicy reject *:*

AccountingStart day 0:00
AccountingMax 5 GBytes
RelayBandwidthRate 1000 KBytes
RelayBandwidthBurst 5000 KBytes # allow higher bursts but maintain average

Transport 9040
DNSPort 5353
AutomapHostsOnResolve 1
AutomapHostsSuffixes .exit,.onion

ControlPort 9051
CookieAuthentication 1
CookieAuthFileGroupReadable 1

Nickname WETor
EOF

setcap cap_net_bind_service=+ep /usr/bin/obfs4proxy

if ! grep -q "NoNewPrivileges=no" /lib/systemd/system/tor@default.service ;
then
	echo  "NoNewPrivileges=no" >> /lib/systemd/system/tor@default.service
	echo  "NoNewPrivileges=no" >> /lib/systemd/system/tor@.service
	systemctl daemon-reload
fi
systemctl enable --now tor.service
systemctl restart tor.service

# make authcookie usable for user pi
# helps with nyx

groupadd tor-log
usermod -a -G tor-log pi
usermod -a -G tor-log debian-tor 

chown debian-tor.tor-log /run/tor/control.authcookie
chmod 660 /run/tor/control.authcookie
