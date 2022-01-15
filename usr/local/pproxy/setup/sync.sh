
#!/bin/bash
# This script runs as pproxy user, NOT as root

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
	git stash
	git pull --ff-only
fi

