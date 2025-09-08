import os.path
import socket
from common.config import logger, conf_catalog
from common.error import VulnersProxyException


def check_api_connectivity(settings):
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
            (settings.vulners_host, 443)
        )
        return True
    except socket.error as ex:
        logger.exception(ex)
        return False


async def get_api_key_info(cache, session, settings):
    result = cache.get(f"__{settings.vulners_api_key}")
    if not result:
        vulners_request = session.build_request(
            method="GET",
            url=f"https://{settings.vulners_host}/api/v3/apiKey/info/",
            headers={"X-API-KEY": settings.vulners_api_key},
        )
        vulners_response = await session.send(vulners_request)
        result = vulners_response.json()
        if result["result"] != "error":
            cache.set(
                f"__{settings.vulners_api_key}",
                result,
                expire=settings.api_cache_timeout,
            )
    if not result["data"].get("license_type"):
        raise VulnersProxyException(
            "Invalid ApiKey",
            f"Verify ApiKey option into `{os.path.join(*conf_catalog)}/vulners_proxy.conf` file",
        )
    return result["data"]
