# This product (WEPN) is produced independently from the Tor® anonymity software
# and carries no guarantee from The Tor Project about quality,
# suitability or anything else. WEPN staff and contributors do not make any
# modifications to the Tor source code as part of WEPN project, and only configure and
# distribute it as part of this platform.
# WEPN is not affiliated, sponsored by, or sponsoring Tor project.
#
# Please learn about Tor organization at https://www.torproject.org/


# These two lines are only used when directly insalling this script
# not as part of post-install pacakge
# apt update
# apt-get --yes  -o Dpkg::Options::="--force-confdef" \
#      -o Dpkg::Options::="--force-confnew" install tor obfs4proxy

ORPORT=`cat /etc/pproxy/config.ini  | grep orport | awk '{print $3}'`
ORPORT=${ORPORT:=8991}

cat > /etc/tor/torrc <<EOF

BridgeRelay 1
ExitRelay 0
ORPort $ORPORT
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

# add Tor's repo to get their updates
# Note: this unfortunately doesn't work on armhf (raspberry) currently. While we are an arm64,
# rpi still shows arch as armhf which is not supported by Tor builds.
# We have our dpkg builds of Tor, from their source and without modification, in our repo.
wget -qO- https://deb.torproject.org/torproject.org/A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89.asc | gpg --dearmor | tee /usr/share/keyrings/tor-archive-keyring.gpg >/dev/null
DISTRIBUTION=`lsb_release -c | awk '{print $2}'`
cat > /etc/apt/sources.list.d/tor.list <<EOF
   deb     [signed-by=/usr/share/keyrings/tor-archive-keyring.gpg] https://deb.torproject.org/torproject.org $DISTRIBUTION main
   deb-src [signed-by=/usr/share/keyrings/tor-archive-keyring.gpg] https://deb.torproject.org/torproject.org $DISTRIBUTION main
EOF
# end of adding Tor repo

/usr/sbin/setcap cap_net_bind_service=+ep /usr/bin/obfs4proxy

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

/usr/sbin/groupadd tor-log
/usr/sbin/usermod -a -G tor-log pi
/usr/sbin/usermod -a -G tor-log debian-tor

chown debian-tor:tor-log /run/tor/control.authcookie
chmod 660 /run/tor/control.authcookie
