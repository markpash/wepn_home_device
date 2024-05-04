import sys
import os
import logging
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)

from ipw import IPW
from shadow import Shadow
from openvpn import OpenVPN
from services import Services
from device import Device

l = logging.getLogger()
ipw = IPW()
s   = Shadow(l)
o   = OpenVPN(l)
a   = Services(l)
device = Device(l)

##s.stop_all()

#s.add_user("mycertname51","0","mypass", 5134, 'en')
#a.add_user("mycertname51","127.0.0.1","mypass", 5134)
#s.add_user("mycertname21","mypass", 2134)
#s.add_user("mycertname31","mypass", 3134)#


ip_address = ipw.myip()
print(">>>>>>>>>>>> adding user ue.mp")
print(a.get_service_creds_summary("1.2.3.4"))
#s.add_user("ue.mp", ip_address ,"9628834282", 4000, 'en')#
#print(s.get_add_email_text("ue.mp",ip_address,"en"))
print(">>>>>>>>>>>> looking at list ")
#device.execute_cmd('/usr/bin/upnpc -l > /tmp/a')
#print(">>>>>>>>>>>> deleting test users")
#s.delete_user("mycertname11")
#s.delete_user("mycertname51")
#s.delete_user("mycertname21")
#o.delete_user("mycertname51")
#s.start()
#s.stop()

#print(">>>>>>>>>>getting email text for test user")

#txt, html, attachments, subject = a.get_add_email_text("mycertname51",ip_address, 'en') 
#print ("text is = " +txt)
#print("deleting user ue.mp")
#s.self_test()
#s.delete_user("ue.mp")#
#device.execute_cmd('/usr/bin/upnpc -l > /tmp/b')
