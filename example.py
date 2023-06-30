from main import InputType, div, li, a, img, ul, input

button = div(
    klass="text-left text-4xl lg:text-base", attrs={"aria-label": "Close"}
).insert(
    ul(klass="list-disc list-inside").insert(
        li(klass="flex flex-col text-sm", id="btn-1").insert(
            a(
                klass="text-blue-500 mr-2 font-bold text-3xl lg:text-base",
                href="google.com",
            ).text("Button 1")
        ),
    ),
    input(name="test", type=InputType.text, value="test", id="test", label_text="test"),
    img(
        klass="w-full",
        src="https://crpier.github.io/assets/memecry_screenshot-66f594b1.png",
        alt="an image",
    ),
)

print(button.render())
