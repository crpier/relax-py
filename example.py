from main import div, li, a, label

button = div(
    klass="text-left text-4xl lg:text-base", attrs={"aria-label": "Close"}
).insert(
    li(klass="flex flex-col text-sm", id="btn-1").insert(
        a(
            klass="text-blue-500 mr-2 font-bold text-3xl lg:text-base",
            href="google.com",
        ).text("Button 1")
    ),
    label(klass="text-blue-500 mr-2 font-bold text-3xl lg:text-base").text(
        "Press this button to...do something?"
    ),
)

print(button.render())
