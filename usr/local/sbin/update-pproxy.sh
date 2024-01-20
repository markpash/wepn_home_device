#!/bin/bash
export PATH=$PATH:/usr/local/sbin/:/usr/sbin/

date > /var/local/pproxy/last-update 2>&1
date > /tmp/update-out 2>&1

dpkg --configure -a >> /tmp/update-out 2>&1

/usr/bin/apt-get update >> /tmp/update-out 2>&1
/usr/bin/apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew"  -f install pproxy-rpi >> /tmp/update-out 2>&1

# Moved to cron-root: OS upgrade needed?
# /usr/local/sbin/upgrade-os.sh >> /tmp/update-out 2>&1
