#!/bin/bash

# simple add user flow for wireguard
# can be improved by adding 

#sudo wg-quick down wg0
#sudo systemctl stop wg-quick@wg0

ip=`curl -s https://ip.we-pn.com`
name=$1

CLEAN=${name//_/}
CLEAN=${CLEAN// /_}
CLEAN=${CLEAN//[^a-zA-Z0-9_]/}
clean_name=`echo -n $CLEAN | tr A-Z a-z`

userdir=users/$clean_name
mkdir -p $userdir

wg genkey | tee $userdir/privatekey | wg pubkey > $userdir/publickey
priv=`cat $userdir/privatekey`
pub=`cat $userdir/publickey`

cat > $userdir/config << EOF
[Interface]
Address = 10.0.0.1/24
PrivateKey = $priv

[Peer]
PublicKey = $pub
AllowedIPs = 0.0.0.0/0
Endpoint = $ip:51820
EOF

echo sudo wg set wg0 peer $pub allowed-ips 0.0.0.0/0


wg set wg0 peer $pub allowed-ips 0.0.0.0/0
wg-quick save wg0

wepn-run 0 2 2
