#!/bin/bash
#wait for the hourly update to pass
#sleep 300

date -R > /var/local/pproxy/last-system-update 2>&1

export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical

wget -qO - https://repo.we-pn.com/repo.we-pn.com.gpg.key | sudo apt-key add -
/usr/bin/apt-get update -qy
/usr/bin/apt-get update -qy --allow-releaseinfo-change --fix-missing
/usr/bin/apt-get upgrade -qy


date -R  >> /var/local/pproxy/last-system-update 2>&1
