This is a simple Flask based API, similar to what runs on the device.
This version reads config from test_config.ini, and returns status dictionary defined in it for status.

== Installation == 
virtualenv wepn_api_dummy_venv
source wepn_api_dummy_venv/bin/activate
pip install -r requirements.txt


== Running == 
python dummy_api.py


This will start the flask server. Now, assuming your device is on ip address 192.168.1.2 you can access:

https://192.168.1.2:5000/

to see a "Hello World" message.

https://192.168.1.2:5000/api/v1/claim/info

this will show a json like this:

{"claimed":"0", "serial_number": "CHANGE_SERIALNUM", "device_key":"ABC1DEF2GH3"}

More API dummies will be added.
