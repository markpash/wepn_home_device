######################################
## Add PProxy user
######################################
echo "Configuring PProxy ... "
echo "Adding users"
adduser pproxy --disabled-password --disabled-login --home /usr/local/pproxy --quiet --gecos "PPROXY User"
adduser openvpn --disabled-password --disabled-login  --quiet --gecos "OpenVPN User"
adduser pproxy gpio 
echo "Correcing owners..."
chown pproxy.pproxy /usr/local/pproxy
chown -R pproxy.pproxy /usr/local/pproxy/* 
chown -R pproxy.pproxy /usr/local/pproxy/.* 
mkdir -p /var/local/pproxy
mkdir -p /var/local/pproxy/shadow/
touch /var/local/pproxy/status.ini
chown pproxy.pproxy /var/local/pproxy
chown pproxy.pproxy /var/local/pproxy/*
chown pproxy.pproxy /var/local/pproxy/.*
chown pproxy.pproxy /var/local/pproxy/shadow/*
cat /usr/local/pproxy/setup/sudoers > /etc/sudoers



/usr/bin/pip3 install -r /usr/local/pproxy/setup/requirements.txt

#autostart service
/bin/ln -s /etc/init.d/pproxy /etc/rc3.d/S01pproxy
/bin/ln -s /etc/init.d/pproxy /etc/rc5.d/S01pproxy

#config initialized/fixed
mkdir -p /etc/pproxy/
chmod ugo+rx /etc/pproxy/
if [[ ! -f /etc/pproxy/config.ini ]];
then
	cp /usr/local/pproxy/config.ini.orig /etc/pproxy/config.ini
	chown pproxy.pproxy /etc/pproxy/config.ini
	chmod 744 /etc/pproxy/config.ini
else
	/usr/bin/python3 /usr/local/pproxy/setup/update_config.py
fi

chown pproxy.pproxy /etc/pproxy/config.ini
chmod 744 /etc/pproxy/config.ini


######################################
## Add OpenVPN Users, Set it up
######################################
echo "Set up OpenVPN ..."

if [[ ! -f /etc/openvpn/server.conf ]]; then 
  echo "Seems like OpenVPN is not configured, initializing that now"
  /bin/bash /usr/local/pproxy/setup/init_vpn.sh
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
/usr/bin/crontab -u pproxy /usr/local/pproxy/setup/cron
/usr/bin/crontab -u root /usr/local/pproxy/setup/cron-root
#install iptables, configure iptables for port forwarding and blocking
/bin/bash /usr/local/pproxy/openvpn-iptables.sh
chown root.root /usr/local/sbin/ip-shadow.sh
chmod 0755 /usr/local/sbin/ip-shadow.sh
chown root.root /usr/local/sbin/restart-pproxy.sh
chmod 0755 /usr/local/sbin/restart-pproxy.sh
chmod 0755 /etc/network/if-up.d/pproxy.sh
chmod 0755 /etc/network/if-down.d/pproxy.sh

##################################
# Setup DNS
##################################
systemctl enable bind9
systemctl start bind9

##################################
#Configure ShadowSocks
##################################
echo "echo ShadowSocks is being set up ... "
adduser shadowsocks --disabled-password --disabled-login  --quiet --gecos "ShadowSocks User"
addgroup shadow-runners
adduser pproxy shadow-runners
adduser shadowsocks shadow-runners
cp /usr/local/pproxy/setup/shadowsocks-libev-manager.service /lib/systemd/system/
cp /usr/local/pproxy/setup/shadowsocks-libev.service /lib/systemd/system/
cp /usr/local/pproxy/setup/shadowsocks-libev-manager /etc/default/
cp /usr/local/pproxy/setup/shadowsocks-libev /etc/default/
cp /usr/local/pproxy/setup/config.json /etc/shadowsocks-libev/config.json
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


echo "enabling i2c"
if grep -Fq "#dtparam=i2c_arm=on" /boot/config.txt 
then
   echo 'dtparam=i2c_arm=on' >> /boot/config.txt
fi

if ! grep -Fq "i2c" /etc/modules 
then
   echo 'i2c-bcm2708' >> /etc/modules
   echo 'i2c-dev' >> /etc/modules
fi


echo "Restarting services"
modprobe i2c_dev
modprobe i2c_bcm2708

systemctl restart shadowsocks-libev
systemctl restart shadowsocks-libev-manager
/bin/sh /etc/init.d/pproxy restart

echo "Installation of PProxy done."
