try:
    from self.configparser import configparser
except ImportError:
    import configparser
STATUS_FILE = '/var/local/pproxy/status.ini'


class WStatus:
    def __init__(self, logger, source_file=None):
        self.status = configparser.ConfigParser()
        self.logger = logger
        if source_file is None:
            source_file = STATUS_FILE
        self.status.read(source_file)
        self.source_file = source_file

    def save(self):
        # TODO: add lock checking
        if self.source_file is not None and self.status is not None:
            self.logger.info("writing status file")
            try:
                statusfile = open(self.source_file, 'w')
                self.status.write(statusfile)
                statusfile.close()
            except Exception as err:
                self.logger.debug(
                    "Something happened when writing status file:" + str(err))

    def reload(self):
        self.status.read(self.source_file)

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
        self.logger.debug('setting ' + field + ' to ' + value)

    def get(self, field):
        try:
            return self.get_field('status', field)
        except:
            self.logger.error("Unknown field: " + field)
            return ""

    def get_field(self, section, field):
        try:
            return self.status.get(section, field)
        except:
            self.logger.error("Unknown section/field: "
                              + section + ":" + field)
            return ""
