* Install
sudo pip3 install pytest pytest-html pytest-dependency

Create a local_test_config.ini, and populate as few first lines of regression test file ask. Format follow configaparser ini structure, for example:

[app]
user=abcd
password=abcd

* To run tests

For local results:

> pytest wepn_regression.py --v


For an HTML result, uploadable:

> pytest wepn_regression.py --html=report.html -s

To run a subset of the tests, you can identify it as semi-regex:

> pytest wepn-regression.py  -vv -k 'test_login or test_claim'
