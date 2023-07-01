from main import InputType, div, a, input, button, form, body, label, p

lol = body(classes=["bg-gray-900"]).insert(
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
        )
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
                div(classes=["text-white", "text-4xl", "mb-8", "text-center"]),
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
                        ),
                        input(
                            name="big oof",
                            type=InputType.text,
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
                                "type": "text",
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
                        ),
                        input(
                            name="big oof",
                            type=InputType.text,
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
                                "type": "password",
                                "placeholder": "******************",
                            },
                        ),
                        p(classes=["text-red-500", "text-xs", "italic", "mt-2"]),
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
                        ),
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
                        ),
                    ),
                ),
                p(classes=["text-center", "text-white", "text-xs", "mt-4"]),
            )
        )
    ),
)
print(lol.render())
