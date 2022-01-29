#!/bin/sh

if (( $# < 3 ))
then
	echo "Format: $0 username ip port"
	exit 1
fi
USERNAME=${1//[^a-zA-Z0-9_\.]/}
IP=${2//[^0-9_\.]/}
PORT=${3//[^0-9_]/}

CONFIG_FILE_PATH=/var/local/pproxy/
FILE=$CONFIG_FILE_PATH/$USERNAME.ovpn
cd /etc/openvpn/easy-rsa/
./easyrsa build-client-full $USERNAME nopass

# Generates the custom client.ovpn
cp /etc/openvpn/client-common.txt $FILE
echo "remote $IP $PORT" >> $FILE
echo "<ca>" >> $FILE
cat /etc/openvpn/easy-rsa/pki/ca.crt >> $FILE
echo "</ca>" >> $FILE
echo "<cert>" >> $FILE
cat /etc/openvpn/easy-rsa/pki/issued/$USERNAME.crt >> $FILE
echo "</cert>" >> $FILE
echo "<key>" >> $FILE
cat /etc/openvpn/easy-rsa/pki/private/$USERNAME.key >> $FILE
echo "</key>" >> $FILE

chown pproxy.pproxy $FILE
echo "Done generating $USERNAME"
