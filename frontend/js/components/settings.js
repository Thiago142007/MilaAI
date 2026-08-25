import { api } from "../api.js";
import { el, esc } from "../ui.js";

export function render(root) {
  root.innerHTML = "";
  root.append(el("div", { class: "page-title" }, "Settings"));

  async function refresh() {
    const s = await api.get("/api/settings");
    root.append(el("div", {
      html: `
      <div class="card">
        <strong>LLM</strong>
        <div class="muted mt">Endpoint: ${esc(s.llm_base_url)} · protocolo: ${esc(s.llm_protocol)}</div>
        <div class="muted">Modelo: ${esc(s.llm_model)} · Visão: ${esc(s.vision_model)}</div>
        <div class="muted">Chaves de API configuradas: ${s.api_keys_configured}</div>
      </div>
      <div class="card">
        <strong>Agente</strong>
        <div class="muted mt">Modo padrão: ${esc(s.autonomy_mode)} · Máx. passos: ${s.agent_max_steps}</div>
        <div class="muted">Workspace: ${esc(s.workspace_root)}</div>
        <div class="muted">Hotkey de emergência: ${esc(s.emergency_hotkey)}</div>
      </div>
      <div class="card">
        <strong>Como alterar</strong>
        <div class="muted mt">Edite o arquivo <code>.env</code> na raiz do projeto (copie de <code>.env.example</code>) e reinicie a NOVA.</div>
      </div>`
    }));
  }
  refresh();
}
