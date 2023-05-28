status_file="/var/local/pproxy/status.ini"
source regenv/bin/activate
wepn-run 1 1
sleep 5
if grep -q CLAIMED "$status_file"; 
then
	echo "Device not unclaimed properly, doing so now"
	pytest wepn-regression.py  -vv -k 'test_login or test_unclaim'
	wepn-run 1 1
fi
while grep -q CLAIMED $status_file; do 
	echo "still claimed, waiting ... ";
	sleep 5 ; 
done
pytest wepn-regression.py -vvv -r w --retries 2 --retry-delay 30
