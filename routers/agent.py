from fastapi import Request
from fastapi.responses import ORJSONResponse
from routers import Router
from common.prepare import prepare_request
from common.crypto import encryption_enabled, encrypt_parameters


router = Router()


@router.api_route("/api/v3/agent/update/", methods=["GET", "POST"])
async def agent_update(request: Request) -> ORJSONResponse:
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )

    if encryption_enabled:
        encrypt_parameters(request, parameters, objects=['ip', 'fqdn', 'macaddress'])
    request = router.session.build_request(
        method=request.method,
        url=endpoint_url,
        json=parameters,
        headers=request_headers,
    )
    vulners_response = await router.session.send(request)
    vulners_response.read()
    vulners_results = vulners_response.json()
    return ORJSONResponse(
        content=vulners_results,
    )


@router.api_route("/api/v3/agent/register/", methods=["GET", "POST"])
async def agent_register(request: Request) -> ORJSONResponse:
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )
    if encryption_enabled:
        encrypt_parameters(request, parameters, objects=['ipaddress', 'fqdn'])
    request = router.session.build_request(
        method=request.method,
        url=endpoint_url,
        json=parameters,
        headers=request_headers,
    )
    vulners_response = await router.session.send(request)
    return ORJSONResponse(
        content=vulners_response.read(),
    )