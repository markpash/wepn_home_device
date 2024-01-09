#!/bin/bash
sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen
locale-gen "en_US.UTF-8"
export LC_ALL="en_US.UTF-8"
export LANG=en_US.UTF-8
PPROXY_HOME=/usr/local/pproxy/
PPROXY_VENV=/var/local/pproxy/wepn-env
venv_flag_file=/var/local/pproxy/wepn-venv-installed
OVPN_ENABLED=0

######################################
## add heartbeat to crontab
## system updates to weekly/daily crontab
######################################
/usr/bin/crontab -u pproxy $PPROXY_HOME/setup/cron
/usr/bin/crontab -u root $PPROXY_HOME/setup/cron-root
/usr/bin/crontab -u pi $PPROXY_HOME/setup/cron-pi

######################################
## Copy back up config files
## helps when files get corrupted
######################################
if [ ! -f "/var/local/pproxy/config.bak" ]; then
    cp /etc/pproxy/config.ini /var/local/pproxy/config.bak
fi
if [ ! -f "/var/local/pproxy/status.bak" ]; then
    cp /var/local/pproxy/status.ini /var/local/pproxy/status.bak
fi

chown pproxy:pproxy /var/local/pproxy/config.bak
chmod 0600 /var/local/pproxy/config.bak
chown pproxy:pproxy /var/local/pproxy/status.bak
chmod 0600 /var/local/pproxy/status.bak

######################################
######################################
## Add PProxy user
######################################
echo -e "\n* Configuring WEPN ... "
echo -e "If you are setting up services yourself, expect some user/owner/file warnings."
echo -e "These are usually harmless errors."

## Removing .git residue just in case
rm -rf /.git/*

echo -e "\nAdding users"
adduser pproxy --disabled-password --disabled-login --home $PPROXY_HOME --quiet --gecos "WEPN PPROXY User"
adduser openvpn --disabled-password --disabled-login  --quiet --gecos "OpenVPN User"
# Adding specific API user so it can have access to local network
adduser wepn-api --disabled-password --disabled-login --home $PPROXY_HOME/local_server --quiet --gecos "WEPN-API User"
adduser pproxy gpio 

echo -e "\nCorrecing owners..."
chown pproxy:pproxy $PPROXY_HOME
chown -R pproxy:pproxy $PPROXY_HOME/* 
chown -R pproxy:pproxy $PPROXY_HOME/.* 
mkdir -p /var/local/pproxy
mkdir -p /var/local/pproxy/shadow/
touch /var/local/pproxy/status.ini
chown pproxy:pproxy /var/local/pproxy
chown pproxy:pproxy /var/local/pproxy/*
chown pproxy:pproxy /var/local/pproxy/.*
chown pproxy:pproxy /var/local/pproxy/shadow/*

echo -e "correcting scripts that run as sudo"
for SCRIPT in ip-shadow restart-pproxy update-pproxy update-system wepn_git prevent_location_issue iptables-flush check-venv
do
	chown root:root /usr/local/sbin/$SCRIPT.sh
	chmod 755 /usr/local/sbin/$SCRIPT.sh
done
# led manager runs as service by root
# led client sends it messages via a socket
# TODO: new led user & group, put pproxy in that group, run as that
chown root:root $PPROXY_HOME/system_services/led_manager.py

cat $PPROXY_HOME/setup/sudoers > /etc/sudoers

python3 -m venv $PPROXY_VENV
source $PPROXY_VENV/bin/activate
touch $venv_flag_file

pip3 install --upgrade pip
pip3 install -r $PPROXY_HOME/setup/requirements.txt
if [ ! $? -eq 0 ]; then
	echo "Doing one-by-one pip install"
	for pkg in `cat $PPROXY_HOME/setup/requirements.txt`
	do
		pip3 install --ignore-installed $pkg
	done
fi
chown pproxy:pproxy $PPROXY_VENV
chown pproxy:pproxy $PPROXY_VENV* -R

#config initialized/fixed
mkdir -p /etc/pproxy/
chmod ugo+rx /etc/pproxy/
if [[ ! -f /etc/pproxy/config.ini ]];
then
	cp $PPROXY_HOME/setup/config.ini.orig /etc/pproxy/config.ini
	chown pproxy:pproxy /etc/pproxy/config.ini
	chmod 744 /etc/pproxy/config.ini
else
	/usr/bin/python3 $PPROXY_HOME/setup/update_config.py
fi

# this was missing when using git and not dpkg
cp /var/local/pproxy/git/home_device/etc/pproxy/acl.conf /etc/pproxy/acl.conf
chown pproxy:pproxy /etc/pproxy/*
chmod 644 /etc/pproxy/*

REMOTE_KEY=/var/local/pproxy/shared_remote_key.priv
chown pproxy:pproxy $REMOTE_KEY
chmod 0600 $REMOTE_KEY

######################################
## Add OpenVPN Users, Set it up
######################################
if [ $OVPN_ENABLED -eq 1 ]; then

	echo -e "\nSet up OpenVPN ..."

	if [[ ! -f /etc/openvpn/server.conf ]]; then 
	  echo -e "\n\nSeems like OpenVPN is not configured, initializing that now"
	  echo -e "this can take a LONG time (hours)"
	  cd $PPROXY_HOME/setup/
	  /bin/bash $PPROXY_HOME/setup/init_vpn.sh
	  cd $PPROXY_HOME/
	fi
	addgroup easy-rsa
	adduser openvpn easy-rsa
	adduser pproxy easy-rsa 
	/bin/sh /etc/init.d/openvpn restart


	chgrp easy-rsa /etc/openvpn
	chgrp easy-rsa /etc/openvpn/ca.crt 
	chgrp easy-rsa /etc/openvpn/crl.pem
	chgrp easy-rsa /etc/openvpn/openvpn-status.log 
	chgrp easy-rsa /etc/openvpn/easy-rsa/pki/* -R
	chgrp easy-rsa /etc/openvpn/easy-rsa/pki/ -R
	chgrp easy-rsa /etc/openvpn/easy-rsa/pki/private/ 
	chgrp easy-rsa /etc/openvpn/easy-rsa/pki/private/* 
	chmod g+rw /etc/openvpn/openvpn-status.log
	chmod g+rw /etc/openvpn/easy-rsa/pki/* -R
	chmod g+rwx /etc/openvpn/easy-rsa/pki/	
	chmod g+rw /etc/openvpn/crl.pem 
	chmod g+rwx /etc/openvpn/* -R
	chmod g+rwx /etc/openvpn

	chown pproxy:pproxy /etc/openvpn/easy-rsa/pki/.rnd
	chmod 600 /etc/openvpn/easy-rsa/pki/.rnd
fi


#install iptables, configure iptables for port forwarding and blocking
if [ $OVPN_ENABLED -eq 1 ]; then
	/bin/bash $PPROXY_HOME/setup/openvpn-iptables.sh
fi

##################################
# Setup DNS
# This can be used to make 
# queries faster and safer
##################################
echo "Setting up DNS (local/remote)"
systemctl enable resolvconf.service
systemctl start resolvconf.service
cat > /etc/resolvconf/resolv.conf.d/head << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
sudo resolvconf --enable-updates
sudo resolvconf -u

##################################
# Create and correct permissions
##################################

addgroup wepn-web
adduser pproxy wepn-web
adduser wepn-api wepn-web
adduser wepn-api shadow-runners
chown pproxy:shadow-runners /var/local/pproxy/shadow.db*
chmod 664 /var/local/pproxy/shadow.db*
touch /var/local/pproxy/tor.db
chown pproxy:shadow-runners /var/local/pproxy/tor.db*
chmod 664 /var/local/pproxy/tor.db*
chown pproxy:shadow-runners /var/local/pproxy/shadow/shadow.sock
chown pproxy:shadow-runners /var/local/pproxy/

##################################
# Create SSL invalid certifcates
##################################
echo -e "\n Setting up the local INVALID certificates"
echo -e "These are ONLY used for local network communications."
echo -e "Local API server will disable itself if it detects port exposure to external IP."
echo -e "See: https://go.we-pn.com/waiver-3"
cd $PPROXY_HOME/local_server/
openssl genrsa -out wepn-local.key 2048 
openssl req -new -key wepn-local.key -out wepn-local.csr -subj "/C=US/ST=California/L=California/O=WEPN/OU=Local WEPN Device/CN=invalid.com"
openssl x509 -req -days 365 -in wepn-local.csr -signkey wepn-local.key -out wepn-local.crt
openssl x509 -in wepn-local.crt -pubkey -noout \
   | openssl asn1parse -inform PEM -in - -noout -out - \
   | openssl dgst -sha256 -binary - \
   | openssl base64 > wepn-local.sig

chown wepn-api wepn-local.*
chgrp wepn-web wepn-local.* 
chgrp wepn-web . 
chmod g+r wepn-local.*
chmod g+r .

systemctl daemon-reload
systemctl enable wepn-api
systemctl enable wepn-keypad
systemctl enable wepn-leds
systemctl start wepn-api
systemctl start wepn-keypad
systemctl start wepn-leds
cd $PPROXY_HOME/setup/

##################################
# Configure ShadowSocks
##################################
echo -e "\n ShadowSocks is being set up ... "
adduser shadowsocks --disabled-password --disabled-login  --quiet --gecos "ShadowSocks User"
addgroup shadow-runners
adduser pproxy shadow-runners
adduser shadowsocks shadow-runners
addgroup wireguard-runners
adduser pproxy wireguard-runners
cp $PPROXY_HOME/setup/shadowsocks-libev-manager.service /lib/systemd/system/
cp $PPROXY_HOME/setup/shadowsocks-libev.service /lib/systemd/system/
cp $PPROXY_HOME/setup/shadowsocks-libev-manager /etc/default/
cp $PPROXY_HOME/setup/shadowsocks-libev /etc/default/
cp $PPROXY_HOME/setup/config.json /etc/shadowsocks-libev/config.json
chown shadowsocks:shadow-runners /etc/shadowsocks-libev/config.json
chmod 775 /etc/shadowsocks-libev/config.json
chown pproxy:shadow-runners /var/local/pproxy/shadow/shadow.sock
chmod 775 /var/local/pproxy/shadow/shadow.sock
chown pproxy:shadow-runners /var/local/pproxy/shadow/
chmod 775 /var/local/pproxy/shadow/
touch /var/local/pproxy/error.log
touch /var/local/pproxy/error.log.1
touch /var/local/pproxy/error.log.2
touch /var/local/pproxy/error.log.3
chown pproxy:wepn-api /var/local/pproxy/error.log*
chmod 650 /var/local/pproxy/error.log*

/bin/ln -s /etc/init.d/shadowsocks-libev /etc/rc3.d/S01shadowsocks-libev
/bin/ln -s /etc/init.d/shadowsocks-libev /etc/rc5.d/S01shadowsocks-libev
/bin/ln -s /etc/init.d/shadowsocks-libev-manager /etc/rc3.d/S01shadowsocks-libev-manager
/bin/ln -s /etc/init.d/shadowsocks-libev-manager /etc/rc5.d/S01shadowsocks-libev-manager
systemctl enable shadowsocks-libev
systemctl enable shadowsocks-libev-manager


echo -e "\n enabling i2c"
adduser pproxy i2c
adduser pproxy gpio
if grep -Fxq "dtparam=i2c_arm=on" /boot/config.txt 
then
   echo "i2c aleady enabled"
else
   echo -e 'dtparam=i2c_arm=on' >> /boot/config.txt
fi

if grep -Fxq "hdmi_force_hotplug=1" /boot/config.txt 
then
   echo "audio already rerouted"
else
   echo -e 'hdmi_force_hotplug=1' >> /boot/config.txt
   echo -e 'hdmi_force_edid_audio=1' >> /boot/config.txt
fi

if ! grep -Fq "i2c" /etc/modules 
then
   echo -e 'i2c-bcm2708' >> /etc/modules
   echo -e 'i2c-dev' >> /etc/modules
fi

echo -e "\n enabling spi"
if grep -Fxq "dtparam=spi=on" /boot/config.txt 
then
   echo "spi aleady enabled"
else
   echo -e 'dtparam=spi=on' >> /boot/config.txt
fi

echo -e "\n#### Restarting services ####"
modprobe i2c_dev
modprobe i2c_bcm2708
modprobe spi-bcm2835
chmod 0655 /etc/modprobe.d/snd-bcm2835.conf
chown root:root /etc/modprobe.d/snd-bcm2835.conf
chown root:root /etc/logrotate.conf



#######################################
# Compile and intall the setuid program
# so we don't need sudo
######################################

echo -e "\n compiling setuid"
SRUN=/usr/local/sbin/wepn-run
gcc setuid.c  -o $SRUN
chown root:wepn-web $SRUN
# setuid user, writable by root, read and execute by wepn-web group
chmod 4750 $SRUN
ls -la $SRUN

echo -e "\n done with setuid"

#######################################
# Install SeeedStudio for speakers
# This is needed for HW2 ONLY
######################################
#/bin/bash install_seeedstudio.sh



#######################################
# Install Tor
#######################################
/bin/bash install_tor.sh

#######################################
# Install Wireguard
#######################################
#/bin/bash install_wireguard.sh

usermod -a -G spi pproxy
usermod -a -G audio pproxy


if [ $OVPN_ENABLED -eq 1 ]; then
	systemctl enable openvpn
	systemctl start openvpn
else
	systemctl disable openvpn
	systemctl stop openvpn
fi

#########################################################
# TODO: this is not a good way to do this, but debhelper
# can only handle one systemctl service ATM.
# restart services independently to use this new update
########################################################

SERVICE_SH=/usr/local/pproxy/setup/set-services.sh
chmod 755 $SERVICE_SH
FLG="/var/local/pproxy/pending-set-service"
echo "1" > $FLG
chown pproxy:pproxy $FLG

########################################################
echo -e "Installation of WEPN done."
exit 0
