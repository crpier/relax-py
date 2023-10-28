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


class MissingDependencyError(Exception):
    ...


class IncorrectInjectableSignatureError(Exception):
    ...


class DoubleInjectionError(Exception):
    ...


_INJECTS: dict[Hashable, object] = {}


class Injected:
    ...


P = ParamSpec("P")
T = TypeVar("T")


def injectable(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
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
        return await func(*args, **kwargs)

    return inner


def injectable_sync(func: Callable[P, T]) -> Callable[P, T]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> T:
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
