import { api } from "./api.js";
import { on, send, isConnected } from "./ws.js";
import { el, toast } from "./ui.js";
import * as chat from "./components/chat.js";
import * as tasks from "./components/tasks.js";
import * as screen from "./components/screen.js";
import * as memory from "./components/memory.js";
import * as toolsPage from "./components/tools.js";
import * as devices from "./components/devices.js";
import * as permissions from "./components/permissions.js";
import * as logs from "./components/logs.js";
import * as settings from "./components/settings.js";
import { initConfirmations } from "./components/confirm.js";

const view = document.getElementById("view");
const pages = { chat, tasks, screen, memory, tools: toolsPage, devices, permissions, logs, settings };
let currentPage = "chat";

function navigate(name) {
  currentPage = name;
  document.querySelectorAll("#sidebar button").forEach((b) =>
    b.classList.toggle("active", b.dataset.page === name)
  );
  if (pages[name] && pages[name].render) {
    pages[name].render(view);
  }
}

document.querySelectorAll("#sidebar button").forEach((b) => {
  b.addEventListener("click", () => navigate(b.dataset.page));
});

const modeSelect = document.getElementById("mode-select");
modeSelect.addEventListener("change", async () => {
  send({ type: "set_mode", mode: modeSelect.value });
});

on("mode_changed", (p) => {
  modeSelect.value = p.mode;
  toast(`Modo de autonomia: ${p.mode.toUpperCase()}`);
});

const stopBtn = document.getElementById("stop-btn");
const resetBtn = document.getElementById("reset-btn");
const voiceCancelBtn = document.getElementById("voice-cancel-btn");

if (voiceCancelBtn) {
  voiceCancelBtn.addEventListener("click", () => {
    chat.stopSpeaking();
    send({ type: "voice_stop" });
  });
}

stopBtn.addEventListener("click", () => {
  chat.stopSpeaking();
  send({ type: "emergency_stop" });
});
resetBtn.addEventListener("click", () => send({ type: "reset_emergency" }));

function setEmergency(active) {
  const pill = document.getElementById("global-status");
  if (active) {
    stopBtn.hidden = true;
    resetBtn.hidden = false;
    pill.className = "status-pill stopped";
    pill.innerHTML = '<span class="dot"></span> EMERGENCY STOP';
    toast("EMERGÊNCIA: todas as ações foram interrompidas.", true);
  } else {
    stopBtn.hidden = false;
    resetBtn.hidden = true;
    if (pill.classList.contains("stopped")) setStatusPill(true);
  }
}
on("emergency", (p) => setEmergency(p.active));

window.__wsSend = send;

window.__updateTaskBar = function (task) {
  const label = document.getElementById("task-label");
  const bar = document.getElementById("task-progress");
  const pct = document.getElementById("task-percent");
  if (!task) return;
  label.textContent = `Task ${task.id}: ${task.description.slice(0, 60)}`;
  const v = Math.round((task.progress || 0) * 100);
  bar.value = v;
  pct.textContent = `${v}% · ${task.status}`;
};

on("task_update", (t) => {
  const ACTIVE = ["queued", "planning", "executing", "waiting_confirmation"];
  if (!ACTIVE.includes(t.status)) {
    const bar = document.getElementById("task-progress");
    bar.value = t.status === "completed" ? 100 : bar.value;
    document.getElementById("task-percent").textContent = t.status;
  }
});

function setStatusPill(ok) {
  const pill = document.getElementById("global-status");
  pill.className = `status-pill ${ok ? "online" : "offline"}`;
  pill.innerHTML = `<span class="dot"></span> ${ok ? "ONLINE" : "OFFLINE"}`;
}

on("chat_accepted", (p) => {});
on("chat_final", (p) => {
  window.__chatTyping && window.__chatTyping(false);
  window.__chatAddMsg && window.__chatAddMsg("nova", p.content || "(vazio)");
});
on("chat_error", (p) => {
  window.__chatTyping && window.__chatTyping(false);
  window.__chatAddMsg && window.__chatAddMsg("nova", `Erro: ${p.error}`);
});
on("agent_state", (p) => {
  if (p.state !== "thinking") window.__chatTyping && window.__chatTyping(false);
});
on("tool_call", (p) => {
  window.__chatTyping && window.__chatTyping(false);
  const args = Object.entries(p.args || {})
    .map(([k, v]) => `${k}=${String(v).slice(0, 40)}`)
    .join(", ");
  window.__chatAddChip && window.__chatAddChip(`▸ ${p.name}(${args})`);
});
on("tool_result", (p) => {
  window.__chatAddChip &&
    window.__chatAddChip(`▪ ${p.name} → ${p.ok ? "ok" : "falhou"}`);
});
on("confirmation_request", (c) => {
  window.__chatAddChip && window.__chatAddChip(`⏸ aguardando confirmação: ${c.title}`);
});
on("ws_close", () => setStatusPill(false));
on("ws_open", () => {});

initConfirmations();

const CHECKS = [
  ["ai", "Checking AI..."],
  ["tools", "Checking tools..."],
  ["permissions", "Checking permissions..."],
  ["microphone", "Checking microphone..."],
  ["screen", "Checking screen access..."],
  ["browser", "Checking browser..."],
  ["memory", "Checking memory..."],
];

async function boot() {
  chat.render(view);
  const list = document.getElementById("boot-checks");

  let data = null;
  // Retry fetching status up to 8 times (4s max) while server initializes
  for (let i = 0; i < 8; i++) {
    try {
      data = await api.get("/api/status");
      if (data && data.checks) break;
    } catch (e) {
      await new Promise((r) => setTimeout(r, 450));
    }
  }

  for (const [key, label] of CHECKS) {
    const check = data && data.checks ? data.checks[key] : null;
    const isOk = check ? check.ok !== false : true;
    const detail = check && check.detail ? ` (${check.detail})` : "";
    const li = el("li", { class: isOk ? "ok" : "fail" }, `${label}${detail}`);
    list.append(li);
    await new Promise((r) => setTimeout(r, 120));
  }

  await new Promise((r) => setTimeout(r, 300));
  const overlay = document.getElementById("boot-overlay");
  if (overlay) overlay.remove();
  setStatusPill(true);

  setInterval(async () => {
    try {
      const s = await api.get("/api/status");
      setStatusPill(!s.emergency_stopped);
      if (s.emergency_stopped) setEmergency(true);
      else setEmergency(false);
    } catch (e) {}
  }, 5000);
}

boot().catch((err) => {
  console.error("boot failed, dismissing overlay", err);
  const overlay = document.getElementById("boot-overlay");
  if (overlay) overlay.remove();
  setStatusPill(true);
});
