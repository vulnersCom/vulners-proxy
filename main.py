import argparse
import uvicorn
import routers
import common.disk_cache as dc
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi_utils.timing import add_timing_middleware
from pydantic import BaseSettings
from starlette.background import BackgroundTask
from httpx import AsyncClient
from common import __version__
from common.prepare import prepare_request
from common.loader import ModuleLoader
from common.config import logger, app_opts, vulners_api_key
from routers import Router


class Settings(BaseSettings):
    vulners_api_key: str = vulners_api_key
    vulners_host: str = "https://vulners.com"
    cache_dir: str = app_opts.get("cache_dir")


settings = Settings()
module_loader = ModuleLoader()
cache = dc.Cache(
    directory=settings.cache_dir,
)

session = AsyncClient(
    follow_redirects=True,
    http2=True,
    timeout=app_opts.getint("cache_timeout"),
)

# Dynamic routers search in path 'routers' for easy plug-in addition
router_instances = module_loader.load_classes(routers, Router)

# Application init
app = FastAPI()
for router in router_instances:
    # Pass shared commons to the routers and add them to the core app
    router.settings = settings
    router.cache = cache
    router.session = session
    router.logger = logger
    app.include_router(router)
# Timing middleware for debug purposes
add_timing_middleware(app, record=logger.debug, prefix="app_timing", exclude="untimed")


@app.get("/")
async def root():
    return {"message": "Vulners Proxy App"}


@app.get("/status")
async def status():
    return {"message": "Under construction"}


@app.get("/clear")
async def status():
    cache.clear()
    return {"message": f"Purged {cache.clear()} records"}


# Default fallback route that just transfers data to Vulners backend and back
@app.api_route("/api/v3/{dispatcher}/{dispatch_method}/", methods=["GET", "POST", "HEAD"])
async def fallback_translator(dispatcher: str, dispatch_method: str, request: Request) -> StreamingResponse:
    parameters, request_headers, endpoint_url = await prepare_request(settings, request)
    request_data = {
        'method': request.method,
         'url': endpoint_url,
        'headers': request_headers,
        'params' if request.method in ('GET', 'HEAD') else 'json': parameters
    }
    vulners_request = session.build_request(**request_data)
    vulners_response = await session.send(vulners_request, stream=True)
    return StreamingResponse(
        content=vulners_response.aiter_raw(),
        media_type=vulners_response.headers["Content-Type"],
        background=BackgroundTask(vulners_response.aclose),
        headers={
            key: vulners_response.headers[key]
            for key in vulners_response.headers
            if key.lower().startswith(("content", "x-vulners"))
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Vulners Proxy")
    parser.add_argument(
        "--version", action="version", version=f"Vulners Proxy Version: {__version__}"
    )
    parser.parse_args()
    uvicorn.run(
        "main:app",
        host=app_opts["host"],
        port=app_opts.getint("port"),
        workers=app_opts.getint("workers"),
        reload=app_opts.getboolean("reload")
    )


if __name__ == "__main__":
    main()
