from common.disk_cache import Cache
from common.config import app_opts


class Statistic(dict):
    __cache = Cache(directory=app_opts['StatisticCacheDir'])

    def __init__(self):
        super().__init__()
        self.update(self.__cache.get('statistic') or {})
        print(self.get_statistic())

    def __getitem__(self, item):
        return self.setdefault(item, 0)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.__cache.set('statistic', self)

    def get_statistic(self) -> str:
        statistic = ''
        if not (keys := [len(key) for key in self]):
            return statistic
        max_len = max(keys)
        for key, value in self.items():
            statistic += f'{key.ljust(max_len, " ")}:\t{value}\n'
        return statistic


statistics = Statistic()
