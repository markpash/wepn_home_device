#!/bin/bash
# This script runs as root, so it can
# set correct permissions, install systemctl scripts, ...

GIT_DIR=/var/local/pproxy/git
WEPN_DIR=/usr/local/pproxy


cp -r $GIT_DIR/home_device/etc/* /etc/
cp -r $GIT_DIR/home_device/usr/local/sbin/* /usr/local/sbin/

/bin/bash $WEPN_DIR/setup/post-install.sh
systemctl daemon-reload
systemctl enable wepn-api
systemctl enable wepn-keypad
systemctl enable wepn-poweroff
systemctl enable wepn-leds
systemctl enable wepn-main

