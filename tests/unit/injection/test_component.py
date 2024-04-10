import pytest
from relax import injection
from relax import html

# TODO: prevent cache file from being written


@injection.component()
def helper_component() -> html.Element:
    return html.div(text="helper")


def test_component_id_from_function_name():
    assert (
        helper_component().render()
        == '<div id="helper-component" class="helper-component">helper</div>'
    )


@injection.component(key="key")
def helper_component_with_str_key() -> html.Element:
    return html.div(text="helper")


def test_component_id_from_str_key():
    assert (
        helper_component_with_str_key().render()
        == '<div id="helper-component-with-str-key-key" class="helper-component-with-str-key">helper</div>'  # noqa: E501
    )


@injection.component(key="key")
def helper_component_with_used_id(*, id: str = injection.Injected) -> html.Element:
    return html.div(text=id)


def test_component_uses_injected_id():
    assert (
        helper_component_with_used_id().render()
        == '<div id="helper-component-with-used-id-key" class="helper-component-with-used-id">helper-component-with-used-id-key</div>'  # noqa: E501
    )


##### Test various args/kwarg combinations


@injection.component(key=lambda identifier: identifier)
def helper_component_with_pos_arg_key(identifier: str) -> html.Element:
    return html.div(text=identifier)


def test_component_pos_args_not_allowed_for_component_args():
    with pytest.raises(TypeError):
        helper_component_with_pos_arg_key("some-identifier")


@injection.component(key=lambda identifier: identifier)
def helper_component_with_kwarg_key(*, identifier: str) -> html.Element:
    return html.div(text=identifier)


def test_component_id_from_kwarg_key():
    assert (
        helper_component_with_kwarg_key(identifier="some-identifier").render()
        == '<div id="helper-component-with-kwarg-key-some-identifier" class="helper-component-with-kwarg-key">some-identifier</div>'  # noqa: E501
    )


@injection.component(
    key=lambda identifier, second_ident: identifier + "-" + second_ident,
)
def helper_component_with_multiple_kwarg_keys(
    *,
    identifier: str,
    second_ident: str,
) -> html.Element:
    return html.div(text=identifier + "." + second_ident)


def test_component_id_from_multiple_kwarg_keys():
    assert (
        helper_component_with_multiple_kwarg_keys(
            identifier="some-identifier",
            second_ident="second-identifier",
        ).render()
        == '<div id="helper-component-with-multiple-kwarg-keys-some-identifier-second-identifier" class="helper-component-with-multiple-kwarg-keys">some-identifier.second-identifier</div>'  # noqa: E501
    )


##### Injection


class HelperType:
    def __init__(self, identifier: str = "default") -> None:
        self.identifier = identifier


@pytest.fixture()
def inject_helper():
    injected_helper = HelperType()
    injection.add_injectable(HelperType, injected_helper)
    yield injected_helper
    injection._INJECTS.clear()


@injection.component(key=lambda identifier: identifier)
def helper_component_with_injection(
    identifier: str,
    *,
    some_dep: HelperType = injection.Injected,
) -> html.Element:
    return html.div(text=identifier + "-" + some_dep.identifier)


@pytest.mark.usefixtures(inject_helper.__name__)
def test_component_with_injection():
    assert (
        helper_component_with_injection(identifier="some-identifier").render()
        == '<div id="helper-component-with-injection-some-identifier" class="helper-component-with-injection">some-identifier-default</div>'  # noqa: E501
    )
