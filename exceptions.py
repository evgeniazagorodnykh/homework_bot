class HTTPStatusError(Exception):
    def __init__(self, response):
        message = (
            f'Неверный код ответа API: {response.status_code}'
        )
        super().__init__(message)

class RequestError(Exception):
    pass
