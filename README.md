# relax-py

Features:

- when signatures of templates are changed, reload the entire app
- reload templates on startup if a websocket connection is available

To document:

- url callables from url_of need to be called with keyword arguments
- all route functions need to have the request as first param
- component functions can only have keyword-only params
- maybe a changelog thingie?
- that the html module doesn't do runtime checking of argument types

Todos:

- do something like `hx_request(url_func, kwargs, hx_trigger, ..)`
