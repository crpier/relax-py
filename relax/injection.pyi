from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

from relax.html import Component, Element

_COMPONENT_NAMES: list[str]
_P = ParamSpec("_P")
_T = TypeVar("_T")
Injected: Any

def injectable(func: Callable[_P, Awaitable[_T]]) -> Callable[_P, Awaitable[_T]]: ...
def injectable_sync(func: Callable[_P, _T]) -> Callable[_P, _T]: ...
def add_injectable(annotation: Any, injectable: Any) -> None: ...
def component(
    key: Callable[..., str] | str | None = None,
) -> Callable[[Callable[_P, Element]], Callable[_P, Component]]: ...
