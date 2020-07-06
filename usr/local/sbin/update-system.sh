#!/bin/bash
#wait for the hourly update to pass
#sleep 300

date -R > /var/local/pproxy/last-system-update 2>&1

wget -qO - https://repo.we-pn.com/repo.we-pn.com.gpg.key | sudo apt-key add -
/usr/bin/apt-get update
/usr/bin/apt-get update -y --allow-releaseinfo-change --fix-missing
/usr/bin/apt-get upgrade -y


date -R  >> /var/local/pproxy/last-system-update 2>&1
