import { api } from "../api.js";
import { el, toast } from "../ui.js";

let recognition = null;
let isRecording = false;

export function render(root) {
  root.innerHTML = "";

  const logBox = el("div", { id: "chat-log" });
  const input = el("input", {
    id: "chat-input",
    placeholder: "Message NOVA... (Enter para enviar, ou clique no microfone)",
    autocomplete: "off",
  });
  const micBtn = el("button", {
    id: "mic-btn",
    title: "Ativar microfone (Push to talk / Web Speech)",
  }, "🎙️");
  const sendBtn = el("button", { id: "send-btn", onclick: send }, "Enviar");

  async function send() {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMsg("user", text);
    showTyping(true);
    window.__wsSend({ type: "chat_message", text, conversation_id: getConvId() });
  }

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") send();
  });

  // Setup Web Speech Recognition
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "pt-BR";

    recognition.onstart = () => {
      isRecording = true;
      micBtn.classList.add("listening");
      toast("Ouvindo... Fale agora");
    };

    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        transcript += event.results[i][0].transcript;
      }
      input.value = transcript;
    };

    recognition.onerror = (event) => {
      logError("Erro no microfone: " + event.error);
      stopRecording();
    };

    recognition.onend = () => {
      stopRecording();
      if (input.value.trim()) {
        send();
      }
    };
  }

  function toggleRecording() {
    if (!recognition) {
      toast("Reconhecimento de voz no navegador não suportado neste ambiente.", true);
      return;
    }
    if (isRecording) {
      recognition.stop();
    } else {
      input.value = "";
      try {
        recognition.start();
      } catch (err) {
        console.warn("speech start error", err);
      }
    }
  }

  function stopRecording() {
    isRecording = false;
    micBtn.classList.remove("listening");
  }

  micBtn.onclick = toggleRecording;

  const layout = el(
    "div",
    { class: "chat-layout" },
    logBox,
    el("div", { class: "chat-input-row" }, micBtn, input, sendBtn)
  );
  root.append(layout);

  let typingEl = null;
  function showTyping(show) {
    if (typingEl) typingEl.remove();
    typingEl = null;
    if (show) {
      typingEl = el("div", { class: "msg typing" }, "NOVA está pensando...");
      logBox.append(typingEl);
      logBox.scrollTop = logBox.scrollHeight;
    }
  }

  function addMsg(role, content) {
    logBox.append(el("div", { class: `msg ${role === "user" ? "user" : "nova"}` }, content));
    logBox.scrollTop = logBox.scrollHeight;
    if (role === "nova" && shouldSpeak()) {
      speakText(content);
    }
  }

  function addChip(text) {
    logBox.append(el("div", { class: "msg tool-chip" }, text));
    logBox.scrollTop = logBox.scrollHeight;
  }

  window.__chatAddMsg = addMsg;
  window.__chatAddChip = addChip;
  window.__chatTyping = showTyping;

  loadHistory(logBox);
}

function shouldSpeak() {
  const toggle = document.getElementById("tts-toggle");
  return toggle ? toggle.checked : true;
}

export function speakText(text) {
  if (!text || text.startsWith("Erro:")) return;
  // Clean text from Markdown artifacts for speech
  const clean = text.replace(/[*_#`\[\]]/g, "").slice(0, 500);

  const stopBtn = document.getElementById("voice-cancel-btn");
  if (stopBtn) stopBtn.style.display = "inline-block";

  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = "pt-BR";
    utterance.rate = 1.05;
    utterance.onend = () => {
      if (stopBtn) stopBtn.style.display = "none";
    };
    utterance.onerror = () => {
      if (stopBtn) stopBtn.style.display = "none";
    };
    window.speechSynthesis.speak(utterance);
  } else {
    // Call server TTS endpoint fallback
    api.post("/api/voice/tts", { text: clean, wait: false }).catch(() => {});
  }
}

export function stopSpeaking() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  api.post("/api/voice/stop", {}).catch(() => {});
  const stopBtn = document.getElementById("voice-cancel-btn");
  if (stopBtn) stopBtn.style.display = "none";
}

function getConvId() {
  let id = localStorage.getItem("nova_conv_id");
  if (!id) {
    id = crypto.randomUUID().replace(/-/g, "").slice(0, 12);
    localStorage.setItem("nova_conv_id", id);
  }
  return id;
}
window.__getConvId = getConvId;

async function loadHistory(logBox) {
  try {
    const msgs = await api.get(`/api/conversations/${getConvId()}/messages`);
    for (const m of msgs.slice(-30)) {
      if (m.role === "user") {
        logBox.append(el("div", { class: "msg user" }, m.content));
      } else if (m.role === "assistant") {
        let content = m.content;
        try {
          const env = JSON.parse(m.content);
          if (typeof env.content === "string") content = env.content;
        } catch {}
        if (content && !content.includes('"tool_calls"')) {
          logBox.append(el("div", { class: "msg nova" }, content));
        }
      }
    }
    logBox.scrollTop = logBox.scrollHeight;
  } catch (e) {}
}
