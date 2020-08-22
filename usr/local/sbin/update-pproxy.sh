#!/bin/bash

date > /var/local/pproxy/last-update 2>&1
date > /tmp/update-out 2>&1

dpkg --configure -a >> /tmp/update-out 2>&1

/usr/bin/apt-get update >> /tmp/update-out 2>&1
/usr/bin/apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew"  -f install pproxy-rpi >> /tmp/update-out 2>&1

#OS upgrade needed?
/usr/local/sbin/upgrade-os.sh >> /tmp/update-out 2>&1
apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" install python3  -qy -f
