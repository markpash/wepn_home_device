export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical

DEST_VERSION_START=6
UNAME=`uname -r`

if [[ $UNAME == $DEST_VERSION_START* ]]; then
	echo "Already upgraded"
	exit
fi

# Going forward after this, we need to *not* touch main repo lsits
# and only update wepn.list
cat > /etc/apt/sources.list << EOF
deb http://deb.debian.org/debian bullseye main contrib non-free
deb http://security.debian.org/debian-security bullseye-security main contrib non-free
deb http://deb.debian.org/debian bullseye-updates main contrib non-free
# Uncomment deb-src lines below then 'apt-get update' to enable 'apt-get source'
#deb-src http://deb.debian.org/debian bullseye main contrib non-free
#deb-src http://security.debian.org/debian-security bullseye-security main contrib non-free
#deb-src http://deb.debian.org/debian bullseye-updates main contrib non-free
EOF



cat > /etc/apt/sources.list.d/raspi.list << EOF
deb http://archive.raspberrypi.org/debian/ bullseye main
# Uncomment line below then 'apt-get update' to enable 'apt-get source'
#deb-src http://archive.raspberrypi.org/debian/ bullseye main
EOF

cat > /etc/apt/sources.list.d/wepn.list << EOF
deb https://repo.we-pn.com/debian/ bullseye main
EOF

/bin/bash /usr/local/sbin/update-system.sh >> /tmp/update-out 2>&1

apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" upgrade >> /tmp/update-out 2>&1
apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" dist-upgrade >> /tmp/update-out 2>&1


/bin/bash /usr/local/sbin/update-system.sh

apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" upgrade shadowsocks-libev  >> /tmp/update-out 2>&1

reboot
