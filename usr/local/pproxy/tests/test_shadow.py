import logging.config
# up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
# sys.path.append(up_dir)
# above line is needed for following classes:
from shadow import Shadow  # noqa E402 need up_dir first

LOG_CONFIG = "/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG, disable_existing_loggers=False)
logger = logging.getLogger("heartbeat")


sh = Shadow(logger)
r = sh.get_usage_json()
print(r)
usage_results = sh.get_usage_status_summary()
print(usage_results)
