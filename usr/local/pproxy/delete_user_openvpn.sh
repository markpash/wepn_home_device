#!/bin/sh
if (( $# < 1 ))
then
	echo "Format: $0 username"
	exit 1
fi
cd /etc/openvpn/easy-rsa/
USERNAME=${1//[^a-zA-Z0-9_\.]/}
./easyrsa --batch revoke $USERNAME
./easyrsa gen-crl
rm -rf pki/reqs/$USERNAME.req
rm -rf pki/private/$USERNAME.key
rm -rf pki/issued/$USERNAME.crt
rm -rf /etc/openvpn/crl.pem
cp /etc/openvpn/easy-rsa/pki/crl.pem /etc/openvpn/crl.pem
#if user is currently connected, restart server so they get kicked out
if grep "$USERNAME" /etc/openvpn/openvpn-status.log
then
    /etc/init.d/openvpn restart
fi
