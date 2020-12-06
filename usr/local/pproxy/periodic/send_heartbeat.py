import sys
import os
import time
import datetime as datetime
from datetime import timedelta
import dateutil.parser
import logging.config
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
LOG_CONFIG="/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)
logger = logging.getLogger("heartbeat")
from heartbeat import HeartBeat
from wstatus import WStatus
from diag import WPDiag

port = 4099

status = WStatus(logger)
claimed=status.get('claimed')

diag = WPDiag(logger)
# True: keep waiting
# False: got it done
def get_results():
       result =  diag.fetch_port_check_results(status.get_field("port_check","experiment_number"))
       if result['finished_time'] != None:
               logger.info("test results are in")
               diag.close_test_port(port)
               status.set_field("port_check","pending", False)
               status.set_field("port_check","result", result['result']['experiment_result'])
               status.set_field("port_check","last_check", str(result['finished_time']))
               status.save()
               return False
       else:
            logger.info("still waiting for test results")
            return True 

if status.has_section("port_check"):
    last_port_check = status.get_field("port_check","last_check")
    logger.info("last port check was " + str(last_port_check))
    last_check_date = dateutil.parser.parse(last_port_check)
    logger.info("last port check was " + str(last_check_date))

    logger.info("pending test results? " + status.get_field("port_check","pending"))
    if status.get_field("port_check","pending") == "True":
       logger.debug("a test has been initiated previously, getting the results")
       get_results()
    elif last_check_date.replace(tzinfo=None) < (datetime.datetime.now().replace(tzinfo=None) + timedelta(hours = -3)):
       #results are too old, request a new one
       logger.info("port test results too old, retesting")
       diag.open_test_port(port)
       experiment_number = diag.request_port_check(port)
       if experiment_number > 0:
           logger.debug("requesting new port check: " + str(experiment_number))
           status.set_field("port_check","pending", True)
           status.set_field("port_check","experiment_number", experiment_number)
           status.save()
       else:
            logger.error("HB request to start port check returned bad id 0")

       time.sleep(15)
       i = 0
       while get_results():
            time.sleep(5)
            i += 1
            if i > 5:
                break



HEARTBEAT_PROCESS = HeartBeat(logger)
HEARTBEAT_PROCESS.send_heartbeat(int(claimed)==1)
