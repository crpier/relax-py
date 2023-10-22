from io import StringIO
from typing import Self
import copy
import warnings
from bs4 import BeautifulSoup, Tag
from pathlib import Path

start_recording = False


class BeautifulTag:
    def __init__(
        self, name: str, attrs: dict[str, str | list[str]], text: str | None = None
    ) -> None:
        self.name = name
        self._children: list[Self] = []
        self._attributes = attrs
        self._parent: BeautifulTag | None = None
        self._text = text.replace("\n", "").strip() if text else None

    def register_child(self, child: Self) -> None:
        self._children.append(child)
        child._parent = self

    def has_children(self) -> bool:
        return self._children != []

    def is_last_child(self) -> bool:
        if self._parent is None:
            return False
        return self._parent._children[-1] == self

    def parent_is_last_child(self) -> bool:
        if self._parent is None:
            return False
        return self._parent.is_last_child()

    def last_child_ancestry_streak(self) -> int:
        if self._parent is None:
            return 0
        if self.is_last_child():
            return 1 + self._parent.last_child_ancestry_streak()
        return 0

    def print_tree(self, destination: StringIO, indentation=""):

        print(indentation + self.name, end="", file=destination)

        element_classes = self._attributes.get("class", [])
        if isinstance(element_classes, list):
            classes: list[str] = element_classes
        else:
            warnings.warn(f"Class attribute is not a list: {element_classes=}")
            classes = [element_classes]
        attributes = copy.deepcopy(self._attributes)
        if "class" in attributes:
            del attributes["class"]

        print("(", end="", file=destination)
        if self.name == "input":
            input_type = self._attributes.get("type", "text")
            input_name = self._attributes.get("name", "TODO-name-me")
            print(f"type=InputType.{input_type},", end=" ", file=destination)
            print(f'name="{input_name}"', end="", file=destination)
            if classes or attributes or self.name == "a" or self.name == "label":
                print(",", end=" ", file=destination)
            if "type" in attributes:
                del attributes["type"]
            if "name" in attributes:
                del attributes["name"]
        if self.name == "label":
            print(f'_for="{self._attributes["for"]}"', end="", file=destination)
            if classes or attributes or self.name == "a":
                print(",", end=" ", file=destination)
                del attributes["for"]
        if self.name == "a":
            print(f'href="{self._attributes["href"]}"', end="", file=destination)
            if classes or attributes:
                print(",", end=" ", file=destination)
                del attributes["href"]
        if classes:
            print("classes=" + str(classes), end="", file=destination)
            if attributes:
                print(",", end=" ", file=destination)
        if attributes:
            print("attrs=" + str(attributes), end="", file=destination)
        print(")", end="", file=destination)

        if not self.has_children() and self._text is not None:
            print(f'.text("{self._text}")', end="", file=destination)

        if self.has_children():
            print(".insert(", file=destination)
        elif self.is_last_child():
            print(")" * self.last_child_ancestry_streak(), end="", file=destination)
            print(",", file=destination)
        else:
            print(",", file=destination)
        for child in self._children:
            child.print_tree(destination, indentation + "    ")


def parse_html_tree(tree: BeautifulSoup | Tag, parent: BeautifulTag) -> None:
    global start_recording
    new_element = None
    for child in tree:
        if isinstance(child, Tag):
            if child.name == "script":
                continue
            if child.name == "body":
                parse_html_tree(child, parent=new_element if new_element else parent)
                start_recording = True
            if start_recording:
                if child.string is not None and any(
                    isinstance(subchild, Tag) for subchild in child
                ):
                    warnings.warn(
                        f"Text and children detected in same element: {child.name=}"
                    )
                attrs: dict[str, str | list[str]] = child.attrs  # type: ignore
                new_element = BeautifulTag(child.name, attrs, child.string)
                parent.register_child(new_element)
            parse_html_tree(child, parent=new_element if new_element else parent)


bt = BeautifulTag("div", {})


with Path("test.html").open() as f:
    html = f.read()
a = BeautifulSoup(html, "html.parser")

string = StringIO()
print(
    "from html import InputType, div, li, a, img, ul, input, button, form, "
    "body, label, p",
    file=string,
)
print("element = ", end="", file=string)
parse_html_tree(a, parent=bt)
bt.print_tree(destination=string)
string.seek(0)
# There's a comma at the end
# I'd rather get rid of it than add a special case to the print_tree function
result = string.read()[:-2]
print(result)
