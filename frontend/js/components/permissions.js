import { api } from "../api.js";
import { el, toast, esc } from "../ui.js";

export function render(root) {
  root.innerHTML = "";
  root.append(el("div", { class: "page-title" }, "Permissions"));

  const grid = el("div", { class: "perm-grid" });

  async function refresh() {
    try {
      const data = await api.get("/api/permissions");
      document.getElementById("mode-select").value = data.mode;
      grid.innerHTML = "";
      for (const c of data.categories) {
        grid.append(
          el("div", { class: "perm-item" },
            el("div", {},
              el("strong", {}, c.category),
              el("div", { class: "muted", style: "font-size:11px;" },
                c.auto_allowed ? "auto permitido no modo atual" : "requer confirmação")
            ),
            el("button", { class: "btn-sm", onclick: () => grant(c.category) }, "Grant sessão")
          )
        );
      }
    } catch (e) {}
  }

  async function grant(category) {
    try {
      await api.post("/api/permissions/grant", { category, scope: "session" });
      toast(`Permissão ${category} concedida para esta sessão.`);
    } catch (e) {
      toast(e.message, true);
    }
  }

  root.append(
    el("p", { class: "muted" },
      "Modo atual define o que roda sem perguntar. FILE_DELETE sempre pede confirmação. Grants de sessão duram até reiniciar."),
    el("div", { class: "mt" }),
    grid,
    el("div", { class: "mt" },
      el("button", { class: "btn-sm", onclick: resetAll }, "Limpar grants da sessão"))
  );

  async function resetAll() {
    await api.post("/api/permissions/reset");
    toast("Grants da sessão limpos.");
    refresh();
  }
  refresh();
}
