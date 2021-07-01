print_result () {
	if [ $2 -eq 0 ]; then
	   echo -e "\e[39m$1 \t\t\t\t\t [ \e[32mOK \e[39m]"
	else
	   echo -e "\e[39m$1 \t\t\t\t\t [ \e[91mFAIL \e[39m]"
	fi
}


echo -e "\n\n========= Starting Basic Test ============"
python3 device_test.py
device=$?
#read -p "Press any key for LCD test" -n1 -s
echo -e "\n\n========= Starting LCD Test ============"
python3 test_lcd.py
lcd=$?

#read -p "Press any key for temperature test" -n1 -s
echo -e "\n\n========= Startingtemparture Sensor Test ============"
python3 test_temperature.py
temp=$?

#read -p "Press any key for buttons test" -n1 -s
echo -e "\n\n========= Startin Buttons Test ============"
python3 test_buttons.py
buttons=$?

#read -p "Press any key for LED test" -n1 -s
echo -e "\n\n========= Starting LED Test ============"
python3 test_led.py
led=$?

#read -p "Press any key for light sensor test" -n1 -s
echo -e "\n\n========= Starting Light Sensor Test ============"
python3 test_ambient.py
ambient=$?

echo -e "\n\n========= Starting speaker Test ============"
/usr/bin/play stereo-test.wav
speaker=5
echo -e "Did you hear left and right sounds? [y/n]\n"
read speaker_test
case $speaker_test in
	y ) 
		speaker=0
		;;
	n ) 
		speaker=1 
		;;
esac
echo -e "Speaker test result:" $speaker

echo -e "\n\n========= Starting microhpne Test ============"
python3 rec.py
echo -e "Recording done, playing it back.\n"
mic_left=5
mic_right=5
/usr/bin/play left.wav
echo -e "Did you hear left? [y/n]\n"
read speaker_test
case $speaker_test in
	y ) 
		mic_left=0
		;;
	n ) 
		mic_left=1 
		;;
esac
/usr/bin/play right.wav

echo -e "Did you hear right? [y/n]\n"
read speaker_test
case $speaker_test in
	y ) 
		mic_right=0
		;;
	n ) 
		mic_right=1 
		;;
esac
mic=5

if [ $mic_left -eq 0 ] && [ $mic_right -eq 0 ]
then
	mic=0
else
	mic=1
fi

echo -e "\n\n======== Test Results  ============"
print_result "Device     " $device
print_result "LCD        " $lcd
print_result "LED        " $led
print_result "Temperature" $temp
print_result "Buttons    " $buttons
print_result "Speaker    " $speaker
print_result "Microhpne  " $mic 
print_result "Light Sensor  " $ambient 
