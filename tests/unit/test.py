from typing import Annotated

import pytest

from relax.test import check


A = Annotated


@pytest.fixture()
def new_sku() -> str:
    return "42"


@check
def test_sku(sku: A[str, new_sku]):
    assert sku == "42"
