import sys
import os
import signal
import select
import time
import argparse
from subprocess import Popen, PIPE
import urllib.request 
import requests

class IPW():
    def myip(self):
        #get the ip.we-pn.com IP
        #data = urllib.request.urlopen('http://ip.we-pn.com')
        try:
          f = requests.get('http://ip.we-pn.com')
          #ip = data.readline();
          ip = str(f.text).rstrip()
          #check if it is valid, not a dupe
          return ip 
        except OSError:
          print("Error in connection to IP resolver service")
          pass
        return 0
