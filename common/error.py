
class VulnersProxyException(BaseException):
    def __init__(self, title, message):
        self.error_title = title
        self.error_msg = message

    def __str__(self):
        return f'{self.error_title} | {self.error_msg}'
