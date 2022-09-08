from fastapi import Request
from fastapi.responses import ORJSONResponse
from routers import Router
from common.prepare import prepare_cache_keys, prepare_request, merge_value_to_key

# search/id call local cache optimization

router = Router()


@router.api_route("/api/v3/search/id/", methods=["GET", "POST"])
async def search_id(request: Request) -> ORJSONResponse:
    parameters, request_headers, endpoint_url, dispatcher = await prepare_request(
        router.settings, request
    )
    id_list = parameters.get("id")
    if id_list and isinstance(id_list, str):
        id_list = [id_list]
    doc_cache_keys = prepare_cache_keys(id_list, fields := parameters.get("fields"))
    ref_cache_keys = prepare_cache_keys(id_list, "references")
    cached_documents = router.cache.get_many(
        list(doc_cache_keys.keys()) + list(ref_cache_keys.keys())
    )
    documents_data = {
        doc_cache_keys[key]: value
        for key, value in cached_documents.items()
        if key in doc_cache_keys
    }
    references_data = {
        ref_cache_keys[key]: value
        for key, value in cached_documents.items()
        if key in ref_cache_keys
    }
    uncached_id_set = list(set(id_list).difference(documents_data.keys()))
    if uncached_id_set:
        parameters["id"] = uncached_id_set
        # Perform minimized vulners request
        request = router.session.build_request(
            method=request.method,
            url=endpoint_url,
            json=parameters,
            headers=request_headers,
        )
        vulners_response = await router.session.send(request)
        vulners_response.read()
        vulners_results = vulners_response.json()
        # Cache the data
        documents_cache_prepared = {
            merge_value_to_key(document_id, fields): data
            for document_id, data in vulners_results.get("data").get("documents", {}).items()
        }
        documents_cache_prepared.update({
            merge_value_to_key(document_id, "references"): data
            for document_id, data in vulners_results.get("data").get("references", {}).items()
        })
        # Combine to the one document
        router.cache.set_many(
            documents_cache_prepared, expire=router.settings.cache_timeout
        )
    else:
        router.statistics[dispatcher] += 1
        vulners_results = {
            "result": "OK",
            "data": {
                "documents": {},
                "references": {},
            },
        }
    #
    # Inject cached data to Vulners response
    vulners_results["data"]["documents"].update(documents_data)
    if not vulners_results["data"].get("references"):
        vulners_results["data"]["references"] = {}
    vulners_results["data"]["references"].update(references_data)

    return ORJSONResponse(
        content=vulners_results,
    )
