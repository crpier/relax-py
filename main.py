from collections import defaultdict
import warnings
from typing import Self


class SelfClosingTag:
    name: str

    def __init__(
        self,
        klass: str | None = None,
        attrs: dict | None = None,
        id: str | None = None,
    ) -> None:
        self._text: str = ""
        self._children: list[Self] = []
        self._attributes: dict = defaultdict(str)
        if klass:
            self.klass(klass)
        if attrs:
            self.attrs(attrs)
        if id:
            self.id(id)
        self._parent: SelfClosingTag | Tag | None = None

    def render(self) -> str:
        return f"<{self.name} {self._render_attributes()} />"

    def _render_attributes(self) -> str:
        return " ".join(
            [
                f'{key}="{value.strip()}"'.strip()
                for key, value in self._attributes.items()
            ]
        ).strip()

    def _render_children(self) -> str:
        return self._text + "".join([child.render() for child in self._children])

    def klass(self, classes: str) -> Self:
        self._attributes["class"] += f"{classes} "
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
            f"<{self.name} {self._render_attributes()}>"
            f"{self._render_children()}"
            f"</{self.name}>"
        )

    def insert(self, *inserted: "SelfClosingTag | Tag", append: bool = True) -> Self:
        children = list(inserted)
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


class a(Tag):
    name = "a"

    def __init__(self, *args, href: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._attributes["href"] = href


class li(Tag):
    name = "li"

    def render(self, *args, **kwargs) -> str:
        if self._parent and self._parent.name not in ["ul", "ol"]:
            warnings.warn(f'"{self.name}" element should be a child of "ul" or "ol"')
        return super().render()


class ul(Tag):
    name = "ul"

    def insert(self, *children: li, **kwargs):
        return super().insert(*children, **kwargs)


class label(Tag):
    name = "label"


class img(SelfClosingTag):
    name = "img"

    def __init__(self, *args, alt: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._attributes["alt"] = alt

    def render(self) -> str:
        return super().render()
