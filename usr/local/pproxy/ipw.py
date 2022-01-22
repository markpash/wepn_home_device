import requests
import re


class IPW():
    def myip(self):
        # get the ip.we-pn.com IP
        try:
            f = requests.get('http://ip.we-pn.com')
            ip = str(f.text).rstrip()
            # check if it is valid, not an error message
            regex = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
            if re.search(regex, ip):
                return ip
            else:
                print("Not a valid ipv4 address")
                return "127.0.0.1"
        except OSError:
            print("Error in connection to IP resolver service")
            pass
        return 0
