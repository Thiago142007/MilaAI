import { api } from "../api.js";
import { el, esc } from "../ui.js";

export function render(root) {
  root.innerHTML = "";
  root.append(el("div", { class: "page-title" }, "Tools"));

  async function refresh() {
    try {
      const tools = await api.get("/api/tools");
      const rows = tools.map((t) =>
        `<tr>
          <td><strong>${esc(t.name)}</strong></td>
          <td>${esc(t.category)}</td>
          <td>${esc(t.risk)}</td>
          <td>${esc((t.permissions || []).join(", "))}</td>
          <td class="muted">${esc(t.description)}</td>
        </tr>`
      );
      root.append(el("div", {
        html: `<table class="data">
          <thead><tr><th>Tool</th><th>Categoria</th><th>Risco</th><th>Permissões</th><th>Descrição</th></tr></thead>
          <tbody>${rows.join("")}</tbody>
        </table>`
      }));
    } catch (e) {}
  }
  refresh();
}
