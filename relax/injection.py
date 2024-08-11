import json
from pathlib import Path
import warnings
from collections.abc import Callable
from functools import wraps
from inspect import _ParameterKind, signature
from typing import Any, Awaitable, ParamSpec, TypeVar, Protocol, Self

from relax.html import Component, Element

"""
A simple dependency injection helper.

Decorate functions that need to be injected with `@injectable`
set the default value of params that need to be injecte to `Injected`.

Note: Injected parameters must be keyword-only.

Example:
```python
from relax.injection import add_injectable, Injected, injectable_sync

@injectable_sync
def do_print(
    from_args: str = "string with default value",
    *,
    from_injection: str = Injected,
) -> None:
    print(from_args)
    print(from_injection)

add_injectable(str, "injected string")
do_print()
```
Running this will print:
```
string with default value
injected string
```
"""


class MissingDependencyError(Exception): ...


class IncorrectInjectableSignatureError(Exception): ...


class DoubleInjectionError(Exception): ...


_INJECTS: dict[object, object] = {}


class _Injected: ...


Injected: Any = _Injected


_P = ParamSpec("_P")
_T = TypeVar("_T")

COMPONENTS_CACHE_FILE = Path("/tmp/relax_components.json")
if not COMPONENTS_CACHE_FILE.exists():
    COMPONENTS_CACHE_FILE.touch()
COMPONENTS_CACHE_FILE = COMPONENTS_CACHE_FILE.open("r+")
COMPONENTS_CACHE_FILE.seek(0)
COMPONENTS_CACHE_FILE.truncate()
COMPONENTS_CACHE_FILE.write("{}")
COMPONENTS_CACHE_FILE.seek(0)
_COMPONENT_NAMES: list[str] = []


class Jsonable(Protocol):
    def model_dump_json(self) -> str: ...

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
    ) -> Self: ...


def inject_into_kwargs(func: Callable, kwargs: Any) -> None:
    for name, sig in signature(func).parameters.items():
        if sig.default is _Injected:
            if sig.kind is not _ParameterKind.KEYWORD_ONLY:
                msg = (
                    f"Injected parameter {name} in "
                    f"{func.__name__} must be keyword-only"
                )
                raise IncorrectInjectableSignatureError(msg)
            if kwargs.get(name) is not None:
                pass
            elif sig.annotation in _INJECTS:
                kwargs.update({name: _INJECTS[sig.annotation]})
            else:
                msg = (
                    "Missing dependency for "
                    f"{name}: {sig.annotation} in {func.__name__}"
                )
                raise MissingDependencyError(msg)


def injectable(func: Callable[_P, Awaitable[_T]]) -> Callable[_P, Awaitable[_T]]:
    @wraps(func)
    async def inner(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        inject_into_kwargs(func, kwargs)
        return await func(*args, **kwargs)

    return inner


def injectable_sync(func: Callable[_P, _T]) -> Callable[_P, _T]:
    @wraps(func)
    def inner(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        inject_into_kwargs(func, kwargs)
        return func(*args, **kwargs)

    return inner


def add_injectable(annotation: object, injectable: object) -> None:
    if annotation in _INJECTS:
        msg = f"Injectable {annotation} already added"
        raise DoubleInjectionError(msg)
    _INJECTS[annotation] = injectable


def retrieve_injectable(annotation: type[_T]) -> _T:
    return _INJECTS[annotation]


def clear_injections() -> None:
    return _INJECTS.clear()


def component(
    key: Callable[..., str] | str | None = None,
) -> Callable[[Callable[_P, Element]], Callable[_P, Component]]:
    def decorator(
        func: Callable[_P, Element],
    ) -> Callable[_P, Component]:
        component_name = func.__name__.replace("_", "-")
        # TODO: don't do this in dev, or find a way to make it useful
        if component_name in _COMPONENT_NAMES:
            msg = f"Component {component_name} already registered"
            warnings.warn(msg, stacklevel=1)
        _COMPONENT_NAMES.append(component_name)

        @wraps(func)
        def inner(**kwargs: Jsonable) -> Component:
            if isinstance(key, str):
                key_val = key
                elem_id = f"{component_name}-{key_val}"
            elif key:
                lsig = signature(key)
                lambda_args = []
                for p_name in lsig.parameters:
                    lambda_args.append(kwargs[p_name])
                key_val = key(*lambda_args)
                elem_id = f"{component_name}-{key_val}"
            else:
                elem_id = component_name
            new_func = injectable_sync(func)
            if "id" in signature(func).parameters:
                # TODO: don't set the id if it was provided in the kwargs already
                func_call_result = new_func(id=elem_id, **kwargs)
            else:
                func_call_result = new_func(**kwargs)
            data = {key: to_json(val) for (key, val) in kwargs.items()}
            # TODO: find a way to do this only in dev mode
            try:
                current_views = json.load(COMPONENTS_CACHE_FILE)
                COMPONENTS_CACHE_FILE.seek(0)
            except (TypeError, FileNotFoundError):
                current_views = {}
            view_key = f"{func.__module__}.{func.__name__}"
            current_views[elem_id] = {
                "path": view_key,
                "data": data,
                "signature": str(signature(func)),
            }
            COMPONENTS_CACHE_FILE.truncate()
            json.dump(current_views, COMPONENTS_CACHE_FILE)
            COMPONENTS_CACHE_FILE.seek(0)

            return func_call_result.set_id(elem_id).classes([component_name])

        return inner

    return decorator


def to_json(obj: Any) -> str:
    if hasattr(obj, "model_dump_json"):
        obj = obj.model_dump(mode="json")
    return obj
