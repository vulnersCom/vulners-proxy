import json, hashlib
from typing import Any

from common.crypto import encrypt_parameters, encryption_enabled
from common.prepare import merge_value_to_key, prepare_cache_keys, prepare_request
from fastapi import Request
from fastapi.responses import ORJSONResponse
from routers import Router

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
        cache_keys[key]: value for key, value in cached_results.items() if key in cache_keys
    }
    uncached_packages = list(set(packages_list).difference(packages_data.keys()))

    if uncached_packages:
        parameters["package"] = uncached_packages

        if encryption_enabled:
            encrypt_parameters(request, parameters, objects=["ip", "fqdn"])

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
                "cvss": {"score": 0.0, "vector": "NONE"},
                "cvelist": [],
                "cumulativeFix": "",
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


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _normalize_fields(fields) -> list[str]:
    if not fields:
        return []
    return sorted(set(fields))


def _software_list(params: dict[str, Any]) -> list[Any]:
    software = params.get("software", [])
    if isinstance(software, (str, dict)):
        return [software]
    return list(software or [])


def _ctx_software(params: dict[str, Any]) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    if "match" in params:
        ctx["match"] = params["match"]
    fields = _normalize_fields(params.get("fields"))
    if fields:
        ctx["fields"] = fields
    return ctx


def _ctx_host(params: dict[str, Any]) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for k in ("operating_system", "application", "hardware", "platform", "match"):
        if k in params:
            ctx[k] = params[k]
    fields = _normalize_fields(params.get("fields"))
    if fields:
        ctx["fields"] = fields
    return ctx


def _v4_key(prefix: str, software_item: Any, ctx: dict[str, Any]) -> str:
    payload = {"input": software_item}
    if ctx:
        payload["ctx"] = ctx
    digest = hashlib.sha256(_canon(payload).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


async def _audit_v4_cached(
    request: Request,
    endpoint_url: str,
    request_headers: dict[str, str],
    dispatcher: str,
    parameters: dict[str, object],
    prefix: str,
    ctx: dict[str, object],
) -> ORJSONResponse:
    software: list[object] = _software_list(parameters)
    keys: list[str] = [_v4_key(prefix, item, ctx) for item in software]

    cached_map: dict[str, object] = router.cache.get_many(keys)
    result_items: list[object | None] = [None] * len(software)
    miss_idx: list[int] = []

    for i, k in enumerate(keys):
        cached = cached_map.get(k)
        if cached is not None:
            result_items[i] = cached
        else:
            miss_idx.append(i)

    if miss_idx:
        subset: list[object] = [software[i] for i in miss_idx]
        req_params: dict[str, object] = dict(parameters)
        req_params["software"] = subset

        if encryption_enabled:
            encrypt_parameters(request, req_params, objects=["ip", "fqdn"])

        upstream_req = router.session.build_request(
            method=request.method, url=endpoint_url, json=req_params, headers=request_headers
        )
        upstream_resp = await router.session.send(upstream_req)
        upstream_resp.read()
        upstream_json: object = upstream_resp.json()

        if isinstance(upstream_json, dict) and isinstance(upstream_json.get("result"), list):
            subset_result: list[object] = upstream_json["result"]
        elif isinstance(upstream_json, list):
            subset_result = upstream_json
        else:
            subset_result = []

        if len(subset_result) < len(subset):
            return ORJSONResponse(content={"result": subset_result})

        for off, idx in enumerate(miss_idx):
            item = subset_result[off]
            result_items[idx] = item
            router.cache.set(keys[idx], item, expire=router.settings.cache_timeout)
    else:
        router.statistics[dispatcher] += 1

    return ORJSONResponse(content={"result": result_items})


@router.api_route("/api/v4/audit/software", methods=["POST"])
async def audit_v4_software(request: Request) -> ORJSONResponse:
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )
    ctx = _ctx_software(parameters)
    return await _audit_v4_cached(
        request, endpoint_url, request_headers, dispatcher, parameters, "v4:software", ctx
    )


@router.api_route("/api/v4/audit/host", methods=["POST"])
async def audit_v4_host(request: Request) -> ORJSONResponse:
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )
    ctx = _ctx_host(parameters)
    return await _audit_v4_cached(
        request, endpoint_url, request_headers, dispatcher, parameters, "v4:host", ctx
    )
