from enum import StrEnum, auto
import warnings
from typing import Self


class HREFTarget(StrEnum):
    _blank = auto()
    _self = auto()
    _parent = auto()
    _top = auto()


class InputType(StrEnum):
    text = auto()
    email = auto()
    password = auto()
    number = auto()
    date = auto()
    file = auto()
    hidden = auto()
    checkbox = auto()
    radio = auto()
    button = auto()


class SelfClosingTag:
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
        self._children: list[Self] = []
        self._attributes: dict = {}
        self._classes: list[str] = []
        if classes:
            self.classes(classes)
        if attrs:
            self.attrs(attrs)
        if id:
            self.id(id)
        if hyperscript:
            self._attributes["_"] = hyperscript
        self._parent: Tag | None = None

    def render(self) -> str:
        return f"<{self.name} {self._render_attributes()} />"

    def _render_attributes(self) -> str:
        attributes = [
            f'{key}="{value.strip()}"'.strip()
            for key, value in self._attributes.items()
        ]
        if self._classes:
            attributes.append(f'class="{" ".join(self._classes)}"')
        if attributes:
            return " " + " ".join(attributes).strip()
        else:
            return ""

    def _render_children(self) -> str:
        return self._text + "".join([child.render() for child in self._children])

    def classes(self, classes: list[str]) -> Self:
        self._classes.extend(classes)
        return self

    def text(self, text: str) -> Self:
        self._text = text
        if self._children:
            raise Exception("Cannot have text and children")
        return self

    def attrs(self, attrs: dict) -> Self:
        self._attributes.update(attrs)
        return self

    def id(self, value: str) -> Self:
        self._attributes["id"] = value
        return self


class Tag(SelfClosingTag):
    def render(self) -> str:
        return (
            f"<{self.name}{self._render_attributes()}>"
            f"{self._render_children()}"
            f"</{self.name}>"
        )

    def insert(
        self,
        *inserted: "SelfClosingTag | Tag | list[SelfClosingTag] | list[Tag]",
        append: bool = True,
    ) -> Self:
        children: list["SelfClosingTag | Tag"] = []
        for insert in inserted:
            if isinstance(insert, list):
                children.extend(insert)
            else:
                children.append(insert)

        for child in children:
            child._parent = self
        if self._text:
            raise Exception("Cannot have text and children")
        if append:
            self._children.extend(children)
        else:
            self._children = children
        return self


class div(Tag):
    name = "div"


class nav(Tag):
    name = "nav"


class p(Tag):
    name = "p"


class body(Tag):
    name = "body"


class button(Tag):
    name = "button"

    def __init__(self, type: str | None = None, **kwargs):
        super().__init__(**kwargs)
        if type:
            self._attributes["type"] = type


class form(Tag):
    name = "form"


class i(Tag):
    name = "i"


class a(Tag):
    name = "a"

    def __init__(self, href: str, target: HREFTarget | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._attributes["href"] = href
        if target:
            self._attributes["target"] = target


class li(Tag):
    name = "li"

    def render(self) -> str:
        if self._parent and self._parent.name not in ["ul", "ol"]:
            warnings.warn(f'"{self.name}" element should be a child of "ul" or "ol"')
        return super().render()


class ul(Tag):
    name = "ul"

    def insert(self, *children: li, **kwargs):
        return super().insert(*children, **kwargs)


class label(Tag):
    name = "label"

    def __init__(self, _for: str, **kwargs):
        super().__init__(**kwargs)
        self._attributes["for"] = _for

    def render(self) -> str:
        if self._parent:
            if all(sibling.name not in ["input"] for sibling in self._parent._children):
                warnings.warn(f'"{self.name}" element should have a sibling "input"')
        return super().render()


class input(SelfClosingTag):
    name = "input"

    def __init__(
        self,
        name: str,
        type: InputType,
        value: str | None = None,
        placeholder: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._attributes["name"] = name
        self._attributes["type"] = type.value
        if value:
            self._attributes["value"] = value
        if placeholder:
            self._attributes["placeholder"] = placeholder


class img(SelfClosingTag):
    name = "img"

    def __init__(self, src: str, alt: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._attributes["alt"] = alt
        self._attributes["src"] = src


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
            raise Exception("Cannot have charset and name/content")
        if charset:
            super().__init__(attrs={"charset": charset})
        else:
            super().__init__(attrs={"name": name, "content": "content"})


class link(SelfClosingTag):
    name = "link"

    def __init__(self, *, href: str, rel: str) -> None:
        super().__init__(attrs={"href": href, "rel": rel})


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
        self, js: str | None = None, src: str | None = None, attrs: dict | None = None
    ) -> None:
        super().__init__()
        if js is not None:
            self.text(js)
        elif src is not None:
            self._attributes["src"] = src
        else:
            raise Exception("script element must have js or src")
        if attrs is not None:
            self._attributes.update(attrs)


class head(Tag):
    name = "head"

    def insert(self, *inserted: meta | link | title | style | script, **kwargs):
        return super().insert(*inserted, **kwargs)


class html(Tag):
    name = "html"

    def __init__(self, lang: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._attributes["lang"] = lang

    def insert(self, *inserted: head | body, **kwargs):
        return super().insert(*inserted, **kwargs)

    def render(self) -> str:
        return "<!DOCTYPE html>" + super().render()
