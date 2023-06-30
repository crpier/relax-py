from collections import defaultdict
from typing import Self


class Tag:
    name: str

    def __init__(
        self,
        *args,
        klass: str | None = None,
        attrs: dict | None = None,
        id: str | None = None,
        href: str | None = None,
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
        if href:
            self.href(href)

    def render(self) -> str:
        return (
            f"<{self.name} {self._render_attributes()}>"
            f"{self._render_children()}"
            f"</{self.name}>"
        )

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

    def insert(self, *inserted: Self, append: bool = True) -> Self:
        children = list(inserted)
        if self._text:
            raise Exception("Cannot have text and children")
        if append:
            self._children.extend(children)
        else:
            self._children = children
        return self

    def id(self, value: str) -> Self:
        self._attributes["id"] = value
        return self

    def href(self, value: str) -> Self:
        self._attributes["href"] = value
        return self


def create_tag(name):
    return type(name, (Tag,), {"name": name})


div = create_tag("div")
a = create_tag("a")
li = create_tag("li")
label = create_tag("label")
