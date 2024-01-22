#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical
export PATH=$PATH:/usr/local/sbin/:/usr/sbin/

PKG=pproxy-rpi
FLG="/var/local/pproxy/pending-set-service"
LOG="/tmp/update-out"

date > /var/local/pproxy/last-update 2>&1
date > $LOG 2>&1

/usr/bin/dpkg --configure -a >> $LOG 2>&1

/usr/bin/apt-get update >> $LOG 2>&1
/usr/bin/apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" -f install $PKG >> $LOG 2>&1

if grep -q 1 $FLG; then
  echo "0" > $FLG
  /bin/bash /usr/local/pproxy/setup/set-services.sh >> $LOG 2>&1
fi

# Moved to cron-root: OS upgrade needed?
# /usr/local/sbin/upgrade-os.sh >> /tmp/update-out 2>&1
