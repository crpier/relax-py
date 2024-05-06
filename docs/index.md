# relax-py

A Python web development framework for `htmx` and `tailwindcss`, with hot module replacement, built on top of [Starlette](https://www.starlette.io/).

## Features

- URL locators based on path functions, with errors based on type annotations.
- Write HTML templates with Python functions.
- Dependency injection helpers

## Usage

Starter example with hot module replacement:

In `app/main.py`:

```py
from relax.app import App, HTMLResponse, Request, Router, ViewContext, websocket_endpoint
from relax.html import div
from relax.injection import Injected, add_injectable
from relax.config import BaseConfig
from relax.server import start_app

import app.templates

router = Router()


@router.path_function("GET", "/hello")
async def hello(request: Request, *, config: BaseConfig = Injected) -> HTMLResponse:
    responder = "Developer" if config.ENV == "dev" else "World"
    template = app.templates.greeting_template(responder)
    if request.scope["from_htmx"]:
        return HTMLResponse(template)
    else:
        return HTMLResponse(app.templates.page_root(template))


@router.path_function("GET", "/")
async def home(request: Request) -> HTMLResponse:
    if request.scope["from_htmx"]:
        return HTMLResponse(div(text="Request from htmx not supported on home page"))
    return HTMLResponse(app.templates.page_root(app.templates.home_page()))


def app_factory() -> App:
    config = BaseConfig()
    add_injectable(BaseConfig, config)

    view_context = ViewContext()
    add_injectable(ViewContext, view_context)

    app = App(config=config, view_context=view_context)
    app.add_router(router)
    app.add_websocket_route("/ws", websocket_endpoint, name="ws")
    if config.ENV == "dev":
        app.listen_to_template_changes()


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

In `app/templates/__init__.py`:

```py
from relax.app import ViewContext
from relax.html import (
    Element,
    body,
    button,
    div,
    head,
    hmr_script,
    html,
    meta,
    script,
    title,
)
from relax.injection import Injected, component

import app.main


def page_root(child: Element) -> Element:
    head_element = head().insert(
        title("Example app"),
        meta(charset="UTF-8"),
        meta(
            name="viewport",
            content="width=device-width, initial-scale=1.0, maximum-scale=1.0",
        ),
        script(
            src="https://unpkg.com/htmx.org@1.9.5",
            attrs={
                "integrity": "sha384-xcuj3WpfgjlKF+FXhSQF"
                "Q0ZNr39ln+hwjN3npfM9VBnUskLolQAcN80McRIVOPuO",
                "crossorigin": "anonymous",
            },
        ),
        script(src="https://cdn.tailwindcss.com"),
        hmr_script(),
    )
    return html(lang="en").insert(
        head_element,
        body(classes=["p-4"]).insert(child),
    )


def greeting_template(name: str) -> Element:
    return div(
        classes=["m-auto", "bg-blue-200", "p-2", "w-max", "rounded-md"],
        text=f"Hello, {name}!",
    )


@component()
def home_page(*, context: ViewContext = Injected, id: str = Injected) -> Element:
    hello_url = context.url_of(app.main.hello)()
    return div(classes=["m-auto", "bg-green-400", "p-2", "rounded-lg", "w-max"]).insert(
        button(text="Greet").hx_get(hello_url, hx_target=f"#{id}", hx_swap="outerHTML"),
    )
```

then run this with:
```sh
env ENV=dev TEMPLATES_DIR=app/templates python app/main.py
```
