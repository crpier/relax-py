import contextlib
from socket import AF_UNIX, SOCK_STREAM, socket
import logging
import uvicorn.config
from uvicorn.supervisors.watchfilesreload import WatchFilesReload
import importlib
import uvicorn
import json
import os
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel
from relax.injection import Injected, injectable, COMPONENTS_CACHE_FILE
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

QueryStr = Annotated[str, "query_param"]
QueryInt = Annotated[int, "query_param"]
PathInt = Annotated[int, "path_param"]
PathStr = Annotated[str, "path_param"]

P = ParamSpec("P")
T = TypeVar("T")

CLIENTS: set[WebSocket] = set()
IMPORTS: dict[str, ModuleType] = {}


type FormData[T] = Annotated[T, "form_data"]


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


def new_decorator(func, auth_scopes: list | None):  # noqa: ANN201, ANN001
    @wraps(func)
    @requires(auth_scopes or [])
    async def inner(request: starlette.requests.Request):  # noqa: ANN202
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
                        and isinstance(fn_values[name], dict)
                        and issubclass(param.annotation, BaseModel)
                    ):
                        model_obj = fn_values[name]
                        fn_values[name] = param.annotation(**(model_obj))
                except TypeError:
                    pass

            updated_views[id] = fn(**fn_values).render()
    except Exception as e:  # noqa: BLE001
        logger.warning("failed loading views: %s", e)
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
        return self.path_functions[func]  # type: ignore


class App(Starlette):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.view_context = ViewContext(self)

    def add_router(self, router: "Router") -> None:
        for route in router.routes:
            self.routes.append(route)
            self.view_context.add_path_function(route.endpoint)


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
                    elif args and args[1] == "form_data":
                        form = await request.form()
                        try:
                            params[param_name] = extract_from_form(form, args[0])
                        except KeyError as e:
                            msg = (
                                "Field missing from form data for " f"{param_name}: {e}"
                            )
                            raise TypeError(msg) from e
                return await injectable(func)(request, **params)

            # TODO: maybe make the name file + fn_name?
            # TODO: also, error out when finding a duplicate name
            self.routes.append(
                Route(endpoint, inner, methods=[method], name=func.__name__),
            )

            return inner

        return decorator


async def listen_to_changes() -> None:
    base_config = BaseConfig()
    with contextlib.suppress(FileNotFoundError):
        base_config.RELOAD_SOCKET_PATH.unlink()
    reload_socket = socket(AF_UNIX, SOCK_STREAM)
    reload_socket.bind(str(base_config.RELOAD_SOCKET_PATH))
    reload_socket.listen(1)

    connection, client_addr = reload_socket.accept()
    try:
        print("connection from ", client_addr)
        while True:
            data = connection.recv(1024)
            if not data:
                break
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


class RelaxReload(WatchFilesReload):
    base_config: BaseConfig

    def __init__(
        self,
        config: uvicorn.config.Config,
        target: Callable[[list[socket] | None], None],
        sockets: list[socket],
        base_config: BaseConfig,
    ) -> None:
        super().__init__(config, target, sockets)
        self.base_config = base_config

    def should_restart(self) -> list[Path] | None:
        changed_paths = super().should_restart()
        if changed_paths is None:
            return None
        changed_templates: list[Path] = []
        changed_app_files: list[Path] = []
        for change in changed_paths:
            try:
                Path(change).relative_to(self.base_config.TEMPLATES_DIR)
                changed_templates.append(Path(change).relative_to(Path.cwd()))
            # we raise ValueError if the path is not in the templates dir
            except ValueError:
                changed_app_files.append(change)
        if len(changed_app_files) > 0:
            print("changed app files: ", changed_app_files)
            return changed_app_files
        if len(changed_templates) > 0:
            print("changed templates: ", changed_templates)
            self._update_templates(changed_templates)
        return None

    def _update_templates(self, changed_templates: list[Path]) -> None:
        reload_socket = socket(AF_UNIX, SOCK_STREAM)
        reload_socket.connect(str(self.base_config.RELOAD_SOCKET_PATH))
        changes = json.dumps(
            {
                "event_type": "update_views",
                "data": [str(change) for change in changed_templates],
            },
        ).encode()
        reload_socket.send(changes)


def start_app(app_path: str, port: int | None = None, log_level: str = "info") -> None:
    config = BaseConfig()

    if port is None:
        port = config.PORT

    server_config = uvicorn.Config(
        app=app_path,
        port=port,
        log_level=log_level,
        factory=True,
    )

    server = uvicorn.Server(server_config)

    reload_config = uvicorn.Config(
        app=app_path,
        port=port,
        factory=True,
        reload=True,
        log_level=log_level,
    )
    sock = reload_config.bind_socket()
    reloader = RelaxReload(
        reload_config,
        target=server.run,
        sockets=[sock],
        base_config=config,
    )
    reloader.run()
