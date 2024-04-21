# relax-py

Features:
- reload templates on startup if a websocket connection is available

To document:

- url callables from url_of need to be called with keyword arguments
- all route functions need to have the request as first param
- component functions can only have keyword-only params
- maybe a changelog thingie?
- that the html module doesn't do runtime checking of argument types
- default values not allowed in component functions params that are used for generating key
- that the hmr scripts need to be included in the page root

Todos:

- do something like `hx_request(url_func, kwargs, hx_trigger, ..)`
- reload scripts with HMR:
  - inline scripts
  - scripts from /static dir
- when signatures of templates are changed, reload the entire app
