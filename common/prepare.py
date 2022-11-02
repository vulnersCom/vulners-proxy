import ast
import hashlib
from fastapi import Request
from common import __version__
from common.config import logger
from json.decoder import JSONDecodeError
from urllib.parse import urlparse


async def prepare_request(settings, request: Request) -> tuple:
    get_parameters = {
        param_name: estimate_typed_value(request.query_params.get(param_name).strip())
        for param_name in request.query_params
    }
    if not get_parameters:
        try:
            parameters = await request.json()
        except JSONDecodeError as err:
            logger.warn(err)
            parameters = {}
    else:
        parameters = get_parameters

    merged_parameters = {}
    if not any([key in request.query_params for key in ("api_key", "apiKey")]) and settings.vulners_api_key:
        merged_parameters["apiKey"] = settings.vulners_api_key
    merged_parameters.update(parameters)
    split_url = str(request.url).split(str(request.base_url))
    split_url[0] = f'https://{settings.vulners_host}'
    endpoint_url = "/".join(split_url)
    dispatcher = ".".join(urlparse(str(request.url)).path.split("/")[-3:-1])
    headers = {
        "User-Agent": "Vulners Proxy Version %s" % __version__,
        **{
            key: request.headers[key]
            for key in request.headers
            if key.lower().startswith(("accept", "x-vulners"))
        }
    }
    return merged_parameters, headers, endpoint_url, dispatcher


def estimate_typed_value(value):
    """
    Safely evaluate an expression node or a string containing a Python
    expression.  The string or node provided may only consist of the following
    Python literal structures: strings, bytes, numbers, tuples, lists, booleans, and None.
    """
    initial_string = value
    if isinstance(value, str):
        try:
            value = ast.parse(value, mode="eval")
        except Exception as err:
            logger.warn(err)
            return initial_string
    if isinstance(value, ast.Expression):
        value = value.body

    def is_hex_or_oct(value):
        try:
            int(value, 16)
            return True and ("x" in value.lower())
        except Exception as err:
            logger.warn(err)
            try:
                int(value, 8)
                return True and ("o" in value.lower())
            except Exception as err:
                logger.warn(err)
                pass
            return False

    def _convert(node, i_string=None):
        if isinstance(node, ast.Constant) and not is_hex_or_oct(i_string):
            return node.value
        elif isinstance(node, (ast.Str, ast.Bytes)):
            return node.s
        elif isinstance(node, ast.Num) and not is_hex_or_oct(i_string):
            return node.n
        # elif isinstance(node, ast.Tuple):
        #     return tuple(map(_convert, node.elts))
        elif isinstance(node, ast.List):
            return list(map(_convert, node.elts))
        raise ValueError("malformed node or string: " + repr(node))
    try:
        return _convert(value, initial_string)
    except Exception as err:
        logger.warn(err)
        return initial_string


def prepare_cache_keys(keys: list, *args) -> dict:
    return {
        merge_value_to_key(key, *args): key
        for key in keys
    }


def merge_value_to_key(*args) -> str:
    hash_data = hashlib.md5()
    for arg in args:
        hash_data.update(str(arg).encode("utf-8"))
    return hash_data.hexdigest()
