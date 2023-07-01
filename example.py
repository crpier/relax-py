from main import InputType, div, li, a, img, ul, input

button = div(
    classes=["text-left", "text-4xl", "lg:text-base"], attrs={"aria-label": "Close"}
).insert(
    ul(classes=["list-disc", "list-inside"]).insert(
        li(classes=["flex", "flex-col", "text-sm"], id="btn-1").insert(
            a(
                classes=[
                    "text-blue-500",
                    "mr-2",
                    "font-bold",
                    "text-3xl",
                    "lg:text-base",
                ],
                href="google.com",
            ).text("Button 1")
        ),
    ),
    input(name="test", type=InputType.text, value="test", id="test", label_text="test"),
    img(
        classes=["w-full"],
        src="https://crpier.github.io/assets/memecry_screenshot-66f594b1.png",
        alt="an image",
    ),
)

print(button.render())
