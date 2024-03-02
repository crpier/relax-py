let socket = new WebSocket("ws://127.0.0.1:8000/ws");
addSocketListeners(socket);
console.log("connected to ws server");

function updateData() {
  console.log("sent components data");
  const components = Array.from(document.querySelectorAll("[data-component]"));
  const componentsMap = components.reduce((map, el) => {
    let newMap = {};
    newMap[el.dataset.component] = el.dataset.values;
    map[el.id] = newMap;
    return map;
  }, {});
  socket.send(JSON.stringify(componentsMap));
}

/** @param {WebSocket} socket **/
function addSocketListeners(socket) {
  socket.addEventListener("open", (ev) => {
    updateData();
  });

  socket.addEventListener("message", (ev) => {
    console.log("new event");
    const event = JSON.parse(ev.data);
    if (event.event_type === "update_views") {
      let newElems = event.data;
      for (const [id, replacer] of Object.entries(newElems)) {
        let replaced = document.getElementById(id);
        Idiomorph.morph(replaced, replacer);
      }
    }
  });

  socket.addEventListener("close", (event) => {
    console.log("socket closed");
    socket = new WebSocket("ws://127.0.0.1:8000/ws");
    console.log("re-connected to ws server");
    addSocketListeners(socket);
  });

  socket.addEventListener("error", (event) => {
    console.log("socket errored");
  });
}

htmx.on("htmx:afterSettle", function(_) {
  updateData();
});
