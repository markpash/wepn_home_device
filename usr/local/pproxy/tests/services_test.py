import sys
import os
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)

from ipw import IPW
from shadow import Shadow
from openvpn import OpenVPN
from services import Services
from device import Device

ipw = IPW()
s   = Shadow()
o   = OpenVPN()
a   = Services()
device = Device()

#s.add_user("mycertname51","0","mypass", 5134)
#a.add_user("mycertname51","127.0.0.1","mypass", 5134)
#s.add_user("mycertname21","mypass", 2134)
#s.add_user("mycertname31","mypass", 3134)#
print(">>>>>>>>>>>> deleting a test user")
s.delete_user("ue.mp")#
ip_address = ipw.myip()
print(">>>>>>>>>>>> adding user ue.mp")
s.add_user("ue.mp", ip_address ,"9628834282", 4000)#
print(">>>>>>>>>>>> looking at list ")
device.execute_cmd('/usr/bin/upnpc -l > /tmp/a')
print(">>>>>>>>>>>> deleting test users")
s.delete_user("mycertname11")
s.delete_user("mycertname51")
s.delete_user("mycertname21")
#o.delete_user("mycertname51")
s.start()
s.stop()

print(">>>>>>>>>>getting email text for test user")

txt, html = a.get_add_email_text("mycertname51",ip_address) 
print (txt)
print("deleting user ue.mp")
s.delete_user("ue.mp")#
device.execute_cmd('/usr/bin/upnpc -l > /tmp/b')
