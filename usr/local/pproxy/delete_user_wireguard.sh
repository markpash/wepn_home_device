#!/bin/bash

if [ $# -eq 0 ]
then
	echo "provide peer alias"
else
	pub=`cat users/$1/publickey`
	wg set wg0 peer $pub remove
	wg show
	rm -rf users/$1/
	wg-quick save wg0
	wepn-run 0 2 2
fi
