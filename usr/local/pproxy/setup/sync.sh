
#!/bin/bash
# This script runs as pproxy user, NOT as root

GIT_DIR=/var/local/pproxy/git
WEPN_DIR=/usr/local/pproxy

if [ ! -d "$GIT_DIR" ];
then
	mkdir $GIT_DIR 
	cd $GIT_DIR
	git clone https://github.com/markpash/wepn_home_device.git home_device
	echo "switching to the dev branch"
	cd home_device
	git checkout markpash
	echo "ln -s $GIT_DIR/home_device/usr/local/pproxy/ $WEPN_DIR"
else
	rm -rf $GIT_DIR/home_device
	cd $GIT_DIR
	git clone https://github.com/markpash/wepn_home_device.git home_device
	echo "switching to the dev branch"
	cd home_device
	git checkout markpash
	echo "ln -s $GIT_DIR/home_device/usr/local/pproxy/ $WEPN_DIR"
fi

