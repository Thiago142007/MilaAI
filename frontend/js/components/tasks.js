import { api } from "../api.js";
import { el, fmtTime } from "../ui.js";

const ACTIVE = new Set(["queued", "planning", "executing", "waiting_confirmation"]);

export function render(root) {
  root.innerHTML = "";
  root.append(el("div", { class: "page-title" }, "Tasks"));
  const list = el("div");
  root.append(list);

  async function refresh() {
    try {
      const tasks = await api.get("/api/tasks?limit=50");
      list.innerHTML = "";
      if (!tasks.length) {
        list.append(el("div", { class: "muted" }, "Nenhuma tarefa ainda."));
      }
      for (const t of tasks) {
        list.append(taskCard(t));
      }
      const active = tasks.find((t) => ACTIVE.has(t.status));
      window.__updateTaskBar(active || null);
    } catch (e) {}
  }

  function taskCard(t) {
    const pct = Math.round((t.progress || 0) * 100);
    const actions = el("div");
    if (ACTIVE.has(t.status)) {
      actions.append(
        el("button", { class: "btn-sm", onclick: () => act(`${t.id}/pause`) }, "Pausar"),
        el("button", { class: "btn-sm", onclick: () => act(`${t.id}/cancel`) }, "Cancelar")
      );
    } else if (t.status === "waiting_confirmation") {
      actions.append(
        el("button", { class: "btn-sm", onclick: () => act(`${t.id}/resume`) }, "Retomar"),
        el("button", { class: "btn-sm", onclick: () => act(`${t.id}/cancel`) }, "Cancelar")
      );
    }
    return el(
      "div",
      { class: "card" },
      el("div", { style: "display:flex;justify-content:space-between;gap:10px;align-items:center;" },
        el("strong", {}, t.description.slice(0, 90)),
        el("span", { class: `badge ${t.status}` }, t.status)
      ),
      el("div", { class: "task-progress" },
        el("div", { style: `width:${pct}%` })
      ),
      el("div", { class: "muted", style: "font-size:12px;" },
        `${t.id} · ${pct}% · ${fmtTime(t.created_at)}${t.error ? " · erro: " + t.error.slice(0, 120) : ""}`
      ),
      actions
    );
  }

  async function act(path) {
    try {
      await api.post(`/api/tasks/${path}`);
      refresh();
    } catch (e) {}
  }

  refresh();
  const timer = setInterval(refresh, 2500);
  const obs = new MutationObserver(() => {
    if (!document.body.contains(root)) {
      clearInterval(timer);
      obs.disconnect();
    }
  });
  obs.observe(document.getElementById("view"), { childList: true });
}
