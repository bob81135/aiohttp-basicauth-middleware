import inspect
import logging
import os
from typing import (
    Callable,
    Iterable,
    Any,
    TYPE_CHECKING,
)

try:
    from typing import Type, Coroutine
except ImportError:
    class _Coroutine:
        # Fake, so you can do Coroutine[foo, bar, baz]
        # You could assert the proper number of items are in the slice,
        # but that seems like overkill, given that mypy will check this
        # and at runtime you probably no longer care
        #
        # See: https://stackoverflow.com/q/44651115/2122401
        # TODO: remove on drop py35
        def __getitem__(self, index: Any) -> None:
            pass
    if not TYPE_CHECKING:
        Coroutine = _Coroutine()

from aiohttp import web
from http_basic_auth import parse_header, BasicAuthException
from aiohttp_basicauth_middleware.strategy import BaseStrategy


log = logging.getLogger(__name__)

def check_list(url, path):
    filename, file_extension = os.path.splitext(url)
    pathname, path_extension = os.path.splitext(path)
    if(file_extension==""):
        filename+="/"
    if(path_extension==""):
        pathname+="/"
        if(filename.startswith(pathname)):
            return True
    else:
        if(url == path):
            return True
    return False

def check_access(
    auth_dict: dict,
    header_value: str,
    strategy: Callable = lambda x: x
) -> bool:
    log.debug('Check access: %r', header_value)

    try:
        login, password = parse_header(header_value)
    except BasicAuthException:
        return False

    hashed_password = auth_dict.get(login)
    hashed_request_password = strategy(password)

    if hashed_password != hashed_request_password:
        return False

    return True


def basic_auth_middleware(
    urls: Iterable,
    auth_dict: dict,
    strategy: Type[BaseStrategy] = lambda x: x
) -> Coroutine:
    async def factory(app, handler) -> Coroutine:
        async def middleware(request) -> web.Response:
            for url in urls:
                if not check_list(request.path,url):
                    continue
                # if not request.path.startswith(url):
                #     continue

                if inspect.isclass(strategy) and issubclass(strategy, BaseStrategy):
                    log.debug("Use Strategy: %r", strategy.__name__)
                    strategy_obj = strategy(
                        request,
                        auth_dict,
                        handler,
                        request.headers.get('Authorization', '')
                    )
                    return await strategy_obj.check()

                if not check_access(auth_dict, request.headers.get('Authorization', ''), strategy):
                    raise web.HTTPUnauthorized(headers={'WWW-Authenticate': 'Basic'})

                return await handler(request)
            return await handler(request)
        return middleware
    return factory
