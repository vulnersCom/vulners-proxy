import binascii
from fastapi import Request
from fastapi.responses import ORJSONResponse
from routers import Router
from common import config
from common.prepare import prepare_request
from common.crypto import encryption_enabled, decrypt


router = Router()


@router.api_route("/api/v3/reports/vulnsreport/", methods=["POST"])
async def reports_vulnsreport(request: Request) -> ORJSONResponse:
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )

    if config.vulners_report_filter_enabled:
        if "filter" in parameters:
            parameters['filter']['tags'] = [config.vulners_report_filter] + parameters['filter'].get('tags', [])
        else:
            parameters['filter'] = {'tags': [config.vulners_report_filter]}
    request = router.session.build_request(
        method=request.method,
        url=endpoint_url,
        json=parameters,
        headers=request_headers,
    )
    vulners_response = await router.session.send(request)
    vulners_response.read()
    vulners_results = vulners_response.json()

    if encryption_enabled and vulners_results["result"] == 'OK':
        for report in vulners_results["data"].get("report", []):
            for key in ("agentip", "agentfqdn", "ipaddress", "fqdn"):
                value = report.get(key)
                if value:
                    try:
                        report[key] = decrypt(value)
                    except binascii.Error:
                        continue
    return ORJSONResponse(
        content=vulners_results,
    )
