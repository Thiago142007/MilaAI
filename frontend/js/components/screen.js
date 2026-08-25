import { api } from "../api.js";
import { el, toast } from "../ui.js";

export function render(root) {
  root.innerHTML = "";
  root.append(el("div", { class: "page-title" }, "Screen"));

  let live = false;
  let timer = null;

  const img = el("img", { id: "screen-img", alt: "screen preview" });

  async function refresh() {
    img.src = `/api/screenshot?t=${Date.now()}`;
  }

  async function captureNow() {
    try {
      const r = await api.post("/api/screenshot/capture");
      if (!r.success) throw new Error(r.error);
      await refresh();
      toast("Screenshot capturado.");
    } catch (e) {
      toast(`Falha ao capturar: ${e.message}`, true);
    }
  }

  const liveBtn = el("button", { class: "btn-sm", onclick: toggleLive }, "Live: OFF");
  function toggleLive() {
    live = !live;
    liveBtn.textContent = `Live: ${live ? "ON" : "OFF"}`;
    if (live) {
      refresh();
      timer = setInterval(refresh, 1200);
    } else {
      clearInterval(timer);
    }
  }

  root.append(
    el("div", { class: "screen-controls" },
      el("button", { class: "btn-sm", onclick: captureNow }, "Capturar agora"),
      liveBtn,
      el("span", { class: "muted" }, "Atualiza a cada 1.2s no modo live.")
    ),
    img
  );
}
