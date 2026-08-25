import { on, send } from "./ws.js";
import { el, toast } from "./ui.js";

export function initConfirmations() {
  on("confirmation_request", (c) => showConfirm(c));
}

function showConfirm(c) {
  if (document.getElementById(`confirm-${c.id}`)) return;

  const riskColor =
    c.risk === "dangerous" ? "var(--danger)" : c.risk === "warning" ? "var(--warn)" : "var(--accent)";

  const backdrop = el("div", { class: "modal-backdrop", id: `confirm-${c.id}` });
  const modal = el(
    "div",
    { class: "modal" },
    el("h3", {}, c.title),
    el("span", {
      class: "badge",
      style: `background:${riskColor}22;color:${riskColor};`,
    }, `risco: ${c.risk}`),
    el("pre", {}, c.detail),
    el("div", { class: "actions" },
      el("button", { class: "btn-deny", onclick: () => answer(c.id, "deny") }, "Cancelar"),
      el("button", { class: "btn-once", onclick: () => answer(c.id, "allow_once") }, "Permitir uma vez"),
      el("button", { class: "btn-task", onclick: () => answer(c.id, "allow_task") }, "Permitir para esta tarefa"),
    )
  );
  backdrop.append(modal);
  document.getElementById("confirm-root").append(backdrop);
  toast("NOVA precisa da sua aprovação.");
}

function answer(id, decision) {
  send({ type: "confirmation_response", id, decision });
  document.getElementById(`confirm-${id}`)?.remove();
}
