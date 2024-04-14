import asyncio
import contextlib
import logging
from starlette.middleware import Middleware
import importlib
import json
import os
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel
from relax.injection import (
    Injected,
    injectable,
    COMPONENTS_CACHE_FILE,
    _COMPONENT_NAMES,
)
from relax.config import BaseConfig
from starlette.websockets import WebSocket, WebSocketDisconnect


import inspect
from dataclasses import Field, _MISSING_TYPE
from enum import StrEnum, auto
from functools import partial, wraps
from inspect import Parameter, signature
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    ClassVar,
    Concatenate,
    Generic,
    Literal,
    Mapping,
    Protocol,
    Self,
    Sequence,
    Type,
    TypedDict,
    TypeVar,
    get_args,
    get_origin,
)
from starlette.datastructures import URL, UploadFile

import starlette.requests
import starlette.types
from starlette.applications import Starlette
from starlette.authentication import requires
import starlette.responses
from starlette.routing import Route
from typing_extensions import ParamSpec

import relax.html

QueryStr = Annotated[str, "query_param"]
QueryInt = Annotated[int, "query_param"]
PathInt = Annotated[int, "path_param"]
PathStr = Annotated[str, "path_param"]

P = ParamSpec("P")
T = TypeVar("T")

CLIENTS: set[WebSocket] = set()
IMPORTS: dict[str, ModuleType] = {}


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


DataclassT = TypeVar("DataclassT", bound=DataclassInstance)

Method = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]

logger = logging.getLogger(__name__)


class HTMLResponse(starlette.responses.HTMLResponse):
    def __init__(
        self,
        content: relax.html.Element,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(content.render(), status_code, headers)


class AuthScope(StrEnum):
    Authenticated = auto()


class Scope(TypedDict):
    from_htmx: bool


class Request(starlette.requests.Request, Generic[T]):
    user: T  # type: ignore
    scope: Scope  # type: ignore

    def __init__(self, base_request: starlette.requests.Request) -> None:
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

    @contextlib.asynccontextmanager
    async def parse_form(
        self,
        data_shape: Type[DataclassT],
    ) -> AsyncGenerator[DataclassT, None]:
        fields: dict[str, Any] = {}
        async with self.form() as form:
            for name, field in data_shape.__dataclass_fields__.items():
                try:
                    if field.type is UploadFile:
                        fields[name] = form[name]
                    else:
                        fields[name] = field.type(form[name])
                except KeyError:
                    if isinstance(field.default, _MISSING_TYPE):
                        raise
                    fields[name] = field.default
            yield data_shape(**fields)


class UserType(Protocol):
    username: str
    display_name: str
    is_authenticated: bool


def get_annotated(param: Parameter) -> Any:
    annotation = param.annotation
    if get_origin(annotation) is Annotated:
        return get_args(annotation)

    if get_origin(getattr(get_origin(annotation), "__value__", None)) is Annotated:
        return (
            get_args(annotation)[0],
            get_args(getattr(get_origin(annotation), "__value__", None))[1],
        )

    try:
        if get_origin(get_args(annotation)[0]) is Annotated:
            return get_args(get_args(annotation)[0])
    except IndexError:
        return None

    return None


def load_views() -> dict | None:
    with COMPONENTS_CACHE_FILE.open("r") as f:
        try:
            raw_data = json.load(f)
        except TypeError:
            logger.exception("failed parsing JSON data")
            raise

    updated_views = {}

    logger.warning("loaded data")
    try:
        for id, element in raw_data.items():
            fn_path = element["path"]
            fn_values = element["data"]
            fn_module, fn_name = fn_path.rsplit(".", 1)
            if fn_module not in IMPORTS:
                IMPORTS[fn_module] = importlib.import_module(fn_module)
            fn = getattr(IMPORTS[fn_module], fn_name)

            # TODO: if we can't find the function referenced in the data, drop it
            for name, param in signature(fn).parameters.items():
                try:
                    if (
                        param.default is not Injected
                        and isinstance(fn_values.get(name), dict)
                        and issubclass(param.annotation, BaseModel)
                    ):
                        model_obj = fn_values[name]
                        fn_values[name] = param.annotation(**(model_obj))
                except TypeError:
                    pass

            updated_views[id] = fn(**fn_values).render()
    except Exception as e:  # noqa: BLE001
        logger.warning("failed loading views: %s", repr(e))
        return None
    return updated_views


async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.warning("got new websocket connection")
    CLIENTS.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.warning("got new data: %s", data)
    except WebSocketDisconnect:
        CLIENTS.remove(websocket)


class ViewContext:
    def __init__(self) -> None:
        self._app: Starlette | None = None
        self.endpoints: dict[Callable, Any] = {}
        self.path_functions: dict[Callable, Callable] = {}

    def attach_to_app(self, app: Starlette) -> Self:
        self._app = app
        return self

    def add_endpoint(self, sig: Any, endpoint: Callable) -> None:
        self.endpoints[sig] = endpoint

    def endpoint(self, sig: Type[T]) -> T:
        return self.endpoints[sig]

    def add_path_function(self, func: Callable) -> None:
        if self._app is None:
            msg = "App instance not set on ViewContext"
            raise ValueError(msg)
        self.path_functions[func] = partial(self._app.url_path_for, func.__name__)

    def url_of(
        self,
        func: Callable[Concatenate["Request", P], Awaitable[Any]],
    ) -> Callable[P, URL]:
        return self.path_functions[func]  # type: ignore


class App(Starlette):
    def __init__(
        self,
        view_context: ViewContext,
        config: BaseConfig,
        debug: bool = False,
        middleware: Sequence[Middleware] | None = None,
        lifespan: starlette.types.Lifespan["App"] | None = None,
    ) -> None:
        super().__init__(debug=debug, middleware=middleware, lifespan=lifespan)
        self.view_context = view_context.attach_to_app(self)
        self.config = config

    def add_router(self, router: "Router") -> None:
        for route in router.routes:
            self.routes.append(route)
            self.view_context.add_path_function(route.endpoint)

    def listen_to_template_changes(self) -> None:
        print("Listening to template changes for hot-module replacement")
        self.listen_task = asyncio.create_task(self._listen_to_template_changes())

    async def _listen_to_template_changes(self) -> None:
        with contextlib.suppress(FileNotFoundError):
            self.config.RELOAD_SOCKET_PATH.unlink()
        print("gonna listen on socket")
        self.reload_server = await asyncio.start_unix_server(
            intermediary_hot_replace_templates,
            self.config.RELOAD_SOCKET_PATH,
        )
        print("started listening on socket: ", self.reload_server.is_serving())


class BaseRouter(Protocol):
    ...


class Router(BaseRouter):
    def __init__(self) -> None:
        self.routes: list[Route] = []

    def path_function(  # noqa: ANN201
        self,
        method: Method,
        endpoint: str,
        auth_scopes: list[AuthScope] | None = None,
    ):
        if auth_scopes is None:
            auth_scopes = []

        def decorator(func):  # noqa: ANN001, ANN202
            @wraps(func)
            @requires(auth_scopes)
            async def inner(request: starlette.requests.Request):  # noqa: ANN202
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
                return await injectable(func)(request, **params)

            # TODO: maybe make the name file + fn_name?
            # TODO: also, error out when finding a duplicate name
            self.routes.append(
                Route(endpoint, inner, methods=[method], name=func.__name__),
            )

            return inner

        return decorator


def update_js_constants(config: BaseConfig) -> None:
    with config.JS_CONSTANTS_PATH.open("w") as f:
        f.write("export const CONSTANTS = {\n")
        for name in _COMPONENT_NAMES:
            f.write(f'   {name.upper().replace("-", "_")}_CLASS: "{name}",\n')
        f.write("}")


async def intermediary_hot_replace_templates(
    sr: asyncio.StreamReader,
    _: asyncio.StreamWriter,
) -> None:
    try:
        data = await sr.read(1024)
        result = json.loads(data)
        if result["event_type"] == "update_views":
            await hot_replace_templates(result["data"])
    except Exception as e:  # noqa: BLE001
        print(e)  # noqa: T201


async def hot_replace_templates(changed_paths: list[str]) -> None:
    try:
        for str_path in changed_paths:
            file_path = Path(str_path)
            str_path = str_path.removesuffix(file_path.suffix)
            str_path = str_path.replace(os.sep, ".")
            if str_path in IMPORTS:
                IMPORTS[str_path] = importlib.reload(IMPORTS[str_path])
            else:
                IMPORTS[str_path] = importlib.import_module(str_path)
                IMPORTS[str_path] = importlib.reload(IMPORTS[str_path])

        logger.warning("reloaded changes")
        new_views = load_views()
        logger.warning("loaded views")
        if new_views is not None:
            for client in CLIENTS:
                await client.send_text(
                    json.dumps({"event_type": "update_views", "data": new_views}),
                )
            logger.warning("updated browser")
        else:
            logger.warning("no data to update server with")
    except Exception as e:  # noqa: BLE001
        print(e)  # noqa: T201
