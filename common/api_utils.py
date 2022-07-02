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
    if not (result := cache.get(f"__{settings.vulners_api_key}")):
        vulners_request = session.build_request(
            method="GET",
            url=f"https://{settings.vulners_host}/api/v3/apiKey/info/",
            params={"apiKey": settings.vulners_api_key},
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


async def get_cached_cost(cache, license_type, session, settings, statistics):
    if not (cost_data := cache.get(f"__{license_type}_costs")):
        vulners_request = session.build_request(
            method="GET",
            url=f"https://{settings.vulners_host}/api/v3/credit/get_requests_cost",
        )
        vulners_response = await session.send(vulners_request)
        for license_costs in vulners_response.json()["data"]["costs"]:
            if license_costs["license"] != license_type:
                continue
            cost_data = license_costs["costs"]
            cache.set(
                f"__{license_type}_costs", cost_data, expire=settings.api_cache_timeout
            )
            break
        else:
            raise VulnersProxyException(
                "Invalid license", "Please contact us support@vulners.com"
            )
    result = 0
    for endpoint, count in list(statistics.items()):
        result += count * cost_data.get(endpoint, 0)
    return result
