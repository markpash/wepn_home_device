#!/bin/bash
# This script runs as root, so it can
# set correct permissions, install systemctl scripts, ...

GIT_DIR=/var/local/pproxy/git
WEPN_DIR=/usr/local/pproxy
OLD_WEPN_DIR=/usr/local/old-pproxy
/usr/sbin/usermod -s  /bin/bash pproxy

mv $WEPN_DIR $OLD_WEPN_DIR
su -c "/bin/bash $OLD_WEPN_DIR/setup/sync.sh" pproxy
cp -r $GIT_DIR/home_device/etc/* /etc/
cp -r $GIT_DIR/home_device/usr/local/sbin/* /usr/local/sbin/

/usr/bin/ln -s $GIT_DIR/home_device/$WEPN_DIR/ $WEPN_DIR

if [ -L $WEPN_DIR ] && [ -e $WEPN_DIR ];
then
	echo "symlink created"
else
	echo "could not create a symlink, please carefully clean up:"
	echo rm $WEPN_DIR
	echo mv $OLD_WEPN_DIR $WEPN_DIR
	echo rm -rf $GIT_DIR
	echo ls -la /usr/local/
	exit
fi

/bin/bash $WEPN_DIR/setup/post-install.sh
systemctl daemon-reload
systemctl enable wepn-api
systemctl enable wepn-keypad
systemctl enable wepn-poweroff
systemctl enable wepn-leds
systemctl enable wepn-main
