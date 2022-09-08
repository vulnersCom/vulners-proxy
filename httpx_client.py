import ssl
import httpcore
import httpx
import asyncio
from common.config import logger, app_opts
from common.error import VulnersProxyException


class HttpXClient(httpx.AsyncClient):
    default_timeout = float(app_opts["ApiRequestTimeout"])

    def build_request(self, *args, timeout=None, **kwargs) -> httpx._models.Request:
        timeout = timeout or self.default_timeout
        return super().build_request(*args, timeout=timeout, **kwargs)

    async def send(self, *args, **kwargs) -> httpx._models.Response:
        try:
            return await super().send(*args, **kwargs)
        except (
            ssl.SSLWantReadError,
            TimeoutError,
            httpcore.ReadTimeout,
            httpx.ReadTimeout,
            asyncio.exceptions.CancelledError,
        ) as err:
            logger.exception(err)
            raise VulnersProxyException(
                "Api request timeout has been reached",
                "Perhaps the request is too large, try increasing ApiRequestTimeout option in the config file"
            )
