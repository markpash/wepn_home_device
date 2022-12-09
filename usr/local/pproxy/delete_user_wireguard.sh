#!/bin/bash

if [ $# -eq 0 ]
then
	echo "provide peer alias"
else
	pub=`cat users/$1/publickey`
	echo wg set wg0 peer $pub remove
	wg set wg0 peer $pub remove
	echo wg show
	wg show
	rm -rf users/$1/
	echo wg-quick save wg0
	wepn-run 1 7
	wepn-run 0 2 2
fi
