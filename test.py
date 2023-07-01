from main import (
    InputType,
    div,
    a,
    input,
    button,
    form,
    body,
    label,
    p,
)

element = body(classes=["bg-gray-900"]).insert(
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
)
