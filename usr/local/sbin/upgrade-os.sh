export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical

DEST_VERSION_START=5
uname=`uname -r`

if [ $uname==DEST_VERSION_START* ]; then
	echo "Already upgraded"
	exit
fi

cat > /etc/apt/sources.list << EOF
deb http://raspbian.raspberrypi.org/raspbian/ buster main contrib non-free rpi
# Uncomment line below then 'apt-get update' to enable 'apt-get source'
#deb-src http://raspbian.raspberrypi.org/raspbian/ buster main contrib non-free rpi
deb https://repo.we-pn.com/debian/ buster main
EOF


cat > /etc/apt/sources.list.d/raspi.list << EOF
deb http://archive.raspberrypi.org/debian/ buster main
# Uncomment line below then 'apt-get update' to enable 'apt-get source'
#deb-src http://archive.raspberrypi.org/debian/ buster main
EOF

/bin/bash /usr/local/sbin/update-system.sh >> /tmp/update-out 2>&1

apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" upgrade >> /tmp/update-out 2>&1
apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" dist-upgrade >> /tmp/update-out 2>&1


/bin/bash /usr/local/sbin/update-system.sh

apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" upgrade shadowsocks-libev  >> /tmp/update-out 2>&1

reboot
