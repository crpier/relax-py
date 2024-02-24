"""
A simple dependency injection framework.

Decorate functions that need to be injected with `@injectable` and
annotate the parameters that need to be injected with `Injected`.

Note: Injected parameters must be keyword-only.

Example:
```python
@injectable
def do_print(
    foo: str = "default",
    *,
    bar: Annotated[str, Injected],
) -> None:
    print(foo)
    print(bar)
```
Running `do_print()` print
```
default
weird
```
"""
from collections.abc import Callable
from inspect import _ParameterKind, signature
from typing import Awaitable, Hashable, ParamSpec, TypeVar

from relax.html import Element


class MissingDependencyError(Exception):
    ...


class IncorrectInjectableSignatureError(Exception):
    ...


class DoubleInjectionError(Exception):
    ...


_INJECTS: dict[Hashable, object] = {}


class Injected:
    ...


_P = ParamSpec("_P")
_T = TypeVar("_T")


def injectable(func: Callable[_P, Awaitable[_T]]) -> Callable[_P, Awaitable[_T]]:
    async def inner(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        for name, sig in signature(func).parameters.items():
            if sig.default is Injected:
                if sig.kind is not _ParameterKind.KEYWORD_ONLY:
                    msg = (
                        f"Injected parameter {name} in "
                        f"function {func.__name__} must be keyword-only"
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
        return await func(*args, **kwargs)

    return inner


def injectable_sync(func: Callable[_P, _T]) -> Callable[_P, _T]:
    def inner(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        for name, sig in signature(func).parameters.items():
            if sig.default is Injected:
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
        return func(*args, **kwargs)

    return inner


def add_injectable(annotation: Hashable, injectable: object) -> None:
    if annotation in _INJECTS:
        msg = f"Injectable {annotation} already added"
        raise DoubleInjectionError(msg)
    _INJECTS[annotation] = injectable


_COMPONENT_NAMES: list[str] = []
_COMPONENT_IDS: list[str] = []


def component(key: Callable[..., str] | str | None = None):
    def decorator(func: Callable[..., Element]):
        component_name = func.__name__.replace("_", "-")
        if component_name in _COMPONENT_NAMES:
            msg = f"Component {component_name} already registered"
            raise ValueError(msg)
        _COMPONENT_NAMES.append(component_name)

        def inner(**kwargs):
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
                func_call_result = new_func(id=elem_id, **kwargs)
            else:
                func_call_result = new_func(**kwargs)
            return func_call_result.set_id(elem_id).classes([component_name])

        return inner

    return decorator
