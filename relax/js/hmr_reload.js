let socket = new WebSocket("ws://127.0.0.1:8000/ws");
addSocketListeners(socket);
console.log("connected to ws server");

/** @param {WebSocket} socket **/
function addSocketListeners(socket) {
  socket.addEventListener("open", (ev) => {
  });

  socket.addEventListener("message", (ev) => {
    console.log("new event");
    const event = JSON.parse(ev.data);
    if (event.event_type === "update_views") {
      let newElems = event.data;
      for (const [id, replacer] of Object.entries(newElems)) {
        let replaced = document.getElementById(id);
        if (!replaced) {
          console.error(`Element with id ${id} not found`);
          continue;
        }
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
