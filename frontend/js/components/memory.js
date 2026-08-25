import { api } from "../api.js";
import { el, toast, fmtTime } from "../ui.js";

export function render(root) {
  root.innerHTML = "";
  root.append(el("div", { class: "page-title" }, "🧠 Multimodal & Procedural Memory"));

  let activeTab = "all";

  const tabsRow = el(
    "div",
    { class: "screen-controls" },
    createTabBtn("all", "Tudo"),
    createTabBtn("fact", "Fatos"),
    createTabBtn("user_fact", "Preferências"),
    createTabBtn("procedure", "Procedimentos")
  );

  function createTabBtn(type, label) {
    const btn = el(
      "button",
      {
        class: `btn-sm ${activeTab === type ? "active" : ""}`,
        onclick: () => {
          activeTab = type;
          renderTabButtons();
          refresh();
        },
      },
      label
    );
    btn.dataset.tab = type;
    return btn;
  }

  function renderTabButtons() {
    tabsRow.querySelectorAll("button").forEach((b) => {
      b.style.borderColor = b.dataset.tab === activeTab ? "var(--accent)" : "var(--border)";
      b.style.color = b.dataset.tab === activeTab ? "var(--accent)" : "var(--muted)";
    });
  }

  const input = el("input", {
    id: "chat-input",
    placeholder: "Adicionar fato ou instrução à memória...",
    style: "flex:1",
  });
  const addBtn = el("button", { id: "send-btn", onclick: add }, "Salvar");
  const list = el("div");

  root.append(
    tabsRow,
    el("div", { style: "display:flex;gap:10px;margin-bottom:16px;" }, input, addBtn),
    list
  );
  renderTabButtons();

  async function add() {
    const content = input.value.trim();
    if (!content) return;
    try {
      await api.post("/api/memory", { content, kind: activeTab === "all" ? "fact" : activeTab });
      input.value = "";
      refresh();
      toast("Memória gravada!");
    } catch (e) {
      toast(e.message, true);
    }
  }

  async function refresh() {
    try {
      const url = activeTab === "all" ? "/api/memory" : `/api/memory?kind=${activeTab}`;
      const items = await api.get(url);
      list.innerHTML = "";
      if (!items.length) {
        list.append(el("div", { class: "muted" }, "Nenhuma memória registrada nesta categoria."));
        return;
      }
      for (const m of items) {
        let contentDisplay = m.content;
        if (m.kind === "procedure") {
          try {
            const parsed = JSON.parse(m.content);
            contentDisplay = `[PROCEDIMENTO: ${parsed.name}]\nPassos: ${(parsed.steps || []).join(" ➔ ")}`;
          } catch {}
        }

        list.append(
          el(
            "div",
            { class: "card", style: "display:flex;justify-content:space-between;gap:12px;" },
            el(
              "div",
              {},
              el("div", { style: "font-weight: 500;" }, contentDisplay.slice(0, 400)),
              el(
                "div",
                { class: "muted", style: "font-size:11px;margin-top:8px;" },
                `Categoria: ${m.kind} · Importância: ${m.importance} · ${fmtTime(m.created_at)}`
              )
            ),
            el("button", { class: "btn-sm", onclick: () => remove(m.id) }, "Excluir")
          )
        );
      }
    } catch (e) {
      toast(`Erro ao carregar memória: ${e.message}`, true);
    }
  }

  async function remove(id) {
    try {
      await api.del(`/api/memory/${id}`);
      refresh();
      toast("Memória excluída.");
    } catch (e) {}
  }

  refresh();
}
