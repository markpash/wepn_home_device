#!/bin/bash
#wait for the hourly update to pass
#sleep 300
date -R > /var/local/pproxy/last-system-update 2>&1

dpkg --configure -a

wget -qO - https://repo.we-pn.com/repo.we-pn.com.gpg.key | sudo apt-key add -
/usr/bin/apt-get update
/usr/bin/apt-get update -y --allow-releaseinfo-change --fix-missing
/usr/bin/apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" upgrade >> /tmp/update-out 2>&1
/usr/bin/apt-get --yes  -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" upgrade shadowsocks-libev  >> /tmp/update-out 2>&1


date -R  >> /var/local/pproxy/last-system-update 2>&1
