#!/bin/bash

echo -e "Reloading and restarting services"
export SYSTEMD_PAGER=""

SYSTEMCTL="/usr/bin/systemctl --no-block --no-pager"
$SYSTEMCTL daemon-reload 
$SYSTEMCTL restart shadowsocks-libev
$SYSTEMCTL restart shadowsocks-libev-manager
$SYSTEMCTL enable wepn-api
$SYSTEMCTL restart wepn-api
$SYSTEMCTL enable wepn-keypad
$SYSTEMCTL restart wepn-keypad
$SYSTEMCTL enable wepn-leds
$SYSTEMCTL restart wepn-leds
$SYSTEMCTL restart wepn-keypad
$SYSTEMCTL enable wepn-poweroff
$SYSTEMCTL enable wepn-main
$SYSTEMCTL restart wepn-main


echo "Restarts done"

# pproxy has moved to wepn-main on systemctl
if test -f /etc/rc3.d/S01pproxy; then
  /bin/sh /etc/init.d/pproxy restart
  update-rc.d pproxy disable
fi
