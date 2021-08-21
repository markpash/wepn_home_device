GIT_DIR=/var/local/pproxy/git
WEPN_DIR=/usr/local/pproxy


if [ ! -d "$GIT_DIR" ];
then
	mkdir $GIT_DIR 
	cd $GIT_DIR
	git clone https://bitbucket.org/dvpn4hr/home_device.git
	ln -s $GIT_DIR/home_device/usr/local/pproxy/ $WEPN_DIR
else
	cd $GIT_DIR/home_device/
	git pull
fi

/bin/bash $WEPN_DIR/setup/post-install.sh
cp -r $GIT_DIR/home_device/etc/* /etc/
cp -r $GIT_DIR/home_device/usr/local/sbin/* /usr/local/sbin/
systemctl enable wepn-api
systemctl enable wepn-keypad
systemctl enable wepn-poweroff
systemctl enable wepn-leds
systemctl enable wepn-main

