import os
import logging
import configparser


conf_catalog = '/etc/vulners_proxy',

if DEBUG := False:
    conf_catalog = os.path.dirname(__file__), os.path.pardir

CONF_PATH = os.path.join(*conf_catalog, 'example_vulners_proxy.conf')

config = configparser.ConfigParser()
config.read(CONF_PATH)

log_opts = config['logging']
app_opts = config['app']
vulners_api_key = config['vulners']['apikey']

if not (log_file := log_opts.get('LogFile')):
    log_file = '/var/log/vulners_proxy/vulners_proxy.log'

logging.basicConfig(
    filename=log_file,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    level=getattr(logging, log_opts.get('LogLevel', 'INFO').upper())
)
logger = logging.getLogger('vulners_proxy')
