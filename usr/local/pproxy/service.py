try:
    from configparser import configparser
except ImportError:
    import configparser
from wstatus import WStatus

CONFIG_FILE = '/etc/pproxy/config.ini'
# setuid command runner
SRUN = "/usr/local/sbin/wepn-run"


class Service:
    def __init__(self, name, logger):
        self.name = name
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.wstatus = WStatus(logger)
        self.logger = logger
        return

    def add_user(self, certname, ip_address, password, port, lang):
        return False

    def delete_user(self, certname):
        return

    def start(self):
        return

    def stop(self):
        return

    def restart(self):
        self.stop_all()
        self.start_all()

    def reload(self):
        pass

    def get_config_section_name(self):
        if self.name == "shadowsocks":
            service_config_name = "shadow"
        else:
            service_config_name = self.name
        return service_config_name

    def is_enabled(self):
        # TODO: this is a workaround until we update service name everywhere
        service_config_name = self.get_config_section_name()
        if self.config.has_section(service_config_name):
            service_present = (int(self.config.get(service_config_name, 'enabled')) == 1)
            service_active = self.wstatus.get_service_status(self.name)
            return service_present and service_active
        else:
            return False

    def set_enabled(self, is_enabled):
        previously_enabled = self.is_enabled()
        self.wstatus.set_service_status(self.get_config_section_name(), is_enabled)
        self.wstatus.save()
        if is_enabled and not previously_enabled:
            self.start()
        if not is_enabled and previously_enabled:
            self.stop()

    def can_email(self):
        if self.config.has_section(self.get_config_section_name()):
            return (int(self.config.get(self.get_config_section_name(), 'email')) == 1)
        else:
            return False

    def get_service_creds_summary(self, ip_address):
        return {}

    def get_usage_status_summary(self):
        return {}

    def get_usage_daily(self):
        return {}

    def get_short_link_text(self, cname, ip_address):
        return ""

    def get_add_email_text(self, certname, ip_address, lang, is_new_user=False):
        txt = ''
        html = ''
        subject = ''
        attachments = []
        return txt, html, attachments, subject

    def get_removal_email_text(self, certname, ip_address):
        txt = ''
        html = ''
        subject = ''
        attachments = []
        return txt, html, attachments, subject

    def get_access_link(self, cname):
        return None

    def execute_setuid(self, cmd):
        return self.execute_cmd(SRUN + " " + cmd)

    def execute_cmd(self, cmd):
        pass

    def recover_missing_servers(self):
        return

    def self_test(self):
        return True

    def configure(self, config_data):
        self.logger.error("configuring with : " + str(config_data))
        if "enabled" in config_data:
            self.set_enabled(config_data["enabled"])

    def backup_restore(self):
        return True
