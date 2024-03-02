import threading
import asyncio
import importlib
import json
import os
from inspect import signature
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel
from relax.injection import Injected
from starlette.websockets import WebSocket, WebSocketDisconnect
from watchfiles import awatch


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
from starlette.datastructures import URL, FormData as BaseFormData

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

type FormData[T] = Annotated[T, "form_data"]

def run_async(coro):  # coro is a couroutine, see example
    _loop = asyncio.new_event_loop()

    _thr = threading.Thread(target=_loop.run_forever, name="Async Runner", daemon=True)

    if not _thr.is_alive():
        _thr.start()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result()


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


def extract_from_form(form: BaseFormData, data_shape: Type[DataclassT]) -> DataclassT:
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
    annotation = param.annotation
    if get_origin(annotation) is Annotated:
        return get_args(annotation)

    if get_origin(getattr(get_origin(annotation), "__value__", None)) is Annotated:
        return (get_args(annotation)[0], get_args(getattr(get_origin(annotation), "__value__", None))[1])

    try:
        if get_origin(get_args(annotation)[0]) is Annotated:
            return get_args(get_args(annotation)[0])
    except IndexError:
        return None

    return None


CLIENTS = set()
VIEWS_DATA = ""
IMPORTS: dict[str, ModuleType] = {}


async def hot_replace_templates(templates_dir):
    async for changes in awatch(templates_dir):
        real_changes = {
            change[1]
            for change in changes
            if os.path.exists(change[1]) and not Path(change[1]).match(".*")
        }
        if len(real_changes) == 0:
            continue
        changed_paths = [
            Path(change).relative_to(Path.cwd()) for change in real_changes
        ]
        print("new changes: ", changed_paths)
        for file_path in changed_paths:
            str_path = str(file_path)
            str_path = str_path.removesuffix(file_path.suffix)
            str_path = str_path.replace(os.sep, ".")
            if str_path in IMPORTS:
                IMPORTS[str_path] = importlib.reload(IMPORTS[str_path])
            else:
                IMPORTS[str_path] = importlib.import_module(str_path)
                IMPORTS[str_path] = importlib.reload(IMPORTS[str_path])

        print("reloaded changes")
        new_views = load_views()
        print("loaded views")
        if new_views is not None:
            for client in CLIENTS:
                await client.send_text(
                    json.dumps({"event_type": "update_views", "data": new_views}),
                )
            print("updated browser")
        else:
            print("no data to update server with")


def load_views() -> dict | None:
    updated_views = {}
    try:
        raw_data = json.loads(VIEWS_DATA)
    except TypeError as e:
        print("failed parsing JSON data: ", e)
        return None

    print("loaded data")
    try:
        for element in raw_data:
            for fn_path, fn_data in raw_data[element].items():
                fn_values = json.loads(fn_data)
                fn_module, fn_name = fn_path.rsplit(".", 1)
                if fn_module not in IMPORTS:
                    IMPORTS[fn_module] = importlib.import_module(fn_module)
                fn = getattr(IMPORTS[fn_module], fn_name)

                for name, param in signature(fn).parameters.items():
                    try:
                        if (
                            param.default is not Injected
                            and isinstance(fn_values[name], dict)
                            and issubclass(param.annotation, BaseModel)
                        ):
                            model_obj = fn_values[name]
                            fn_values[name] = param.annotation(**(model_obj))
                    except TypeError:
                        pass

                updated_views[element] = fn(**fn_values).render()
    except Exception as e:
        print("failed loading views: ", e)
        return None
    return updated_views


async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("got new websocket connection")
    CLIENTS.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print("got new data")
            global VIEWS_DATA  # noqa: PLW0603
            VIEWS_DATA = data
            # Echo received message to all connected CLIENTS
    except WebSocketDisconnect:
        CLIENTS.remove(websocket)


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


class App(Starlette, Generic[T]):
    config: T

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
