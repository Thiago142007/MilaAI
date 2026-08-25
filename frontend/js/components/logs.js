import { api } from "../api.js";
import { el, fmtTime, esc } from "../ui.js";

export function render(root) {
  root.innerHTML = "";
  root.append(el("div", { class: "page-title" }, "Logs & Auditoria"));

  const tabs = el("div", { style: "display:flex;gap:8px;margin-bottom:12px;" });
  const content = el("div");

  const btnRuntime = el("button", { class: "btn-sm active", onclick: () => show("runtime") }, "Runtime");
  const btnAudit = el("button", { class: "btn-sm", onclick: () => show("audit") }, "Auditoria (DB)");
  tabs.append(btnRuntime, btnAudit);
  root.append(tabs, content);

  let mode = "runtime";
  let timer = null;

  async function refresh() {
    try {
      if (mode === "runtime") {
        const logs = await api.get("/api/logs?limit=200");
        content.innerHTML = logs
          .map(
            (l) =>
              `<div class="log-line"><span class="muted">${fmtTime(l.ts)}</span> ` +
              `<span class="lv-${l.level}">${l.level}</span> ` +
              `<span class="muted">${esc(l.logger)}</span> :: ${esc(l.message)}</div>`
          )
          .join("");
      } else {
        const rows = await api.get("/api/audit?limit=150");
        content.innerHTML =
          `<table class="data"><thead><tr><th>Quando</th><th>Categoria</th><th>Ação</th><th>Detalhe</th></tr></thead><tbody>` +
          rows
            .map(
              (r) =>
                `<tr><td>${fmtTime(r.ts)}</td><td>${esc(r.category)}</td>` +
                `<td>${esc(r.action)}</td><td class="muted">${esc(JSON.stringify(r.detail)).slice(0, 220)}</td></tr>`
            )
            .join("") +
          "</tbody></table>";
      }
    } catch (e) {}
  }

  function show(m) {
    mode = m;
    btnRuntime.classList.toggle("active", m === "runtime");
    btnAudit.classList.toggle("active", m === "audit");
    clearInterval(timer);
    refresh();
    timer = setInterval(refresh, 3000);
  }

  show("runtime");
}
