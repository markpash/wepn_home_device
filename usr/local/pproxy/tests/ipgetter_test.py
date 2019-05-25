import sys
import os
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
from ipw import IPW
ipw= IPW()

ip = ipw.myip()
print(ip)
