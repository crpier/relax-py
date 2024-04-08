import inspect
from typing import Any, Callable, ParamSpec, TypeVar, get_args
from inspect import signature

P = ParamSpec("P")
T = TypeVar("T")


def check(func: Callable[..., None]):  # noqa: ANN201
    renames = {}
    sig = signature(func)
    for name, val in sig.parameters.items():
        annotation = get_args(val.annotation)
        fixture_name = annotation[1].__name__
        renames[name] = fixture_name
    return _rename_parameters(func, renames)


def _rename_parameters(
    func: Callable[..., None],
    rename_dict: dict,
) -> Callable[..., None]:
    original_sig = inspect.signature(func)
    new_params = [
        param.replace(name=rename_dict.get(param.name, param.name))
        for param in original_sig.parameters.values()
    ]
    new_sig = original_sig.replace(parameters=new_params)

    def wrapper(*args: Any, **kwargs: Any):  # noqa: ANN202
        bound_args = new_sig.bind(*args, **kwargs)
        return func(*bound_args.args, **bound_args.kwargs)

    wrapper.__signature__ = new_sig  # type: ignore[reportFunctionMemberAccess]

    return wrapper
