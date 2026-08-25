const handlers = new Map();
let socket = null;
let backoff = 1000;
let connected = false;

export function on(type, fn) {
  if (!handlers.has(type)) handlers.set(type, []);
  handlers.get(type).push(fn);
}

export function send(obj) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(obj));
    return true;
  }
  return false;
}

export function isConnected() {
  return connected;
}

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${proto}://${location.host}/ws`);

  socket.onopen = () => {
    connected = true;
    backoff = 1000;
    dispatch("ws_open", {});
  };

  socket.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      dispatch(msg.type, msg.payload || {});
    } catch (e) {
      console.error("bad ws message", e);
    }
  };

  socket.onclose = () => {
    connected = false;
    dispatch("ws_close", {});
    setTimeout(connect, backoff);
    backoff = Math.min(backoff * 2, 15000);
  };

  socket.onerror = () => socket.close();
}

function dispatch(type, payload) {
  (handlers.get(type) || []).forEach((fn) => {
    try {
      fn(payload);
    } catch (e) {
      console.error(`handler for ${type} failed`, e);
    }
  });
}

connect();
