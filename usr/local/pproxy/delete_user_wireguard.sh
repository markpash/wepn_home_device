#!/bin/bash

name=$1
CLEAN=${name//_/}
CLEAN=${CLEAN// /_}
CLEAN=${CLEAN//[^a-zA-Z0-9_\.]/}
clean_name=`echo -n $CLEAN | tr A-Z a-z`
userdir=/var/local/pproxy/users/$clean_name

if [ $# -eq 0 ]
then
	echo "provide peer alias"
else
	pub=`cat $userdir/publickey`
	echo wg set wg0 peer $pub remove
	# wg set wg0 peer $pub remove
	wepn-run 1 17 0 $pub
	rm $userdir/wg.conf
	rm $userdir/privatekey
	rm $userdir/publickey
	rm $userdir/psk
	rmdir $userdir/
	echo wg-quick save wg0
	wepn-run 1 7 0
	wepn-run 0 2 2 0
fi
