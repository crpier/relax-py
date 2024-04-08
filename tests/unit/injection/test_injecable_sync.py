from typing import Annotated
import pytest
from relax import injection
from relax import test


class HelperType:
    def __init__(self, identifier: str = "default") -> None:
        self.identifier = identifier


@injection.injectable_sync
def helper_correct_function(
    *,
    helper_arg: HelperType = injection.Injected,
) -> HelperType:
    return helper_arg


@injection.injectable_sync
def helper_function_without_kwarg_only(
    helper_arg: HelperType = injection.Injected,
) -> HelperType:
    return helper_arg


@pytest.fixture()
def inject_helper():
    injected_helper = HelperType()
    injection.add_injectable(HelperType, injected_helper)
    yield injected_helper
    injection._INJECTS.clear()


@injection.injectable_sync
def function_with_normal_pos_args(
    normal_arg: str,
    *,
    helper_arg: HelperType = injection.Injected,
) -> tuple[str, HelperType]:
    return normal_arg, helper_arg


@injection.injectable_sync
def function_with_normal_kwargs(
    *,
    normal_kwarg: str,
    helper_arg: HelperType = injection.Injected,
) -> tuple[str, HelperType]:
    return normal_kwarg, helper_arg


@pytest.mark.usefixtures(inject_helper.__name__)
def test_double_injection_raises_error():
    with pytest.raises(injection.DoubleInjectionError):
        injection.add_injectable(HelperType, HelperType())


@test.check
def test_injection_is_performed(injected: Annotated[HelperType, inject_helper]):
    result = helper_correct_function()
    assert result is injected


def test_injection_on_function_with_pos_args_raises_error():
    with pytest.raises(injection.IncorrectInjectableSignatureError):
        helper_function_without_kwarg_only()


def test_missing_dependency_raises_error():
    with pytest.raises(injection.MissingDependencyError):
        helper_correct_function()


def test_args_can_be_given_manually():
    manual_helper = HelperType()
    result = helper_correct_function(helper_arg=manual_helper)
    assert result is manual_helper


@pytest.mark.usefixtures(inject_helper.__name__)
def test_manual_args_override_injected():
    manual_helper = HelperType(identifier="manual")
    result = helper_correct_function(helper_arg=manual_helper)
    assert result is manual_helper


@test.check
def test_function_with_normal_pos_args_and_injected_args(
    injected: Annotated[HelperType, inject_helper],
):
    arg_str = "normal"
    result_str, result_helper = function_with_normal_pos_args(arg_str)
    assert result_str is arg_str
    assert result_helper is injected


@test.check
def test_function_with_normal_pos_param_as_kwarg_and_injected_args(
    injected: Annotated[HelperType, inject_helper],
):
    arg_str = "normal"
    result_str, result_helper = function_with_normal_pos_args(normal_arg=arg_str)
    assert result_str is arg_str
    assert result_helper is injected


@test.check
def test_function_with_normal_kwargs_and_injected_args(
    injected: Annotated[HelperType, inject_helper],
):
    arg_str = "normal"
    result_str, result_helper = function_with_normal_kwargs(normal_kwarg=arg_str)
    assert result_str is arg_str
    assert result_helper is injected
