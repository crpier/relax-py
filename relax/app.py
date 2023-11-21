import inspect
from enum import StrEnum, auto
from functools import wraps
from inspect import _ParameterKind, signature
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    Concatenate,
    Generic,
    Protocol,
    TypedDict,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

import starlette.requests
import starlette.types
from starlette.applications import Starlette
from starlette.authentication import requires
from starlette.routing import Route
from typing_extensions import ParamSpec

QueryStr = Annotated[str, "query_param"]
QueryInt = Annotated[int, "query_param"]
PathInt = Annotated[int, "path_param"]
PathStr = Annotated[str, "path_param"]

PathPart = Union[QueryStr, QueryInt, PathInt, PathStr]

P = ParamSpec("P")
T = TypeVar("T")


class AuthScope(StrEnum):
    Authenticated = auto()


class Scope(TypedDict):
    from_htmx: bool


class Request(starlette.requests.Request, Generic[T]):
    scope: Scope  # type: ignore[assignment]
    user: T


class UserType(Protocol):
    username: str
    display_name: str
    is_authenticated: bool


class App(Starlette):
    def url_wrapper(
        self,
        func: Callable[Concatenate[Request, P], Any],
    ) -> Callable[P, str]:
        def inner(*_: P.args, **kwargs: P.kwargs) -> str:
            return self.url_path_for(func.__name__, **kwargs)

        return inner

    # TODO: method should be enum maybe?
    def path_function(
        self,
        method: str,
        endpoint: str,
        auth_scopes: list[AuthScope] | None = None,
    ):
        if auth_scopes is None:
            auth_scopes = []

        def decorator(
            func: Callable[Concatenate[Request, ...], Any],
        ):
            @wraps(func)
            @requires(auth_scopes)
            async def inner(request: Request):
                params = {}
                request.scope["from_htmx"] = (
                    request.headers.get("HX-Request", False) == "true"
                )
                for param_name, param in signature(func).parameters.items():
                    # TODO: param validation
                    if (
                        get_origin(param.annotation) is Annotated
                        or get_origin(get_args(param.annotation)[0]) is Annotated
                    ):
                        try:
                            if (
                                get_args(param.annotation)[1] == "query_param"
                                or get_args(get_args(param.annotation)[0])[1]
                                == "query_param"
                            ):
                                params[param_name] = request.query_params.get(
                                    param_name,
                                    param.default,
                                )
                                if params[param_name] is inspect._empty:
                                    msg = (
                                        f"function {func.__name__} is missing "
                                        f"required parameter {param_name}"
                                    )
                                    raise TypeError(msg)
                        except IndexError:
                            pass
                        if get_args(param.annotation)[1] == "path_param" or (
                            len(get_args(get_args(param.annotation)[0])) > 1
                            and get_args(get_args(param.annotation)[0])[1]
                            == "path_param"
                        ):

                            params[param_name] = request.path_params.get(
                                param_name,
                                param.default,
                            )
                            if params[param_name] is inspect._empty:
                                msg = (
                                    f"function {func.__name__} is missing "
                                    f"required parameter {param_name}"
                                )
                                raise TypeError(msg)
                return await func(request, **params)

            # TODO: maybe make the name file + fn_name?
            # TODO: also, error out when finding a duplicate name
            self.routes.append(
                Route(endpoint, inner, methods=[method], name=func.__name__),
            )

            return inner

        return decorator
