from shadow import Shadow
import sys
import os
import logging
import logging.config
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)


LOG_CONFIG = "/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)

logger = logging.getLogger("recovery")
shadow_server = Shadow(logger)
shadow_server.recover_missing_servers()
