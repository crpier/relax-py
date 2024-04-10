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


def cast_abs_path(value: str) -> Path:
    return Path(value).absolute()


class BaseConfig:
    def __init__(self) -> None:
        self.config = starlette.config.Config()

        self.TEMPLATES_DIR = self.config("TEMPLATES_DIR", cast=cast_abs_path)
        self.ENV = self.config("ENV", default="prod", cast=cast_to_env)
        self.PORT = self.config("PORT", default=443, cast=int)
        self.RELOAD_SOCKET_PATH = self.config(
            "RELOAD_SOCKET_PATH",
            default=Path("/tmp/relax-reload"),
            cast=cast_abs_path,
        )
        self.JS_CONSTANTS_PATH = self.config(
            "JS_CONSTANTS_PATH",
            default=Path("static/js/constants.js"),
            cast=Path,
        )

    def __repr__(self) -> str:
        rep = self.__dict__.copy()
        del rep["config"]
        return rep.__repr__()
