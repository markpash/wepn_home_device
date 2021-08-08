
python3 rec.py
echo -e "Recording done, playing it back.\n"
mic_left=5
mic_right=5
/usr/bin/play left.wav
echo -e "Did you hear left? [y/n]\n"
read mic_test
case $mic_test in
	y ) 
		mic_left=0
		;;
	n ) 
		mic_left=1 
		;;
esac
/usr/bin/play right.wav

echo -e "Did you hear right? [y/n]\n"
read mic_test
case $mic_test in
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

exit $mic
