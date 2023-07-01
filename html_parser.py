from typing import Self
import copy
import warnings
from bs4 import BeautifulSoup, Tag
from pathlib import Path

start_recording = False


class BeautifulTag:
    def __init__(
        self, name: str, attrs: dict[str, str], text: str | None = None
    ) -> None:
        self.name = name
        self._children = []
        self._attributes = attrs
        self._parent: BeautifulTag | None = None

    def register_child(self, child: Self) -> None:
        self._children.append(child)
        child._parent = self

    def has_children(self) -> bool:
        return self._children != []

    def is_last_child(self) -> bool:
        return self._parent and self._parent._children[-1] == self

    def last_child_ancestry_streak(self) -> int:
        if self.is_last_child():
            return 1 + self._parent.last_child_ancestry_streak()
        return 0

    def print_tree(self, indentation=""):

        print(indentation + self.name, end="")

        classes = self._attributes.get("class", [])
        attributes = copy.deepcopy(self._attributes)
        if "class" in attributes:
            del attributes["class"]

        print("(", end="")
        if self.name == "label":
            print(f'_for="{self._attributes["for"]}"', end="")
            if classes or attributes or self.name == "a":
                print(",", end=" ")
                del attributes["for"]
        if self.name == "a":
            print(f'href="{self._attributes["href"]}"', end="")
            if classes or attributes:
              print(",", end=" ")
              del attributes["href"]
        if classes:
            print("classes=" + str(classes), end="")
            if attributes:
                  print(",", end=" ")
        if attributes:
            print("attrs=" + str(attributes), end="")
        print(")", end="")


        if self.has_children():
            print(".insert(")
        elif self.is_last_child():
            print(")" * self.last_child_ancestry_streak(), end="")
            if self._parent.is_last_child():
                print(",")
            else:
                print(",")
        else:
            print(",")
        for child in self._children:
            child.print_tree(indentation + "    ")


def parse_html_tree(tree: BeautifulSoup, parent: BeautifulTag) -> None:
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
                new_element = BeautifulTag(child.name, child.attrs, child.string)
                parent.register_child(new_element)
            parse_html_tree(child, parent=new_element if new_element else parent)


bt = BeautifulTag("div", {})


with Path("test.html").open() as f:
    html = f.read()

a = BeautifulSoup(html, "html.parser")
print(
    "from main import InputType, div, li, a, img, ul, input, button, form, "
    "body, label, p, InputType"
)
print("lol = ", end="")
parse_html_tree(a, parent=bt)
bt.print_tree()
