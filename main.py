from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import StreamingResponse
from fastapi_utils.timing import add_timing_middleware
from pydantic import BaseSettings
from starlette.background import BackgroundTask
from httpx import AsyncClient
from common.prepare import prepare_request
import common.diskcache as dc
import logging
from common.loader import ModuleLoader
import routers

# Shared commons goes first

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    vulners_api_key: str = ""
    vulners_host: str = "https://vulners.com"
    cache_dir: str = "/tmp/vulners-proxy.cache/"
    cache_timeout: int = 10

settings = Settings()
module_loader = ModuleLoader()
cache = dc.Cache(
    directory = settings.cache_dir,
)

session = AsyncClient(
    follow_redirects=True,
    http2 = True,
)

# Dynamic routers search in path 'routers' for easy plug-in addition
router_instances = module_loader.load_classes(routers, APIRouter)

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
add_timing_middleware(app, record=logger.info, prefix="app", exclude="untimed")

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
@app.api_route("/api/v3/{dispatcher}/{dispatch_method}/", methods=['GET','POST'])
async def fallback_translator(dispatcher: str, dispatch_method:str, request: Request):
    parameters, request_headers, endpoint_url = await prepare_request(settings, request)
    if request.method in ['GET', 'HEAD']:
        vulners_request = session.build_request(method=request.method,
                                        url=endpoint_url,
                                        params=parameters,
                                        headers=request_headers
                                        )
    else:
        vulners_request = session.build_request(method=request.method,
                                                url=endpoint_url,
                                                json=parameters,
                                                headers=request_headers
                                                )
    vulners_response = await session.send(vulners_request, stream=True)
    return StreamingResponse(
            content=vulners_response.aiter_raw(),
            media_type=vulners_response.headers['Content-Type'],
            background=BackgroundTask(vulners_response.aclose),
            headers = dict((k,vulners_response.headers[k]) for k in vulners_response.headers if k.lower().startswith(("x-vulners","content"))),
            )
