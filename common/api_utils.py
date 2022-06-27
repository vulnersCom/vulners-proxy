import socket
import main
from common.config import logger


def check_api_connectivity():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((main.settings.vulners_host, 443))
        return True
    except socket.error as ex:
        logger.exception(ex)
        return False


async def get_api_key_info():
    vulners_request = main.session.build_request(
        method='GET',
        url=f'https://{main.settings.vulners_host}/api/v3/apiKey/info/',
        params={'apiKey': main.settings.vulners_api_key}
    )
    vulners_response = await main.session.send(vulners_request)
    return vulners_response.json().pop("data")
