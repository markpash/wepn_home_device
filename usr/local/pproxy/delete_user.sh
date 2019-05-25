#!/bin/sh
cd /etc/openvpn/easy-rsa/
./easyrsa --batch revoke $1
./easyrsa gen-crl
rm -rf pki/reqs/$1.req
rm -rf pki/private/$1.key
rm -rf pki/issued/$1.crt
rm -rf /etc/openvpn/crl.pem
cp /etc/openvpn/easy-rsa/pki/crl.pem /etc/openvpn/crl.pem
#if user is currently connected, restart server so they get kicked out
if grep "$1" /etc/openvpn/openvpn-status.log
then
    /etc/init.d/openvpn restart
fi
