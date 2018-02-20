import logging
from typing import Callable, Coroutine, Iterable

from aiohttp import web
from basicauth import decode, DecodeError


log = logging.getLogger(__name__)


def check_access(auth_dict: dict, header_value: str, strategy: Callable = lambda x: x) -> bool:
    try:
        login, password = decode(header_value)
    except DecodeError:
        return False

    hashed_password = auth_dict.get(login)
    hashed_request_password = strategy(password)

    if hashed_password != hashed_request_password:
        return False

    return True


def basic_auth_middleware(urls: Iterable, auth_dict: dict, strategy: Callable = lambda x: x) -> Coroutine:
    async def factory(app, handler):
        async def middleware(request):
            for url in urls:
                if not request.path.startswith(url):
                    continue

                if not check_access(auth_dict, request.headers.get('Authorization', ''), strategy):
                    raise web.HTTPUnauthorized(headers={'WWW-Authenticate': 'Basic'})

                return await handler(request)

            return await handler(request)
        return middleware
    return factory
