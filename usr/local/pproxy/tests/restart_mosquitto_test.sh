echo `date` >> /tmp/mqtt.tests
# adjust paths here
/usr/bin/python3 test_mqtt.py

if [ $? -eq 0 ]
then
	echo "All Good"
	result="Good"
else
	echo "Need to restart"
	/usr/bin/systemctl stop mosquitto
	sleep 10
	/usr/bin/systemctl start mosquitto
	echo "Done"
	result="Bad"
fi

echo $result >> /tmp/mqtt.tests
