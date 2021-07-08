PPROXY_HOME=/usr/local/pproxy/

######################################
## Add PProxy user
######################################
echo -e "\n* Configuring PProxy ... "
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
chown pproxy.pproxy $PPROXY_HOME
chown -R pproxy.pproxy $PPROXY_HOME/* 
chown -R pproxy.pproxy $PPROXY_HOME/.* 
mkdir -p /var/local/pproxy
mkdir -p /var/local/pproxy/shadow/
touch /var/local/pproxy/status.ini
chown pproxy.pproxy /var/local/pproxy
chown pproxy.pproxy /var/local/pproxy/*
chown pproxy.pproxy /var/local/pproxy/.*
chown pproxy.pproxy /var/local/pproxy/shadow/*

echo -e "correcting scripts that rung as sudo"
for SCRIPT in ip-shadow restart-pproxy update-pproxy update-system
do
	chown root.root /usr/local/sbin/$SCRIPT.sh
	chmod 755 /usr/local/sbin/$SCRIPT.sh
done

cat $PPROXY_HOME/setup/sudoers > /etc/sudoers


python3.7 -m pip install --upgrade pip
PIP=pip3
if ! command -v $PIP -V &> /dev/null
then
	PIP=/usr/local/bin/pip3
fi

$PIP install --upgrade pip
$PIP install -r $PPROXY_HOME/setup/requirements.txt

pip3 install --upgrade pip
pip3 install -r $PPROXY_HOME/setup/requirements.txt

#autostart service
chmod 0755 /etc/init.d/pproxy
/bin/ln -s /etc/init.d/pproxy /etc/rc3.d/S01pproxy
/bin/ln -s /etc/init.d/pproxy /etc/rc5.d/S01pproxy

#config initialized/fixed
mkdir -p /etc/pproxy/
chmod ugo+rx /etc/pproxy/
if [[ ! -f /etc/pproxy/config.ini ]];
then
	cp $PPROXY_HOME/setup/config.ini.orig /etc/pproxy/config.ini
	chown pproxy.pproxy /etc/pproxy/config.ini
	chmod 744 /etc/pproxy/config.ini
else
	/usr/bin/python3 $PPROXY_HOME/setup/update_config.py
fi

chown pproxy.pproxy /etc/pproxy/config.ini
chmod 744 /etc/pproxy/config.ini


######################################
## Add OpenVPN Users, Set it up
######################################
echo -e "\nSet up OpenVPN ..."

if [[ ! -f /etc/openvpn/server.conf ]]; then 
  echo -e "\n\nSeems like OpenVPN is not configured, initializing that now"
  echo -e "this can take a LONG time (hours)"
  /bin/bash $PPROXY_HOME/setup/init_vpn.sh
fi
addgroup easy-rsa
adduser openvpn easy-rsa
adduser pproxy i2c
adduser pproxy gpio
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

chown pproxy.pproxy /etc/openvpn/easy-rsa/pki/.rnd
chmod 600 /etc/openvpn/easy-rsa/pki/.rnd

#empty crontab
#add heartbeat to crontab
#add apt-get update && apt-get install pproxy-rpi to weekly crontab
/usr/bin/crontab -u pproxy $PPROXY_HOME/setup/cron
/usr/bin/crontab -u root $PPROXY_HOME/setup/cron-root
#install iptables, configure iptables for port forwarding and blocking
/bin/bash $PPROXY_HOME/openvpn-iptables.sh
chown root.root /usr/local/sbin/ip-shadow.sh
chmod 0755 /usr/local/sbin/ip-shadow.sh
chown root.root /usr/local/sbin/restart-pproxy.sh
chmod 0755 /usr/local/sbin/restart-pproxy.sh
chmod 0755 /etc/network/if-up.d/pproxy.sh
chmod 0755 /etc/network/if-down.d/pproxy.sh

##################################
# Setup DNS
# This can be used to make 
# queries faster and safer
##################################
systemctl enable bind9

if [[ ! -f /var/log/named/bind.log ]]; then 
	mkdir -p /var/log/named
	chown bind.bind /var/log/named/

	echo -e > /etc/bind/named.conf.local << EOF
//
// Do any local configuration here
//

// Consider adding the 1918 zones here, if they are not used in your
// organization
//include "/etc/bind/zones.rfc1918";
logging{
  channel simple_log {
    file "/var/log/named/bind.log" versions 3 size 5m;
    severity warning;
    print-time yes;
    print-severity yes;
    print-category yes;
  };
  category default{
    simple_log;
  };
};
EOF
fi
systemctl restart bind9

##################################
# Create SSL invalid certifcates
##################################
echo -e "\n Setting up the local INVALID certificates"
echo -e "These are ONLY used for local network communications."
echo -e "Local API server will disable itself if it detects port exposure to external IP."
addgroup wepn-web
adduser pproxy wepn-web
adduser wepn-api wepn-web
cd $PPROXY_HOME/local_server/
openssl genrsa -out wepn-local.key 2048 
openssl req -new -key wepn-local.key -out wepn-local.csr -subj "/C=US/ST=California/L=California/O=WEPN/OU=Local WEPN Device/CN=invalid.com"
openssl x509 -req -days 365 -in wepn-local.csr -signkey wepn-local.key -out wepn-local.crt

chgrp wepn-web wepn-local.* 
chgrp wepn-web . 
chmod g+r wepn-local.*
chmod g+r .
cp $PPROXY_HOME/setup/wepn-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable wepn-api
systemctl start wepn-api
cd $PPROXY_HOME/setup/

##################################
# Configure ShadowSocks
##################################
echo -e "\n ShadowSocks is being set up ... "
adduser shadowsocks --disabled-password --disabled-login  --quiet --gecos "ShadowSocks User"
addgroup shadow-runners
adduser pproxy shadow-runners
adduser shadowsocks shadow-runners
cp $PPROXY_HOME/setup/shadowsocks-libev-manager.service /lib/systemd/system/
cp $PPROXY_HOME/setup/shadowsocks-libev.service /lib/systemd/system/
cp $PPROXY_HOME/setup/shadowsocks-libev-manager /etc/default/
cp $PPROXY_HOME/setup/shadowsocks-libev /etc/default/
cp $PPROXY_HOME/setup/config.json /etc/shadowsocks-libev/config.json
chown shadowsocks.shadow-runners /etc/shadowsocks-libev/config.json
chmod 775 /etc/shadowsocks-libev/config.json
chown pproxy.shadow-runners /var/local/pproxy/shadow/shadow.sock
chmod 775 /var/local/pproxy/shadow/shadow.sock
chown pproxy.shadow-runners /var/local/pproxy/shadow/
chmod 775 /var/local/pproxy/shadow/

/bin/ln -s /etc/init.d/shadowsocks-libev /etc/rc3.d/S01shadowsocks-libev
/bin/ln -s /etc/init.d/shadowsocks-libev /etc/rc5.d/S01shadowsocks-libev
/bin/ln -s /etc/init.d/shadowsocks-libev-manager /etc/rc3.d/S01shadowsocks-libev-manager
/bin/ln -s /etc/init.d/shadowsocks-libev-manager /etc/rc5.d/S01shadowsocks-libev-manager
systemctl enable shadowsocks-libev
systemctl enable shadowsocks-libev-manager


echo -e "\n enabling i2c"
if grep -Fxq "dtparam=i2c_arm=on" /boot/config.txt 
then
   echo "i2c aleady enabled"
else
   echo -e 'dtparam=i2c_arm=on' >> /boot/config.txt
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

#######################################
# Install SeeedStudio for speakers
# This is needed for HW2
######################################
/bin/bash install_seeedstudio.sh

usermod -a -G spi pproxy
usermod -a -G audio pproxy

systemctl daemon-reload 
systemctl restart shadowsocks-libev
systemctl restart shadowsocks-libev-manager
systemctl enable wepn-api
systemctl restart wepn-api
systemctl disable wepn-keypad
systemctl disable wepn-leds
#systemctl restart wepn-keypad
/bin/sh /etc/init.d/pproxy restart


echo -e "Installation of PProxy done."
