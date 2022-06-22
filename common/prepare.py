from fastapi import Request
import ast
import hashlib
from json.decoder import JSONDecodeError

async def prepare_request(settings, request: Request):
    get_parameters = dict(
        (param_name, estimateTypedValue(request.query_params.get(param_name).strip())) for param_name in request.query_params)
    if not get_parameters:
        try:
            parameters = await request.json()
        except JSONDecodeError as e:
            parameters = {}
    else:
        parameters = get_parameters
    merged_parameters = dict()
    if ('api_key' not in request.query_params or 'apiKey' not in request.query_params) and settings.vulners_api_key:
        merged_parameters['apiKey'] = settings.vulners_api_key
    merged_parameters.update(parameters)
    split_url = str(request.url).split(str(request.base_url))
    split_url[0] = settings.vulners_host
    endpoint_url = "/".join(split_url)
    return merged_parameters, \
           dict((k, request.headers[k]) for k in request.headers if k.lower().startswith(('accept', 'X-Vulners'))), \
           endpoint_url

def estimateTypedValue(s):
    """
    Safely evaluate an expression node or a string containing a Python
    expression.  The string or node provided may only consist of the following
    Python literal structures: strings, bytes, numbers, tuples, lists, booleans, and None.
    """
    initial_string = s
    if isinstance(s, str):
        try:
            s = ast.parse(s, mode='eval')
        except:
            return initial_string
    if isinstance(s, ast.Expression):
        s = s.body

    def is_hex_or_oct(s):
        try:
            int(s, 16)
            return True and ("x" in s.lower())
        except Exception as e:
            try:
                int(s, 8)
                return True and ("o" in s.lower())
            except Exception as e:
                pass
            return False

    def _convert(node, i_string = None):
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
        elif isinstance(node, ast.NameConstant):
            return node.value
        raise ValueError('malformed node or string: ' + repr(node))

    try:
        value = _convert(s, initial_string)
        return value
    except:
        return initial_string

def prepare_cache_keys(keys, *args):
    return dict((merge_value_to_key(key, *args), key) for key in keys)

def merge_value_to_key(*args):
    hashData = hashlib.md5()
    for val in args:
        val = str(val)
        hashData.update(val.encode("utf-8"))
    return hashData.hexdigest()
