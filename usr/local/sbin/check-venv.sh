#!/bin/bash
need_reinstall=false
add_flag=true
PPROXY_HOME=/usr/local/pproxy/
PPROXY_VENV=/var/local/pproxy/wepn-env
flag_file=/var/local/pproxy/wepn-venv-installed

installer_pid=`ps -ef | grep post-install | grep -v grep | tr -s ' ' | cut -d ' ' -f2`

if ! [ -z $installer_pid ]; then
	wait $installer_pid
fi

if ! [ -f $flag_file ]; then
	need_reinstall=true
fi

if ! [ -d $PPROXY_VENV ]; then
	need_reinstall=true
fi

source $PPROXY_VENV/bin/activate
if [ $? -ne 0 ]; then
	need_reinstall=true
fi
$PPROXY_VENV/bin/python3 -V
if [ $? -ne 0 ]; then
	need_reinstall=true
fi

wget -q --spider http://connectivity.we-pn.com
retval=$?

until [ $retval -eq 0 ];
do
	# offline, sleep 5 seconds
	sleep 5
	wget -q --spider http://connectivity.we-pn.com
	retval=$?
done



if [ "$need_reinstall" = true ]; then
	/usr/bin/python3 -m venv --clear $PPROXY_VENV
	pip_pid=$!
	wait $pip_pid
	if [ "$add_flag" = true ]; then
		touch $flag_file
	fi
	source $PPROXY_VENV/bin/activate
	#pip3 install -r $PPROXY_HOME/setup/requirements.txt
	#pip_pid=$!
	#wait $pip_pid
	chown pproxy:shadow-runners $PPROXY_VENV
	chown pproxy:shadow-runners $PPROXY_VENV/* -R
	echo "done installing venv"
	/bin/bash $PPROXY_HOME/setup/post-install.sh
	echo "done installing WEPN source"
	post_pid=$!
	wait $post_pid
	/bin/bash $PPROXY_HOME/setup/set-services.sh
	echo "DONE restarting WEPN services"
fi
