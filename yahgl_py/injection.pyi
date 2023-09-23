from typing import Any, ParamSpec, TypeVar, Awaitable, Callable

P = ParamSpec("P")
T = TypeVar("T")
Injected: Any

def injectable(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]: ...
def add_injectable(annotation: Any, injectable: Any) -> None: ...
