import warnings
import sys
from pathlib import Path
from collections.abc import Iterable
from html import escape
from typing import Literal, Protocol, Self, Sequence, TypeVar

from starlette.datastructures import URL

HREFTarget = Literal["_blank", "_self", "_parent", "_top"]

InputType = Literal[
    "text",
    "email",
    "password",
    "number",
    "date",
    "file",
    "hidden",
    "checkbox",
    "radio",
    "button",
]

ButtonType = Literal["button", "submit", "reset"]

HTMXRequestType = Literal["get", "post", "put", "delete"]


class InvalidHTMLError(Exception):
    ...


T = TypeVar("T")


class Element(Protocol):
    _parent: "Tag | None"
    name: str

    def render(self) -> str:
        ...

    def set_id(self, value: str) -> Self:
        ...

    @property
    def id(self) -> str | None:
        ...

    def classes(self, classes: list[str]) -> Self:
        ...

    def attrs(self, attrs: dict) -> Self:
        ...

    def hx_get(
        self,
        target: str | URL,
        hx_encoding: Literal["multipart/form-data"] | None = None,
        hx_target: str | Self | None = None,
        hx_swap: Literal[
            "innerHTML",
            "outerHTML",
            "beforebegin",
            "afterbegin",
            "beforeend",
            "afterend",
            "delete",
            "none",
        ]
        | None = None,
        **kwargs: str,
    ) -> Self:
        ...


class Component(Element, Protocol):
    @property
    def id(self) -> str:
        ...


class SelfClosingTag(Element):
    name: str

    def __init__(
        self,
        *,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
    ) -> None:
        self._text: str = ""
        self._attributes: dict = {}
        self._classes: list[str] = []
        if classes:
            self.classes(classes)
        if attrs:
            self.attrs(attrs)
        if id:
            self.set_id(id)
        if hyperscript:
            self.hyperscript(hyperscript)
        self._parent: Tag | None = None

    def render(self) -> str:
        return f"<{self.name} {self._render_attributes()} />"

    def _render_attributes(self) -> str:
        attributes = [
            f'{escape(key)}="{escape(str(value).strip())}"'.strip()
            for key, value in self._attributes.items()
        ]
        if self._classes:
            attributes.append(
                f'class="{" ".join([escape(klass) for klass in self._classes])}"',
            )
        if attributes:
            return " " + " ".join(attributes).strip()
        return ""

    def classes(self, classes: list[str]) -> Self:
        self._classes.extend(classes)
        return self

    def hyperscript(self, command: str) -> Self:
        self._attributes["_"] = command
        return self

    def attrs(self, attrs: dict) -> Self:
        self._attributes.update(attrs)
        return self

    def set_id(self, value: str) -> Self:
        self._attributes["id"] = value
        return self

    @property
    def id(self) -> str | None:
        return self._attributes["id"]

    def _htmx(
        self,
        request_type: HTMXRequestType,
        target: str | URL,
        hx_encoding: Literal["multipart/form-data"] | None = None,
        hx_target: str | Self | None = None,
        hx_swap: Literal[
            "innerHTML",
            "outerHTML",
            "beforebegin",
            "afterbegin",
            "beforeend",
            "afterend",
            "delete",
            "none",
        ]
        | None = None,
        **kwargs: str,
    ) -> Self:
        self._attributes["hx-" + request_type] = target
        if hx_encoding:
            self._attributes["hx-encoding"] = hx_encoding
        if isinstance(hx_target, SelfClosingTag):
            try:
                self._attributes["hx-target"] = hx_target._attributes["id"]
            except KeyError as exc:
                msg = (
                    f"Target element {hx_target.__class__.__name__} "
                    "must have an id attribute"
                )
                raise InvalidHTMLError(msg) from exc
        elif isinstance(hx_target, str):
            self._attributes["hx-target"] = hx_target
        if hx_swap:
            self._attributes["hx-swap"] = hx_swap
        for key, value in kwargs.items():
            attr = key.replace("_", "-")
            self._attributes[attr] = value
        return self

    def hx_get(
        self,
        target: str | URL,
        hx_encoding: Literal["multipart/form-data"] | None = None,
        hx_target: str | Self | None = None,
        hx_swap: Literal[
            "innerHTML",
            "outerHTML",
            "beforebegin",
            "afterbegin",
            "beforeend",
            "afterend",
            "delete",
            "none",
        ]
        | None = None,
        **kwargs: str,
    ) -> Self:
        return self._htmx("get", target, hx_encoding, hx_target, hx_swap, **kwargs)

    def hx_post(
        self,
        target: str | URL,
        hx_encoding: Literal["multipart/form-data"] | None = None,
        hx_target: str | Self | None = None,
        hx_swap: Literal[
            "innerHTML",
            "outerHTML",
            "beforebegin",
            "afterbegin",
            "beforeend",
            "afterend",
            "delete",
            "none",
        ]
        | None = None,
        **kwargs: str,
    ) -> Self:
        return self._htmx("post", target, hx_encoding, hx_target, hx_swap, **kwargs)

    def hx_put(
        self,
        target: str | URL,
        hx_encoding: Literal["multipart/form-data"] | None = None,
        hx_target: str | Self | None = None,
        hx_swap: Literal[
            "innerHTML",
            "outerHTML",
            "beforebegin",
            "afterbegin",
            "beforeend",
            "afterend",
            "delete",
            "none",
        ]
        | None = None,
        **kwargs: str,
    ) -> Self:
        return self._htmx("put", target, hx_encoding, hx_target, hx_swap, **kwargs)

    def hx_delete(
        self,
        target: str | URL,
        hx_encoding: Literal["multipart/form-data"] | None = None,
        hx_target: str | Self | None = None,
        hx_swap: Literal[
            "innerHTML",
            "outerHTML",
            "beforebegin",
            "afterbegin",
            "beforeend",
            "afterend",
            "delete",
            "none",
        ]
        | None = None,
        **kwargs: str,
    ) -> Self:
        return self._htmx("delete", target, hx_encoding, hx_target, hx_swap, **kwargs)


class Tag(SelfClosingTag):
    def __init__(
        self,
        *,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
        text: str | None = None,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        self._children: list[Element] = []
        if text is not None:
            self.text(text)

    def render(self) -> str:
        return (
            f"<{self.name}{self._render_attributes()}>"
            f"{self._render_children()}"
            f"</{self.name}>"
        )

    def _render_children(self) -> str:
        return escape(self._text) + "".join(
            [child.render() for child in self._children],
        )

    def text(self, text: str) -> Self:
        self._text = text
        if self._children:
            msg = "Cannot have text and children"
            raise InvalidHTMLError(msg)
        return self

    def insert(
        self,
        *children: Sequence[Element] | Element | None,
        append: bool = True,
    ) -> Self:
        if self._text:
            msg = "Cannot have text and children"
            raise InvalidHTMLError(msg)

        # since we are so lenient with what we accept
        # sieve arguments until we get just a list of elements
        final_list: list[Element] = []
        for child in children:
            if child is None:
                continue
            if isinstance(child, Iterable):
                for sub_child in child:
                    final_list.append(sub_child)
                    sub_child._parent = self
            else:
                final_list.append(child)
                child._parent = self
        if append:
            self._children.extend(final_list)
        else:
            self._children = final_list
        return self


class Fragment(Tag):
    name = "<>"

    def __init__(
        self,
        children: Sequence[Element | None] | None,
    ) -> None:
        super().__init__()
        self.insert(children)

    def render(self) -> str:
        return super()._render_children()


class div(Tag):
    name = "div"


class main(Tag):
    name = "main"


class progress(Tag):
    name = "progress"


class nav(Tag):
    name = "nav"


class p(Tag):
    name = "p"


class span(Tag):
    name = "span"


class body(Tag):
    name = "body"


class button(Tag):
    name = "button"

    def __init__(
        self,
        *,
        type: ButtonType | None = None,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
        text: str | None = None,
    ) -> None:
        super().__init__(
            classes=classes,
            attrs=attrs,
            id=id,
            hyperscript=hyperscript,
            text=text,
        )
        if type:
            self._attributes["type"] = type
        else:
            self._attributes["type"] = "button"


class form(Tag):
    name = "form"

    def __init__(
        self,
        *,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
        action: str | None = None,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        if action is not None:
            self._attributes["action"] = action


class i(Tag):
    name = "i"


class a(Tag):
    name = "a"

    def __init__(
        self,
        href: str | URL,
        target: HREFTarget | None = None,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
        text: str | None = None,
    ) -> None:
        super().__init__(
            classes=classes,
            attrs=attrs,
            id=id,
            hyperscript=hyperscript,
            text=text,
        )
        self._attributes["href"] = href
        if target:
            self._attributes["target"] = target


class li(Tag):
    name = "li"

    def render(self) -> str:
        if not self._parent:
            warnings.warn(
                f'"{self.name}" element should be a child of "ul" or "ol"',
                stacklevel=2,
            )

        if self._parent and self._parent.name not in ["ul", "ol"]:
            warnings.warn(
                f'"{self.name}" element should be a child of "ul" or "ol"',
                stacklevel=2,
            )
        return super().render()


class ul(Tag):
    name = "ul"
    # TODO: warning when children are not "li"


class label(Tag):
    name = "label"

    def __init__(
        self,
        _for: str | None = None,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        if _for is not None:
            self._attributes["for"] = _for


class svg(Tag):
    name = "svg"


class path(Tag):
    name = "path"


class select(Tag):
    name = "select"

    def __init__(
        self,
        name: str,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        self._attributes["name"] = name


class option(Tag):
    name = "option"

    def __init__(
        self,
        value: str,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        self._attributes["value"] = value


class input(SelfClosingTag):
    name = "input"

    def __init__(
        self,
        name: str,
        type: InputType,
        value: str | None = None,
        placeholder: str | None = None,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        self._attributes["name"] = name
        self._attributes["type"] = type
        if value:
            self._attributes["value"] = value
        if placeholder:
            self._attributes["placeholder"] = placeholder
        if disabled is True:
            self._attributes["disabled"] = True


class img(SelfClosingTag):
    name = "img"

    def __init__(
        self,
        src: str,
        alt: str,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        self._attributes["alt"] = alt
        self._attributes["src"] = src


class video(Tag):
    name = "video"

    def __init__(
        self,
        src: str,
        *,
        controls: bool = False,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes, attrs=attrs, hyperscript=hyperscript)
        self._attributes["src"] = src
        if controls:
            self._attributes["controls"] = "true"


class textarea(Tag):
    name = "textarea"

    def __init__(
        self,
        name: str,
        type: InputType,
        placeholder: str | None = None,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        self._attributes["name"] = name
        self._attributes["type"] = type
        if placeholder:
            self._attributes["placeholder"] = placeholder
        if disabled is True:
            self._attributes["disabled"] = True


class meta(SelfClosingTag):
    name = "meta"

    def __init__(
        self,
        *,
        charset: str | None = None,
        name: str | None = None,
        content: str | None = None,
    ) -> None:
        if charset and (name or content):
            msg = "Cannot have charset and name/content"
            raise InvalidHTMLError(msg)
        if charset:
            super().__init__(attrs={"charset": charset})
        else:
            super().__init__(attrs={"name": name, "content": content})


class link(SelfClosingTag):
    name = "link"

    def __init__(self, *, href: str, rel: str, type: str | None = None) -> None:
        super().__init__(attrs={"href": href, "rel": rel})
        if type is not None:
            self._attributes["type"] = type


class title(Tag):
    name = "title"

    def __init__(self, name: str) -> None:
        super().__init__()
        self.text(name)


class style(Tag):
    name = "style"

    def __init__(self, stylesheet: str) -> None:
        super().__init__()
        self.text(stylesheet)


class script(Tag):
    name = "script"

    def __init__(
        self,
        js: str | None = None,
        src: str | None = None,
        attrs: dict | None = None,
        *,
        type: Literal["importmap", "module", "speculationrules"] | None = None,
        defer: bool = False,
    ) -> None:
        super().__init__()
        if js is not None:
            self.text(js)
        elif src is not None:
            self._attributes["src"] = src
        else:
            msg = "<script> element must have js or src"
            raise InvalidHTMLError(msg)
        if attrs is not None:
            self._attributes.update(attrs)
        if defer:
            self._attributes["defer"] = "true"
        if type is not None:
            self._attributes["type"] = type

    # sorry mate can't help you escape that
    # your risk
    def _render_children(self) -> str:
        return self._text + "".join([child.render() for child in self._children])


class head(Tag):
    name = "head"
    # TODO: ensure only meta | link | title | style | script elements can be inserted


class html(Tag):
    name = "html"

    def __init__(
        self,
        lang: str,
        classes: list[str] | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        hyperscript: str | None = None,
    ) -> None:
        super().__init__(classes=classes, attrs=attrs, id=id, hyperscript=hyperscript)
        self._attributes["lang"] = lang

    # TODO: ensure only head | body can be inserted

    def render(self) -> str:
        return "<!DOCTYPE html>" + super().render()


class aside(Tag):
    name = "aside"

class details(Tag):
    name = "details"

class summary(Tag):
    name = "summary"

class dialog(Tag):
    name = "dialog"

class h1(Tag):
    name = "h1"


class h2(Tag):
    name = "h2"


class h3(Tag):
    name = "h3"


class h4(Tag):
    name = "h4"

class h5(Tag):
    name = "h5"

class figure(Tag):
    name = "figure"

def hmr_script() -> list[script]:
    file_path = sys.modules[__name__].__file__
    if file_path is None:
        msg = "Cannot find current file path"
        raise RuntimeError(msg)
    current_path = Path(file_path)
    with (current_path.parent / "js" / "hmr_reload.js").open() as f:
        return [
            script(
                js=f.read(),
            ),
            script(src="https://unpkg.com/idiomorph@0.3.0"),
        ]
