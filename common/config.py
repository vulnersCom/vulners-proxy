import configparser
import logging
import os

conf_catalog = ("/etc/vulners_proxy",)

DEBUG = False
if DEBUG:
    conf_catalog = os.path.dirname(__file__), os.path.pardir

CONF_PATH = os.path.join(*conf_catalog, "vulners_proxy.conf")

config = configparser.ConfigParser(inline_comment_prefixes=("#",))
config.read(CONF_PATH)

log_opts = config["logging"]
app_opts = config["app"]
vulners_api_key = config["vulners"]["apikey"]
vulners_report_filter_enabled = int(config["vulners"].get("enablereportfilter", "0"))
vulners_report_filter = config["vulners"].get("reportfiltertag", "")

log_file = log_opts.get("LogFile")
if not log_file:
    log_file = "/var/log/vulners_proxy/vulners_proxy.log"

os.makedirs(os.path.split(log_file)[0], exist_ok=True)

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=getattr(logging, log_opts.get("LogLevel", "INFO").upper()),
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger("vulners_proxy")
