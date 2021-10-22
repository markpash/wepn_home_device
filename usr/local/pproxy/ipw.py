import requests


class IPW():
    def myip(self):
        # get the ip.we-pn.com IP
        try:
            f = requests.get('http://ip.we-pn.com')
            ip = str(f.text).rstrip()
            # check if it is valid, not a dupe
            return ip
        except OSError:
            print("Error in connection to IP resolver service")
            pass
        return 0
