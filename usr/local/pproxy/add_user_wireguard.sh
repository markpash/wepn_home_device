#!/bin/bash

# simple add user flow for wireguard
# can be improved by adding 

#sudo wg-quick down wg0
#sudo systemctl stop wg-quick@wg0

ip=`curl -s https://ip.we-pn.com`
# remove trailing new line
ip=${ip//[$'\r\n ']/}
name=$1
port=$2
inv_ip_server=10.10.0.1


clean_port=${port//[^0-9]/}

CLEAN=${name//_/}
CLEAN=${CLEAN// /_}
CLEAN=${CLEAN//[^a-zA-Z0-9_\.]/}
clean_name=`echo -n $CLEAN | tr A-Z a-z`
main_users_dir=/var/local/pproxy/users
userdir=$main_users_dir/$clean_name
mkdir -p $userdir

if ! test -f $userdir/privatekey; then
	# new user

	# find an unassigned ip address
	# inspired by https://github.com/angristan/wireguard-install/blob/master/wireguard-install.sh
	USED=0
	for DOT_IP in {2..254}; do
		USED=0
		for f in `find $main_users_dir -name wg.conf`; do
			DOT_EXISTS=$(grep -sc "${inv_ip_server::-1}${DOT_IP}" "$f" )
			if [[ ${DOT_EXISTS} != '0' ]]; then
				# echo "Found $DOT_IP in $f"
				USED=1
				break
			fi
		done
		if [[ $USED == 0 ]]; then
			#echo "Found free: $DOT_IP"
			break
		fi
	done
	inv_ip=${inv_ip_server::-1}${DOT_IP}

	wg genkey | tee $userdir/privatekey | wg pubkey > $userdir/publickey
	wg genpsk > $userdir/psk
else
	if ! test -f $userdir/psk; then
		wg genpsk > $userdir/psk
	fi
	# existing user, reuse keys + invalid IP but update external IP
	inv_ip=`cat $userdir/wg.conf | grep Address | grep -Eo '[0-9\.]+' | head -1`
fi
priv=`cat $userdir/privatekey`
pub=`cat $userdir/publickey`
psk=`cat $userdir/psk`

cat > $userdir/wg.conf << EOF
[Interface]
PrivateKey = $priv
Address = $inv_ip/32
DNS = $inv_ip_server,8.8.8.8

[Peer]
PublicKey = $pub
PresharedKey = $psk
Endpoint = $ip:$clean_port
AllowedIPs = 0.0.0.0/0
EOF

#sudo wg set wg0 peer $pub preshared-key /var/local/pproxy/users/$clean_name/psk allowed-ips $inv_ip/32
wepn-run 1 6 0 $pub $clean_name $inv_ip

#sudo wg-quick save wg0
#wg-quick save wg0
wepn-run 1 7 0

wepn-run 0 2 2 0
