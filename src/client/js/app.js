import { VRMEngine } from "../avatar/vrmEngine.js";

// Initialize Fullscreen 3D Model
let vrmAvatar = null;
const canvasContainer = document.getElementById("vrm-canvas-container");
if (canvasContainer) {
  vrmAvatar = new VRMEngine(canvasContainer);
}

// UI Elements
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");
const ttsBtn = document.getElementById("tts-btn");

let ttsEnabled = true;

ttsBtn?.addEventListener("click", () => {
  ttsEnabled = !ttsEnabled;
  ttsBtn.classList.toggle("active", ttsEnabled);
  ttsBtn.textContent = ttsEnabled ? "🔊" : "🔇";
});

// WebSocket Connection
const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const wsUrl = `${protocol}//${window.location.host}/ws`;
let ws = null;

function connectWS() {
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("[MILA] Conectado ao servidor");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleWSEvent(data.type, data.payload);
    } catch (e) {
      console.error("[WS] Erro:", e);
    }
  };

  ws.onclose = () => {
    setTimeout(connectWS, 2000);
  };
}
connectWS();

function handleWSEvent(type, payload) {
  if (type === "chat_final") {
    const text = payload.content || "";
    if (ttsEnabled && text) {
      speakMessage(text, payload.audioBase64);
    }
  } else if (type === "tool_call") {
    vrmAvatar?.setExpression("neutral");
  } else if (type === "vrm_expression") {
    if (payload.expression && vrmAvatar) {
      vrmAvatar.setExpression(payload.expression);
    }
  } else if (type === "agent_state") {
    if (payload.state === "thinking") {
      vrmAvatar?.setExpression("thinking");
    }
  }
}

// Send Message
function sendChat() {
  const text = chatInput.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

  chatInput.value = "";
  vrmAvatar?.setExpression("thinking");

  ws.send(
    JSON.stringify({
      type: "chat_message",
      text,
      conversation_id: getConversationId(),
    })
  );
}

sendBtn?.addEventListener("click", sendChat);
chatInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});

// Web Speech Audio Recognition
let recognition = null;
let isListening = false;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "pt-BR";
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.onstart = () => {
    isListening = true;
    micBtn?.classList.add("listening");
  };

  recognition.onresult = (e) => {
    let transcript = "";
    for (let i = e.resultIndex; i < e.results.length; ++i) {
      transcript += e.results[i][0].transcript;
    }
    chatInput.value = transcript;
  };

  recognition.onend = () => {
    isListening = false;
    micBtn?.classList.remove("listening");
    if (chatInput.value.trim()) {
      sendChat();
    }
  };
}

micBtn?.addEventListener("click", () => {
  if (!recognition) {
    alert("Reconhecimento de voz não disponível no navegador.");
    return;
  }
  if (isListening) {
    recognition.stop();
  } else {
    chatInput.value = "";
    recognition.start();
  }
});

// Single Voice Audio Manager (Prevents Duplicate Audio)
let currentPlayingAudio = null;

function stopAllVoice() {
  if (currentPlayingAudio) {
    try {
      currentPlayingAudio.pause();
      currentPlayingAudio.currentTime = 0;
    } catch {}
    currentPlayingAudio = null;
  }
  vrmAvatar?.stopSpeaking();

  // Send stop to server
  try {
    fetch("/api/voice/stop", { method: "POST" }).catch(() => {});
  } catch {}
}

// Voice Synthesis (Kokoro-82M 100% Local) & Lip-Sync
function speakMessage(text, audioBase64) {
  const clean = text.replace(/[*_#`\[\]]/g, " ").slice(0, 800).trim();
  stopAllVoice();

  if (!clean) return;

  vrmAvatar?.startSpeaking(clean);
  vrmAvatar?.setExpression("happy");

  if (audioBase64) {
    try {
      const src = audioBase64.startsWith("data:") ? audioBase64 : `data:audio/wav;base64,${audioBase64}`;
      const audio = new Audio(src);
      currentPlayingAudio = audio;

      audio.onended = () => {
        currentPlayingAudio = null;
        vrmAvatar?.stopSpeaking();
        vrmAvatar?.setExpression("neutral");
      };

      audio.onerror = (e) => {
        console.warn("[Voice] Audio playback error:", e);
        currentPlayingAudio = null;
        fallbackSpeech(clean);
      };

      audio.play().catch((err) => {
        console.warn("[Voice] Autoplay blocked or interrupted:", err);
        currentPlayingAudio = null;
        fallbackSpeech(clean);
      });
      return;
    } catch (e) {
      console.warn("[Voice] Audio init error:", e);
    }
  }

  // Fallback to Web Speech API if audioBase64 was not provided or failed
  fallbackSpeech(clean);
}

function fallbackSpeech(text) {
  if (!window.speechSynthesis) {
    setTimeout(() => {
      vrmAvatar?.stopSpeaking();
      vrmAvatar?.setExpression("neutral");
    }, Math.min(text.length * 60, 4000));
    return;
  }

  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "pt-BR";
    utterance.rate = 1.0;
    utterance.onend = () => {
      vrmAvatar?.stopSpeaking();
      vrmAvatar?.setExpression("neutral");
    };
    utterance.onerror = () => {
      vrmAvatar?.stopSpeaking();
      vrmAvatar?.setExpression("neutral");
    };
    window.speechSynthesis.speak(utterance);
  } catch {
    vrmAvatar?.stopSpeaking();
    vrmAvatar?.setExpression("neutral");
  }
}

// Voice Settings Modal Controls
const settingsBtn = document.getElementById("settings-btn");
const settingsModal = document.getElementById("voice-settings-modal");
const settingsCloseBtn = document.getElementById("voice-settings-close");
const voiceSelect = document.getElementById("voice-select");
const voiceSpeed = document.getElementById("voice-speed");
const voiceSpeedVal = document.getElementById("voice-speed-val");
const voiceVolume = document.getElementById("voice-volume");
const voiceVolumeVal = document.getElementById("voice-volume-val");
const voiceDevice = document.getElementById("voice-device");
const voiceTestBtn = document.getElementById("voice-test-btn");
const voiceStopBtn = document.getElementById("voice-stop-btn");

settingsBtn?.addEventListener("click", () => {
  settingsModal?.classList.toggle("hidden");
});

settingsCloseBtn?.addEventListener("click", () => {
  settingsModal?.classList.add("hidden");
});

voiceSpeed?.addEventListener("input", () => {
  if (voiceSpeedVal) voiceSpeedVal.textContent = `${Number(voiceSpeed.value).toFixed(2)}x`;
  saveVoiceConfig();
});

voiceVolume?.addEventListener("input", () => {
  if (voiceVolumeVal) voiceVolumeVal.textContent = `${Math.round(Number(voiceVolume.value) * 100)}%`;
  saveVoiceConfig();
});

voiceSelect?.addEventListener("change", saveVoiceConfig);
voiceDevice?.addEventListener("change", saveVoiceConfig);

function saveVoiceConfig() {
  const payload = {
    voice: voiceSelect?.value || "pf_dora",
    speed: parseFloat(voiceSpeed?.value || "1.0"),
    volume: parseFloat(voiceVolume?.value || "1.0"),
    device: voiceDevice?.value || "auto",
  };

  fetch("/api/voice/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).catch(() => {});
}

// Load Available Voices from Server
async function loadVoicesList() {
  try {
    const res = await fetch("/api/voice/status");
    if (res.ok) {
      const data = await res.json();
      if (data.available_voices && voiceSelect) {
        voiceSelect.innerHTML = "";
        data.available_voices.forEach((v) => {
          const opt = document.createElement("option");
          opt.value = v;
          if (v === "pf_dora") opt.textContent = `${v} (Feminina · PT-BR)`;
          else if (v === "pm_alex") opt.textContent = `${v} (Masculina · PT-BR)`;
          else if (v.startsWith("af_")) opt.textContent = `${v} (Feminina · EN-US)`;
          else if (v.startsWith("am_")) opt.textContent = `${v} (Masculina · EN-US)`;
          else if (v.startsWith("bf_")) opt.textContent = `${v} (Feminina · EN-GB)`;
          else opt.textContent = v;
          if (v === (data.default_voice || "pf_dora")) opt.selected = true;
          voiceSelect.appendChild(opt);
        });
      }
    }
  } catch {}
}
loadVoicesList();

// Test Voice Button
voiceTestBtn?.addEventListener("click", async () => {
  const text = "Olá! Eu sou a Mila. Como posso ajudar você?";
  const voice = voiceSelect?.value || "pf_dora";
  const speed = parseFloat(voiceSpeed?.value || "1.0");

  voiceTestBtn.textContent = "⏳ Gerando...";
  try {
    const res = await fetch("/api/voice/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice, speed }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.audioBase64) {
        speakMessage(text, data.audioBase64);
      }
    }
  } catch (e) {
    console.warn("Voice test failed:", e);
  } finally {
    voiceTestBtn.textContent = "▶ Testar Voz";
  }
});

// Stop Voice Button
voiceStopBtn?.addEventListener("click", () => {
  stopAllVoice();
});

function getConversationId() {
  let id = localStorage.getItem("mila_cid");
  if (!id) {
    id = "conv_" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("mila_cid", id);
  }
  return id;
}

