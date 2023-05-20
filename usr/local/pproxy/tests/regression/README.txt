* Install
virtualenv regenv
source regenv/bin/activate
pip3 install -r requirements.txt

Create a local_test_config.ini, and populate as few first lines of regression test file ask. Format follow configaparser ini structure, for example:

```
[user]
token=abcdefg
user=regression@we-pn.com
password=samplepassword

[app]
authorization_base_url = https://api.we-pn.com/o/token/
client_id=clientidfromdjango
client_secret=clientsecretfromdjango

[device]
url=https://api.we-pn.com/api
key=keythatworks
serial=ABCDEFG

[friend]
static_id=123
```

* To run tests

For local results:

> pytest wepn-regression.py --v


For an HTML result, uploadable:

> pytest wepn-regression.py --html=report.html -s

To run a subset of the tests, you can identify it as semi-regex:

> pytest wepn-regression.py  -vv -k 'test_login or test_claim'

