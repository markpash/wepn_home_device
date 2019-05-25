
try:
    from self.configparser import configparser
except ImportError:
    import configparser
STATUS_FILE='/var/local/pproxy/status.ini'

class WStatus:
    def __init__(self):
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        print(self.status.get('status','claimed'))

    def save(self):
        #TODO: add lock checking
        with open(STATUS_FILE, 'w') as statusfile:
           self.status.write(statusfile)


    def set(self,field,value):
        if not isinstance(value, str):
            value = str(value)
        self.status.set('status', field, value)
        print('setting '+field+' to '+value)


    def get(self, field):
        try:
            return self.status.get('status',field)
        except:
            print("Unknown field:" + field)
            return ""

