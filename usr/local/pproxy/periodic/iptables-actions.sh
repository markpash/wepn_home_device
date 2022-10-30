#!/bin/bash
ROOT=/usr/local/sbin/

cd $ROOT
# flush old rules
/usr/local/sbin/wepn-run 1 8 
# add tor redirects for go.we-pn.com/wrong-location
/usr/local/sbin/wepn-run 1 9

# block access to local ip addresses by remote connections
# /usr/local/sbin/wepn-run 1 10

