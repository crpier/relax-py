import asyncio
import contextlib
import importlib
import inspect
import json
import logging
import os
from dataclasses import _MISSING_TYPE, Field, is_dataclass
from enum import StrEnum, auto
from functools import wraps
from html import escape
from inspect import Parameter, signature
from pathlib import Path
from types import ModuleType
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
    Sequence,
    TypedDict,
    TypeVar,
    get_args,
    get_origin,
)

import starlette.requests
import starlette.responses
import starlette.types
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.authentication import requires
from starlette.datastructures import URL, UploadFile, URLPath
from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing_extensions import ParamSpec

import relax.html
from relax.config import BaseConfig
from relax.injection import (
    _COMPONENT_NAMES,
    COMPONENTS_CACHE_FILE,
    Injected,
    injectable,
)

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


DataclassT = TypeVar("DataclassT", bound=[DataclassInstance, BaseModel])

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
        data_shape: type[DataclassT],
    ) -> AsyncGenerator[DataclassT, None]:
        fields: dict[str, Any] = {}
        async with self.form() as form:
            if issubclass(data_shape, BaseModel):
                yield data_shape.model_validate(form)
            elif is_dataclass(data_shape):
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
            else:
                raise TypeError(
                    "data_shape for form must be a pydantic model or a dataclass",
                )


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
    try:
        raw_data = json.load(COMPONENTS_CACHE_FILE)
        COMPONENTS_CACHE_FILE.seek(0)
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


class App(Starlette):
    def __init__(
        self,
        config: BaseConfig,
        debug: bool = False,
        middleware: Sequence[Middleware] | None = None,
        lifespan: starlette.types.Lifespan["App"] | None = None,
    ) -> None:
        super().__init__(debug=debug, middleware=middleware, lifespan=lifespan)
        self.config = config

    def add_router(self, router: "Router") -> None:
        router.app = self
        for route in router.routes:
            self.routes.append(route)

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
        self.app: App | None = None

    def path_function(  # noqa: ANN201
        self,
        method: Method,
        endpoint: str,
        auth_scopes: list[AuthScope] | None = None,
    ):
        if auth_scopes is None:
            auth_scopes = []

        def decorator(
            func: Callable[Concatenate["Request", P], Awaitable[Any]],
        ) -> Callable[P, URLPath]:
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

            def get_url(
                **kwargs: Any,
            ) -> URLPath:
                if self.app is None:
                    msg = "App instance not set on ViewContext"
                    raise ValueError(msg)
                query_params: dict[str, Any] = {}
                for name, param in signature(func).parameters.items():
                    if name == "request":
                        continue
                    args = get_annotated(param)
                    if args and args[1] == "query_param":
                        try:
                            query_params[name] = kwargs.pop(name)
                        except KeyError as e:
                            msg = f"missing query parameter {name} for {func.__name__}"
                            raise ValueError(msg) from e
                base_url = self.app.url_path_for(func.__name__, **kwargs)
                if query_params != {}:
                    for idx, (name, param) in enumerate(query_params.items()):
                        if idx == 0:
                            base_url = URLPath(
                                f"{base_url}?{name}={escape(str(param), quote=True)}",
                            )
                        else:
                            base_url = URLPath(
                                f"{base_url}&{name}={escape(str(param), quote=True)}",
                            )
                return base_url

            return get_url

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
            str_path = str_path.removesuffix(".__init__")
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
