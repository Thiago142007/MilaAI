import { api } from "../api.js";
import { el, toast } from "../ui.js";

export function render(root) {
  root.innerHTML = "";
  root.append(el("div", { class: "page-title" }, "📡 Device Manager"));

  const container = el("div", { class: "device-container" });
  const grid = el("div", { class: "device-grid" });

  const actionsRow = el(
    "div",
    { class: "screen-controls" },
    el("button", { class: "btn-sm", onclick: loadDevices }, "🔄 Atualizar"),
    el("button", { class: "btn-sm", onclick: promptAddESP32 }, "➕ Adicionar ESP32"),
    el("button", { class: "btn-sm", onclick: promptAddMobile }, "📱 Parear Celular")
  );

  container.append(actionsRow, grid);
  root.append(container);

  async function loadDevices() {
    grid.innerHTML = "";
    try {
      const devices = await api.get("/api/devices");
      if (!devices || devices.length === 0) {
        grid.append(el("div", { class: "muted" }, "Nenhum dispositivo encontrado."));
        return;
      }
      for (const d of devices) {
        grid.append(createDeviceCard(d));
      }
    } catch (e) {
      toast(`Falha ao listar dispositivos: ${e.message}`, true);
    }
  }

  function createDeviceCard(dev) {
    const card = el("div", { class: "device-card" });
    const isConn = dev.connected;

    const badge = el(
      "span",
      { class: `badge ${isConn ? "completed" : "failed"}` },
      isConn ? "CONNECTED" : "DISCONNECTED"
    );

    const header = el(
      "div",
      { class: "device-header" },
      el("span", { class: "device-name" }, dev.name || dev.id),
      badge
    );

    const body = el("div", { class: "device-body" });
    body.append(el("div", { class: "muted" }, `Tipo: ${dev.type}`));
    if (dev.os) body.append(el("div", { class: "muted" }, `OS: ${dev.os}`));
    if (dev.cpu_percent !== undefined)
      body.append(el("div", { class: "muted" }, `CPU: ${dev.cpu_percent}% · RAM: ${dev.ram_percent}%`));
    if (dev.endpoint)
      body.append(el("div", { class: "muted" }, `Endpoint: ${dev.endpoint}`));

    const btnRow = el("div", { class: "mt" });
    if (dev.id !== "local-pc") {
      const connBtn = el(
        "button",
        {
          class: "btn-sm",
          onclick: async () => {
            if (isConn) {
              await api.post(`/api/devices/${dev.id}/disconnect`, {});
              toast(`Dispositivo ${dev.name} desconectado.`);
            } else {
              const ep = prompt("Informe o host/porta (ex: 192.168.1.50 ou COM3):", dev.endpoint || "");
              if (ep) {
                await api.post(`/api/devices/${dev.id}/connect`, { endpoint: ep });
                toast(`Dispositivo ${dev.name} conectado.`);
              }
            }
            loadDevices();
          },
        },
        isConn ? "Desconectar" : "Conectar"
      );

      const sendBtn = el(
        "button",
        {
          class: "btn-sm",
          onclick: async () => {
            const cmd = prompt("Comando ou JSON para enviar ao dispositivo:");
            if (cmd) {
              let payload = cmd;
              try { payload = JSON.parse(cmd); } catch {}
              await api.post(`/api/devices/${dev.id}/send`, { payload });
              toast("Comando enviado com sucesso.");
            }
          },
        },
        "Enviar comando"
      );
      btnRow.append(connBtn, sendBtn);
    }

    card.append(header, body, btnRow);
    return card;
  }

  async function promptAddESP32() {
    const id = prompt("ID do ESP32 (ex: esp32-sensor-1):");
    if (!id) return;
    const ep = prompt("Endpoint/IP ou porta serial (ex: 192.168.4.1 ou COM3):");
    try {
      await api.post(`/api/devices/${id}/connect`, { endpoint: ep || "" });
      toast(`ESP32 ${id} cadastrado com sucesso!`);
      loadDevices();
    } catch (e) {
      toast(`Erro ao registrar ESP32: ${e.message}`, true);
    }
  }

  async function promptAddMobile() {
    const id = prompt("ID do Celular (ex: mobile-mateus):");
    if (!id) return;
    try {
      await api.post(`/api/devices/${id}/connect`, { pairing_code: "1234" });
      toast(`Celular ${id} pareado!`);
      loadDevices();
    } catch (e) {
      toast(`Erro ao parear celular: ${e.message}`, true);
    }
  }

  loadDevices();
}
