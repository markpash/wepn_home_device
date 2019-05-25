#!/bin/sh
CONFIG_FILE_PATH=/var/local/pproxy/
FILE=$CONFIG_FILE_PATH/$1.ovpn
cd /etc/openvpn/easy-rsa/
./easyrsa build-client-full $1 nopass

# Generates the custom client.ovpn
cp /etc/openvpn/client-common.txt $FILE
echo "remote $2 $3" >> $FILE
echo "<ca>" >> $FILE
cat /etc/openvpn/easy-rsa/pki/ca.crt >> $FILE
echo "</ca>" >> $FILE
echo "<cert>" >> $FILE
cat /etc/openvpn/easy-rsa/pki/issued/$1.crt >> $FILE
echo "</cert>" >> $FILE
echo "<key>" >> $FILE
cat /etc/openvpn/easy-rsa/pki/private/$1.key >> $FILE
echo "</key>" >> $FILE

chown pproxy.pproxy $FILE
echo "Done generating $1"
