from fastapi import Request
from fastapi.responses import ORJSONResponse
from routers import Router
from common.prepare import prepare_cache_keys, prepare_request, merge_value_to_key
from common.crypto import encryption_enabled, encrypt_parameters


router = Router()


@router.api_route("/api/v3/audit/audit/", methods=["GET", "POST"])
async def audit_audit(request: Request) -> ORJSONResponse:
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )
    packages_list = parameters.get("package")
    if packages_list and isinstance(packages_list, str):
        packages_list = [packages_list]

    cache_args = parameters.get("os"), parameters.get("version")
    cache_keys = prepare_cache_keys(packages_list, cache_args)

    cached_results = router.cache.get_many(cache_keys)
    packages_data = {
        cache_keys[key]: value
        for key, value in cached_results.items()
        if key in cache_keys
    }
    uncached_packages = list(set(packages_list).difference(packages_data.keys()))

    if uncached_packages:
        parameters["package"] = uncached_packages

        if encryption_enabled:
            encrypt_parameters(request, parameters, objects=['ip', 'fqdn'])

        request = router.session.build_request(
            method=request.method,
            url=endpoint_url,
            json=parameters,
            headers=request_headers,
        )
        vulners_response = await router.session.send(request)
        vulners_response.read()
        vulners_results = vulners_response.json()
        response_packages = {**vulners_results.get("data").get("packages", {})}
        response_packages.update(
            {key: "empty" for key in uncached_packages if key not in response_packages}
        )
        prepared_cache = {
            merge_value_to_key(package, cache_args): data
            for package, data in response_packages.items()
        }
        router.cache.set_many(prepared_cache, expire=router.settings.cache_timeout)
    else:
        router.statistics[dispatcher] += 1
        vulners_results = {
            "result": "OK",
            "data": {
                "packages": {},
                "vulnerabilities": [],
                "reasons": [],
                "cvss": {
                    "score": 0.0,
                    "vector": "NONE"
                },
                "cvelist": [],
                "cumulativeFix": ""
            },
        }

    result_data = vulners_results["data"]
    result_data.setdefault("packages", {}).update(
        {key: value for key, value in packages_data.items() if value != "empty"}
    )

    result_data["vulnerabilities"] = [
        bulletin_id
        for package in result_data["packages"].values()
        for bulletin_id in package.keys()
    ]

    result_data["reasons"] = [
        reason
        for package in result_data["packages"].values()
        for reasons in package.values()
        for reason in reasons
    ]

    cumulative_fix = []
    for reason in result_data["reasons"]:
        for word in reason["fix"].split():
            if word in cumulative_fix:
                continue
            cumulative_fix.append(word)
    result_data["cumulativeFix"] = " ".join(cumulative_fix)

    return ORJSONResponse(
        content=vulners_results,
    )
