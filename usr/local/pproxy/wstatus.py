
try:
    from self.configparser import configparser
except ImportError:
    import configparser
STATUS_FILE='/var/local/pproxy/status.ini'

class WStatus:
    def __init__(self, source_file=None):
        self.status = configparser.ConfigParser()
        if source_file==None:
            source_file = STATUS_FILE
        self.status.read(source_file)
        self.source_file=source_file

    def save(self):
        #TODO: add lock checking
        if self.source_file and self.status:
            with open(self.source_file, 'w') as statusfile:
               self.status.write(statusfile)


    def has_section(self, section):
        return self.status.has_section(section)

    def add_section(self, section):
        return self.status.add_section(section)

    def set(self, field, value):
        try:
            self.set_field('status', field, value)
        except:
            print("Unknown field to write:" + field)

    def set_field(self, section, field, value):
        if not isinstance(value, str):
            value = str(value)
        self.status.set(section, field, value)
        print('setting '+field+' to '+value)


    def get(self, field):
        try:
            return self.get_field('status', field)
        except:
            print("Unknown field:" + field)
            return ""


    def get_field(self, section, field):
        try:
            return self.status.get(section, field)
        except:
            print("Unknown section/field:" + section + ":"+ field)
            return ""

