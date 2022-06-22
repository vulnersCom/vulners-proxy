from diskcache import Cache as _Cache
import concurrent.futures

class Cache(_Cache):

    def get_key(self, key, *args, **kwargs):
        return key, super().get(key, *args, **kwargs)

    def get_many(self, keys, default=None, read=False, expire_time=False, tag=False, retry=False):
        results = dict()
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            lookup_calls = [executor.submit(self.get_key, key, default, read, expire_time, tag, retry) for key in keys]
            for future in concurrent.futures.as_completed(lookup_calls):
                key, value = future.result()
                if value:
                    results[key] = value
        return results

    def set_many(self, key_values, expire=None, read=False, tag=None, retry=False):
        operation_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            lookup_calls = [executor.submit(self.set, key, key_values[key], expire, read, tag, retry) for key in key_values]
            for future in concurrent.futures.as_completed(lookup_calls):
                operation_results.append(future.result())
        return all(operation_results)