#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical

PKG=pproxy-rpi
FLG=/var/local/pproxy/pending-set-service

date > /var/local/pproxy/last-update 2>&1
date > /tmp/update-out 2>&1

/usr/bin/dpkg --configure -a >> /tmp/update-out 2>&1

/usr/bin/apt-get update >> /tmp/update-out 2>&1
/usr/bin/apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" -f install $PKG >> /tmp/update-out 2>&1

# Moved to cron-root: OS upgrade needed?
# /usr/local/sbin/upgrade-os.sh >> /tmp/update-out 2>&1
