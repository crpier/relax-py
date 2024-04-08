import pytest

from relax import html


@pytest.fixture()
def new_sku() -> str:
    return "42"


def test_element_render():
    element = html.div()
    assert element.render() == "<div></div>"


def test_element_with_text_in_arg():
    element = html.div(text="hello")
    assert element.render() == "<div>hello</div>"


def test_element_with_text_in_method():
    element = html.div().text("hello")
    assert element.render() == "<div>hello</div>"


def test_element_insert():
    element = html.div().insert(html.div())
    assert element.render() == "<div><div></div></div>"


def test_element_insert_and_text_raises_error():
    with pytest.raises(html.InvalidHTMLError):
        html.div(text="oof").insert(html.div())


def test_element_classes_in_arg():
    element = html.div(classes=["class1", "class2"])
    assert element.render() == '<div class="class1 class2"></div>'


def test_element_classes_in_method():
    element = html.div().classes(["class1", "class2"])
    assert element.render() == '<div class="class1 class2"></div>'


def test_element_custom_attrs_in_arg():
    element = html.div(attrs={"data-foo": "bar"})
    assert element.render() == '<div data-foo="bar"></div>'


def test_element_custom_attrs_in_method():
    element = html.div().attrs({"data-foo": "bar"})
    assert element.render() == '<div data-foo="bar"></div>'


def test_element_id_in_arg():
    element = html.div(id="foo")
    assert element.render() == '<div id="foo"></div>'


def test_element_id_in_method():
    element = html.div().set_id("foo")
    assert element.render() == '<div id="foo"></div>'


def test_element_hx_get():
    element = html.div().hx_get("some-url")
    assert element.render() == '<div hx-get="some-url"></div>'


def test_button_with_all_args():
    element = html.button(
        text="click me",
        classes=["p-4", "bg-green-500"],
        attrs={"data-foo": "bar"},
        id="foo",
        type="submit",
    )
    assert element.render() == (
        '<button data-foo="bar" id="foo" type="submit" class="p-4 bg-green-500">click me</button>'  # noqa: E501
    )


def test_form_with_all_args():
    element = html.form(
        classes=["p-4", "bg-green-500"],
        attrs={"data-foo": "bar"},
        id="foo",
        hyperscript="post",
        action="some-url",
    )
    assert element.render() == (
        '<form data-foo="bar" id="foo" _="post" action="some-url" class="p-4 bg-green-500"></form>'  # noqa: E501
    )


def test_a_with_all_args():
    element = html.a(
        href="some-url",
        target="_blank",
        classes=["p-4", "bg-green-500"],
        attrs={"data-foo": "bar"},
        id="foo",
        hyperscript="post",
        text="click me",
    )
    assert element.render() == (
        '<a data-foo="bar" id="foo" _="post" href="some-url" target="_blank" class="p-4 bg-green-500">click me</a>'  # noqa: E501
    )


def test_orphan_li_gives_warning():
    with pytest.warns(match='"li" element should be a child of "ul" or "ol"'):
        html.li().render()


def test_li_with_non_list_parent_gives_warning():
    with pytest.warns(match='"li" element should be a child of "ul" or "ol"'):
        html.div().insert(html.li()).render()


def test_label_without_sibling_input_gives_warning():
    with pytest.warns(
        match='"label" element should have a sibling "input"',
    ):
        html.label("aa").render()
