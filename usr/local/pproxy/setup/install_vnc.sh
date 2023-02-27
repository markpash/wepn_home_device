#!/bin/bash

# password comes in as param
password=$1

# install the packages
# this cannot be done within post-install of anotehr package
# apt install realvnc-vnc-server

# create the passwrod and store in user config
# we are using user pi
echo $password | vncpasswd -service

#enable vnc auth 
vnc_file=/root/.vnc/config.d/vncserver-x11

cat >$vnc_file<<EOF
Authentication=VncAuth
EOF

# enable the service
