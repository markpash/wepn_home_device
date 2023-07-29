#!/bin/bash

name=$1
CLEAN=${name//_/}
CLEAN=${CLEAN// /_}
CLEAN=${CLEAN//[^a-zA-Z0-9_]/}
clean_name=`echo -n $CLEAN | tr A-Z a-z`
userdir=users/$clean_name

if [ $# -eq 0 ]
then
	echo "provide peer alias"
else
	pub=`cat users/$userdir/publickey`
	echo wg set wg0 peer $pub remove
	wg set wg0 peer $pub remove
	echo wg show
	wg show
	rm $userdir/wg.conf
	rm $userdir/privatekey
	rm $userdir/publickey
	rmdir $userdir/
	echo wg-quick save wg0
	wepn-run 1 7
	wepn-run 0 2 2
fi
