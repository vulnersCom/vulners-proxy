from fastapi import Request
from fastapi.responses import ORJSONResponse
from routers import Router
from common.prepare import prepare_cache_keys, prepare_request, merge_value_to_key

# search/id call local cache optimization

router = Router()


@router.api_route("/api/v3/search/id/", methods=["GET", "POST"])
async def search_id(request: Request):
    parameters, request_headers, endpoint_url = await prepare_request(
        router.settings, request
    )
    id_list = []
    if isinstance(parameters.get("id"), str) and parameters.get("id"):
        id_list = [parameters.get("id")]
    doc_cache_keys = prepare_cache_keys(id_list, parameters.get("fields"))
    ref_cache_keys = prepare_cache_keys(id_list, "references")
    get_documents_cache = router.cache.get_many(
        list(doc_cache_keys.keys()) + list(ref_cache_keys.keys())
    )
    documents_data = {
        doc_cache_keys[key]: value
        for key, value in get_documents_cache.items()
        if key in doc_cache_keys
    }
    references_data = {
        ref_cache_keys[key]: value
        for key, value in get_documents_cache.items()
        if key in ref_cache_keys
    }
    uncached_id_set = set(id_list).difference(documents_data.keys())
    parameters["id"] = list(uncached_id_set)
    if uncached_id_set:
        # Perform minimized vulners request
        request = router.session.build_request(
            method="POST", url=endpoint_url, json=parameters, headers=request_headers
        )
        vulners_response = await router.session.send(request)
        vulners_response.read()
        vulners_results = vulners_response.json()
        # Cache the data
        documents_cache_prepared = {
            merge_value_to_key(document_id, parameters.get("fields")): data
            for document_id, data in vulners_results.get("data").get("documents", {}).items()
        }
        references_cache_prepared = {
            merge_value_to_key(document_id, "references"): data
            for document_id, data in vulners_results.get("data").get("references", {}).items()
        }
        # Combine to the one document
        documents_cache_prepared.update(references_cache_prepared)
        router.cache.set_many(
            documents_cache_prepared, expire=router.settings.cache_timeout
        )
    else:
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
