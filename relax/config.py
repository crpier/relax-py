from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BeforeValidator, Field
from pathlib import Path
from pydantic_settings import BaseSettings

ENV: TypeAlias = Literal["dev", "prod"]


def cast_to_env(value: str) -> Literal["dev", "prod"]:
    if value == "dev":
        return "dev"
    if value == "prod":
        return "prod"
    msg = f"Invalid value: {value}"
    raise ValueError(msg)


def cast_abs_path(value: Any) -> Path:
    return Path(value).absolute()


AbsolutePath = Annotated[Path, BeforeValidator(cast_abs_path)]


class BaseConfig(BaseSettings):
    # TODO: make it so that this is optional in PROD
    TEMPLATES_DIR: AbsolutePath = Field(default=...)
    ENV: Literal["DEV", "PROD", "TEST"] = Field(default=...)
    PORT: int = Field(default=8000)
    RELOAD_SOCKET_PATH: AbsolutePath = Field(
        default=Path("~/.cache/relax-reload").expanduser()
    )
    JS_CONSTANTS_PATH: AbsolutePath = Field(default=Path("static/js/constants.js"))
