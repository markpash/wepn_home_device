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

# wait 5 mins for the device to become stable.
# also helps prevent removing pip env when filesystem
# is expanding after first boot.
sleep 300

if ! [ -f $flag_file ]; then
	need_reinstall=true
fi

if ! [ -d $PPROXY_VENV ]; then
	echo "venv missing"
	need_reinstall=true
fi

source $PPROXY_VENV/bin/activate
if [ $? -ne 0 ]; then
	echo "pip not activated"
	need_reinstall=true
fi
$PPROXY_VENV/bin/python3 -V
if [ $? -ne 0 ]; then
	echo "python missing"
	need_reinstall=true
fi

##############################################
# This part is disabled for now. Some packages
# are installed differently when installed.
##############################################
# $PPROXY_VENV/bin/pip freeze > /tmp/reqs.txt
# /usr/bin/diff /tmp/reqs.txt $PPROXY_HOME/setup/requirements.txt
# if [ $? -ne 0 ]; then
# 	echo "delta in pip packages"
# 	need_reinstall=true
# fi
##############################################


wget -q --spider http://connectivity.we-pn.com
retval=$?

until [ $retval -eq 0 ];
do
	# offline, sleep 5 seconds
	# we need this to avoid pip install without internet
	sleep 5
	wget -q --spider http://connectivity.we-pn.com
	retval=$?
done

# Disabling this check
# this has made re-insall, a very expensive process, much
# more common since ALL start failures trigger a reinstall.
#
#
# service_state=`systemctl show -p SubState --value wepn-main`

# if ! [ "$service_state" = "running" ]
# then
# 	echo "service failed: $service_state"
#	need_reinstall=true
# fi
#


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
	echo "starting post-install"
	/bin/bash $PPROXY_HOME/setup/post-install.sh
	post_pid=$!
	wait $post_pid
	echo "done installing WEPN source"
	/bin/bash $PPROXY_HOME/setup/set-services.sh
	echo "DONE restarting WEPN services"
fi
