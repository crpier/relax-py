import inspect
from dataclasses import Field, _MISSING_TYPE
from enum import StrEnum, auto
from functools import partial, wraps
from inspect import Parameter, signature
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Concatenate,
    Generic,
    Literal,
    Mapping,
    Protocol,
    Type,
    TypedDict,
    TypeVar,
    get_args,
    get_origin,
)
from starlette.datastructures import URL, FormData, UploadFile

import starlette.requests
import starlette.types
from starlette.applications import Starlette
from starlette.authentication import requires
import starlette.responses
from starlette.routing import Route
from typing_extensions import ParamSpec

import relax.html
import relax.injection

QueryStr = Annotated[str, "query_param"]
QueryInt = Annotated[int, "query_param"]
PathInt = Annotated[int, "path_param"]
PathStr = Annotated[str, "path_param"]

P = ParamSpec("P")
T = TypeVar("T")


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


DataclassT = TypeVar("DataclassT", bound=DataclassInstance)

Method = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]


class HTMLResponse(starlette.responses.HTMLResponse):
    def __init__(
        self,
        content: relax.html.Element,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(content.render(), status_code, headers)


def extract_from_form(form: FormData, data_shape: Type[DataclassT]) -> DataclassT:
    fields: dict[str, Any] = {}
    for name, field in data_shape.__dataclass_fields__.items():
        try:
            fields[name] = field.type(form[name])
        except KeyError:
            if isinstance(field.default, _MISSING_TYPE):
                raise
            fields[name] = field.default
    return data_shape(**fields)


def new_decorator(func, auth_scopes: list | None):
    @wraps(func)
    @requires(auth_scopes or [])
    async def inner(request: starlette.requests.Request):
        request = Request(request)
        params: dict[str, Any] = {}
        request.scope["from_htmx"] = request.headers.get("HX-Request", False) == "true"
        for param_name, param in signature(func).parameters.items():
            if (args := get_annotated(param)) and args[1] == "query_param":
                if (param_value := request.query_params.get(param_name)) is None:
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

    return inner


class AuthScope(StrEnum):
    Authenticated = auto()


class Scope(TypedDict):
    from_htmx: bool


class Request(starlette.requests.Request, Generic[T]):
    user: T
    scope: Scope  # type: ignore

    def __init__(self, base_request: starlette.requests.Request):
        super().__init__(base_request.scope, base_request._receive, base_request._send)

    def url_of(
        self,
        func: Callable[Concatenate["Request", P], Awaitable[Any]],
        *_: P.args,
        **kwargs: P.kwargs,
    ) -> URL:
        return self.url_for(func.__name__, **kwargs)

    def url_wrapper(
        self,
        func: Callable[Concatenate["Request", P], Awaitable[Any]],
    ) -> Callable[P, URL]:
        def inner(*_: P.args, **kwargs: P.kwargs) -> URL:
            return self.url_for(func.__name__, **kwargs)

        return inner


class UserType(Protocol):
    username: str
    display_name: str
    is_authenticated: bool


def get_annotated(param: Parameter) -> Any:
    if get_origin(param.annotation) is Annotated:
        return get_args(param.annotation)

    try:
        if get_origin(get_args(param.annotation)[0]) is Annotated:
            return get_args(get_args(param.annotation)[0])
    except IndexError:
        return None

    return None


class RelaxRoute:
    def __init__(
        self,
        path: str,
        method: Method,
        endpoint: Callable[Concatenate[Request, P], Awaitable[Any]],
        # TODO: runtime validation of the signature
        sig: Type[Callable[P, Any]] | None = None,
        auth_scopes: list[AuthScope] | None = None,
    ) -> None:
        self.path = path
        self.endpoint = endpoint
        self.method = method
        self.auth_scopes = auth_scopes
        self.sig = sig


class ViewContext:
    def __init__(self, app: "App") -> None:
        self._app = app
        self.endpoints: dict[Callable, Any] = {}
        self.path_functions: dict[Callable, Callable] = {}

    def add_endpoint(self, sig: Any, endpoint: Callable) -> None:
        self.endpoints[sig] = endpoint

    def endpoint(self, sig: Type[T]) -> T:
        return self.endpoints[sig]

    def add_path_function(self, func: Callable) -> None:
        self.path_functions[func] = partial(self._app.url_path_for, func.__name__)

    def url_of(
        self,
        func: Callable[Concatenate["Request", P], Awaitable[Any]],
    ) -> Callable[P, URL]:
        return self.path_functions[func]


class App(Starlette):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.view_context = ViewContext(self)

    def add_router(self, router: "Router") -> None:
        for route in router.routes:
            self.routes.append(route)
            self.view_context.add_path_function(route.endpoint)

    def add_routes(self, routes: list[RelaxRoute]) -> None:
        for route in routes:
            # TODO: maybe make the name file + fn_name?
            # TODO: also, error out when finding a duplicate name
            route_name = route.endpoint.__name__
            new_route = Route(
                path=route.path,
                endpoint=new_decorator(route.endpoint, route.auth_scopes),
                methods=[route.method],
                name=route_name,
            )
            self.routes.append(new_route)
            if route.sig:
                lol = partial(self.url_path_for, route_name)
                self.view_context.add_endpoint(sig=route.sig, endpoint=lol)

    # TODO: method should be enum maybe?
    def path_function(
        self,
        method: Method,
        endpoint: str,
        auth_scopes: list[AuthScope] | None = None,
    ):
        if auth_scopes is None:
            auth_scopes = []

        def decorator(func):
            @wraps(func)
            @requires(auth_scopes)
            async def inner(request: starlette.requests.Request):
                request = Request(request)
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


class BaseRouter(Protocol):
    ...


class Router(BaseRouter):
    def __init__(self) -> None:
        self.routes: list[Route] = []

    def path_function(
        self,
        method: Method,
        endpoint: str,
        auth_scopes: list[AuthScope] | None = None,
        sig: Any = None,
    ):
        if auth_scopes is None:
            auth_scopes = []

        def decorator(func):
            @wraps(func)
            @requires(auth_scopes)
            async def inner(request: starlette.requests.Request):
                request = Request(request)
                params: dict[str, Any] = {}
                request.scope["from_htmx"] = (
                    request.headers.get("HX-Request", False) == "true"
                )
                for param_name, param in signature(func).parameters.items():
                    args = get_annotated(param)
                    if args and args[1] == "query_param":
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
                    elif args and args[1] == "path_param":
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
                    elif args and args[1] == "form_data":
                        form = await request.form()
                        try:
                            params[param_name] = extract_from_form(form, args[0])
                        except KeyError as e:
                            msg = (
                                "Field missing from form data for " f"{param_name}: {e}"
                            )
                            raise TypeError(msg) from e
                return await relax.injection.injectable(func)(request, **params)

            # TODO: maybe make the name file + fn_name?
            # TODO: also, error out when finding a duplicate name
            self.routes.append(
                Route(endpoint, inner, methods=[method], name=func.__name__),
            )

            return inner

        return decorator
