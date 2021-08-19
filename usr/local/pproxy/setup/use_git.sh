GIT_DIR=/var/local/pproxy/git
WEPN_DIR=/usr/local/pproxy
mkdir $GIT_DIR 
cd $GIT_DIR

git clone https://bitbucket.org/dvpn4hr/home_device.git
ln -s $GIT_DIR/home_device/usr/local/pproxy/ $WEPN_DIR

/bin/bash $WEPN_DIR/setup/post-install.sh
cp -r /var/local/pproxy/git/home_device/etc/* /etc/systemd/
systemctl enable wepn-api
#systemctl enable wepn-keypad
systemctl enable wepn-poweroff
#systemctl enable wepn-leds

