import inspect
from enum import StrEnum, auto
from functools import wraps
from inspect import Parameter, signature
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


def get_annotated(param: Parameter) -> Any:
    if get_origin(param.annotation) is Annotated:
        return get_args(param.annotation)

    if get_origin(get_args(param.annotation)[0]) is Annotated:
        return get_args(get_args(param.annotation)[0])

    return None


class App(Starlette):
    def url_wrapper(
        self,
        func: Callable[Concatenate[Request, P], Awaitable[Any]],
        # TODO: str should be a urlpath instead
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

        def decorator(func):
            @wraps(func)
            @requires(auth_scopes)
            async def inner(request: Request):
                params: dict[str, Any] = {}
                request.scope["from_htmx"] = (
                    request.headers.get("HX-Request", False) == "true"
                )
                for param_name, param in signature(func).parameters.items():
                    if (args := get_annotated(param)) and args[1] == "query_param":
                        if (
                            param_value := request.query_params.get(param_name)
                        ) is None:
                            if param.default is inspect._empty:
                                msg = (
                                    f"parameter {param_name} from function "
                                    f"{func.__name__} has no default value "
                                    "and was not provided in the request"
                                )
                                raise TypeError(msg)
                            params[param_name] = param.default
                        else:
                            # TODO: also allow something like
                            # \ Annotated[Path | None, "query_param"] = Path("/")
                            params[param_name] = args[0](param_value)
                    elif (args := get_annotated(param)) and args[1] == "path_param":
                        if (param_value := request.path_params.get(param_name)) is None:
                            if param.default is inspect._empty:
                                msg = (
                                    f"parameter {param_name} from function "
                                    f"{func.__name__} has no default value "
                                    "and was not provided in the request"
                                )
                                raise TypeError(msg)
                            params[param_name] = param.default
                        else:
                            params[param_name] = args[0](param_value)
                return await func(request, **params)

            # TODO: maybe make the name file + fn_name?
            # TODO: also, error out when finding a duplicate name
            self.routes.append(
                Route(endpoint, inner, methods=[method], name=func.__name__),
            )

            return inner

        return decorator
