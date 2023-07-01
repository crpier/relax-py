from yahgl_py.main import (
    InputType,
    div,
    form,
    head,
    html,
    a,
    link,
    meta,
    label,
    script,
    style,
    title,
    input,
    body,
    button,
    p,
)

bod = body(classes=["bg-gray-900"]).insert(
    div(classes=["flex", "items-center", "justify-center", "h-screen"]).insert(
        button(
            classes=[
                "bg-blue-500",
                "hover:bg-blue-700",
                "text-white",
                "font-bold",
                "py-2",
                "px-4",
                "rounded",
                "focus:outline-none",
                "focus:shadow-outline",
            ],
            attrs={"onclick": "toggleModal()"},
        ).text("Open Login Form")
    ),
    div(classes=["modal"], attrs={"id": "login-modal"}).insert(
        div(classes=["flex", "items-center", "justify-center", "h-screen"]).insert(
            div(
                classes=[
                    "bg-gray-800",
                    "rounded-lg",
                    "shadow-md",
                    "px-8",
                    "pt-6",
                    "pb-8",
                ]
            ).insert(
                div(classes=["flex", "justify-between", "items-center", "mb-4"]).insert(
                    div(classes=["text-white", "text-4xl", "text-center"]).text(
                        "Login"
                    ),
                    button(
                        classes=["text-white", "text-2xl", "focus:outline-none"],
                        attrs={"onclick": "toggleModal()"},
                    ).text("×"),
                ),
                form().insert(
                    div(classes=["mb-4"]).insert(
                        label(
                            _for="username",
                            classes=[
                                "block",
                                "text-white",
                                "text-sm",
                                "font-bold",
                                "mb-2",
                            ],
                        ).text("Username"),
                        input(
                            type=InputType.text,
                            name="TODO-name-me",
                            classes=[
                                "shadow",
                                "appearance-none",
                                "border",
                                "rounded",
                                "w-full",
                                "py-2",
                                "px-3",
                                "text-gray-700",
                                "leading-tight",
                                "focus:outline-none",
                                "focus:shadow-outline",
                            ],
                            attrs={
                                "id": "username",
                                "placeholder": "Enter your username",
                            },
                        ),
                    ),
                    div(classes=["mb-6"]).insert(
                        label(
                            _for="password",
                            classes=[
                                "block",
                                "text-white",
                                "text-sm",
                                "font-bold",
                                "mb-2",
                            ],
                        ).text("Password"),
                        input(
                            type=InputType.password,
                            name="TODO-name-me",
                            classes=[
                                "shadow",
                                "appearance-none",
                                "border",
                                "border-red-500",
                                "rounded",
                                "w-full",
                                "py-2",
                                "px-3",
                                "text-gray-700",
                                "leading-tight",
                                "focus:outline-none",
                                "focus:shadow-outline",
                            ],
                            attrs={
                                "id": "password",
                                "placeholder": "******************",
                            },
                        ),
                        p(classes=["text-red-500", "text-xs", "italic", "mt-2"]).text(
                            "Please choose a password."
                        ),
                    ),
                    div(classes=["flex", "items-center", "justify-between"]).insert(
                        button(
                            classes=[
                                "bg-blue-500",
                                "hover:bg-blue-700",
                                "text-white",
                                "font-bold",
                                "py-2",
                                "px-4",
                                "rounded",
                                "focus:outline-none",
                                "focus:shadow-outline",
                            ],
                            attrs={"type": "button", "onclick": "toggleModal()"},
                        ).text("Sign In"),
                        a(
                            href="#",
                            classes=[
                                "inline-block",
                                "align-baseline",
                                "font-bold",
                                "text-sm",
                                "text-blue-500",
                                "hover:text-blue-800",
                            ],
                        ).text("Forgot Password?"),
                    ),
                ),
                p(classes=["text-center", "text-white", "text-xs", "mt-4"]).text(
                    "©2023 Company. All rights reserved."
                ),
            )
        )
    ),
    script(
        """
    function toggleModal() {
      const modal = document.getElementById('login-modal');
      modal.style.display = modal.style.display === 'block' ? 'none' : 'block';
    }"""
    ),
)

page = html(lang="en").insert(
    head().insert(
        title("Hello World!"),
        meta(charset="UTF-8"),
        meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        link(
            href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
            rel="stylesheet",
        ),
        style(
            """
    .modal {
      display: none;
      position: fixed;
      z-index: 9999;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.5);
    }
              """
        ),
    ),
    bod,
)

print(page.render())
