from typing import Literal, TypeAlias

import starlette.config
from pathlib import Path

ENV: TypeAlias = Literal["dev", "prod"]


def cast_to_env(value: str) -> Literal["dev", "prod"]:
    if value == "dev":
        return "dev"
    if value == "prod":
        return "prod"
    msg = f"Invalid value: {value}"
    raise ValueError(msg)


class BaseConfig:
    def __init__(self) -> None:
        self.config = starlette.config.Config()

        self.TEMPLATES_DIR = self.config("TEMPLATES_DIR", cast=Path)
        self.ENV = self.config("ENV", default="prod", cast=cast_to_env)
        self.PORT = self.config("ENV", default=443, cast=int)

    def __repr__(self) -> str:
        rep = self.__dict__.copy()
        del rep["config"]
        return rep.__repr__()
