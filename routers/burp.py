from fastapi import Request
from fastapi.responses import ORJSONResponse
from routers import Router
from common.prepare import prepare_cache_keys, prepare_request, merge_value_to_key

# search/id call local cache optimization

router = Router()

@router.api_route("/api/v3/burp/softwareapi/", methods=["GET", "POST"])
async def burp_software(request: Request):
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )
    software_call_key = prepare_cache_keys(parameters.values())
    cached_response = router.cache.get(software_call_key)
    if not cached_response:
        request = router.session.build_request(
            method=request.method, url=endpoint_url, json=parameters, headers=request_headers
        )
        vulners_response = await router.session.send(request)
        vulners_response.read()
        vulners_results = vulners_response.json()
        router.cache.set(
            software_call_key, vulners_results, expire=router.settings.cache_timeout
        )
    else:
        router.statistics[dispatcher] += 1
        vulners_results = cached_response
    return ORJSONResponse(
        content=vulners_results,
    )


@router.api_route("/api/v3/burp/software/", methods=["GET", "POST"])
async def burp_software(request: Request):
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )
    software_call_key = prepare_cache_keys(parameters.values())
    cached_response = router.cache.get(software_call_key)
    if not cached_response:
        request = router.session.build_request(
            method=request.method, url=endpoint_url, json=parameters, headers=request_headers
        )
        vulners_response = await router.session.send(request)
        vulners_response.read()
        vulners_results = vulners_response.json()
        router.cache.set(
            software_call_key, vulners_results, expire=router.settings.cache_timeout
        )
    else:
        router.statistics[dispatcher] += 1
        vulners_results = cached_response
    return ORJSONResponse(
        content=vulners_results,
    )


@router.api_route("/api/v3/burp/packages/", methods=["GET", "POST"])
async def burp_packages(request: Request):
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )

    packages_list = parameters.get("packages", [])
    software_keys = {
        merge_value_to_key(
            package["software"].lower(),
            package["version"].lower(),
            parameters.get("os"),
            parameters.get("osVersion"),
        ): package
        for package in packages_list
    }
    cached_data = router.cache.get_many(software_keys)
    cached_packages = [software_keys[_] for _ in cached_data]
    uncached_packages = [
        package
        for package in packages_list
        if package not in cached_packages
    ]
    parameters["packages"] = uncached_packages
    if uncached_packages:
        # Perform minimized vulners request
        request = router.session.build_request(
            method="POST", url=endpoint_url, json=parameters, headers=request_headers
        )
        vulners_response = await router.session.send(request)
        vulners_response.read()
        vulners_results = vulners_response.json()
        set_many_packages = {}
        for package_vulnerabilities in vulners_results["data"]["vulnerabilities"]:
            cache_key = merge_value_to_key(
                package_vulnerabilities["package"].lower(),
                package_vulnerabilities["version"].lower(),
                parameters.get("os"),
                parameters.get("osVersion"),
            )
            set_many_packages[cache_key] = package_vulnerabilities
        router.cache.set_many(set_many_packages, expire=router.settings.cache_timeout)
        # Cache the data
    else:
        router.statistics[dispatcher] += 1
        vulners_results = {
            "result": "OK",
            "data": {
                "vulnerabilities": [],
            },
        }
    # Inject cached data to Vulners response
    vulners_results["data"]["vulnerabilities"] += cached_data.values()

    return ORJSONResponse(
        content=vulners_results,
    )
