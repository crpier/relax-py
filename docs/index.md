# relax-py

A Python web development framework for `htmx` and `tailwindcss`, with hot module replacement, built on top of [Starlette](https://www.starlette.io/).

## Features

- URL locators based on path functions, with errors based on type annotations.
- Write HTML templates with Python functions.
- Dependency injection helpers

## Usage

Starter example without hot module replacement:

```py
from relax.app import App, HTMLResponse, Request, Router, ViewContext
from relax.html import Element, button, div
from relax.injection import Injected, add_injectable, component
from relax.config import BaseConfig
from relax.server import start_app


router = Router()


def greeting_template(name: str) -> Element:
    return div(classes=["m-auto", "bg-gray-100"], text=f"Hello, {name}!")


@router.path_function("GET", "/hello")
async def hello(_: Request, *, config: BaseConfig = Injected) -> HTMLResponse:
    responder = "Developer" if config.ENV == "dev" else "World"
    template = greeting_template(responder)
    return HTMLResponse(template)


@component()
def home_page(*, context: ViewContext = Injected, id: str = Injected) -> Element:
    hello_url = context.url_of(hello)()
    return div(classes=["m-auto", "bg-gray-100"]).insert(
        button(text="Greet").hx_get(hello_url, hx_target=f"#{id}"),
    )


@router.path_function("GET", "/")
async def greet(_: Request) -> HTMLResponse:
    return HTMLResponse(home_page())


def app_factory() -> App:
    config = BaseConfig()
    add_injectable(BaseConfig, config)

    view_context = ViewContext()
    add_injectable(ViewContext, view_context)

    app = App(config=config, view_context=view_context)
    app.add_router(router)

    return app


if __name__ == "__main__":
    config = BaseConfig()
    start_app(
        app_path="app.main:app_factory",
        config=config,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
```
