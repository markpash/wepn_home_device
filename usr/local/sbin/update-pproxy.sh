#!/bin/bash
date > /var/local/pproxy/last-update 2>&1
date > /var/local/tmp/update-out 2>&1

/usr/bin/apt-get update >> /tmp/update-out 2>&1
/usr/bin/apt-get -y install pproxy-rpi >> /tmp/update-out 2>&1
