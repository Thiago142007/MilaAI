import cors from "cors";
import express from "express";
import http from "http";
import path from "path";
import { fileURLToPath } from "url";
import { WebSocket, WebSocketServer } from "ws";
import { NovaAgent, TaskManager } from "./agent/agentLoop.js";
import { config, PROJECT_ROOT } from "./config.js";
import { deviceManager } from "./devices/deviceManager.js";
import { LLMClient } from "./llm/llmClient.js";
import { MemoryManager } from "./memory/memoryManager.js";
import { ScreenPerception } from "./perception/screenCapture.js";
import { buildDefaultRegistry } from "./tools/toolRegistry.js";
import { voiceManager } from "./voice/voiceManager.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: "/ws" });

app.use(cors());
app.use(express.json({ limit: "50mb" }));
app.use((err: any, _req: express.Request, res: express.Response, next: express.NextFunction) => {
  if (err instanceof SyntaxError && "status" in err && (err as any).status === 400 && "body" in err) {
    return res.status(400).json({ error: "Invalid JSON format" });
  }
  next();
});

// Initialize Subsystems
const llm = new LLMClient(config);
const screen = new ScreenPerception(config, llm);
const memory = new MemoryManager(config);
const registry = buildDefaultRegistry();
const taskManager = new TaskManager();
const agent = new NovaAgent(config, llm, registry, memory, screen, taskManager);

// Serve Static Frontend Assets & Three.js client
const clientDir = path.join(PROJECT_ROOT, "src", "client");
app.use(express.static(clientDir));

// WebSocket Event Hub
const clients = new Set<WebSocket>();

function broadcast(type: string, payload: any) {
  const msg = JSON.stringify({ type, payload });
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(msg);
    }
  }
}

wss.on("connection", (ws) => {
  clients.add(ws);
  console.log(`[WS] Client connected (total: ${clients.size})`);

  ws.on("message", async (raw) => {
    try {
      const data = JSON.parse(raw.toString());
      const type = data.type;

      if (type === "chat_message") {
        const text = (data.text || "").trim();
        if (!text) return;
        const cid = memory.ensureConversation(data.conversation_id);

        ws.send(JSON.stringify({ type: "chat_accepted", payload: { conversation_id: cid } }));

        // Broadcast to 3D Avatar that NOVA started thinking
        broadcast("vrm_expression", { expression: "thinking" });

        const result = await agent.run(text, cid, (event, payload) => {
          broadcast(event, payload);
          // If a tool is called, trigger speech/action on the 3D model
          if (event === "tool_call") {
            broadcast("vrm_expression", { expression: "neutral", motion: "nod" });
          }
        });

        let audioBase64: string | null = null;
        if (result.reply) {
          try {
            audioBase64 = await voiceManager.generateSpeechAudio(result.reply, config);
          } catch {}
        }

        broadcast("chat_final", {
          conversation_id: cid,
          task_id: result.taskId,
          content: result.reply,
          audioBase64,
        });

        // Trigger speaking lip-sync on 3D Avatar
        broadcast("vrm_expression", { expression: "happy", speakText: result.reply });
      } else if (type === "emergency_stop") {
        agent.stopEvent.isStopped = true;
        voiceManager.stopSpeaking();
        broadcast("emergency", { active: true });
        broadcast("vrm_expression", { expression: "surprised" });
      } else if (type === "reset_emergency") {
        agent.stopEvent.isStopped = false;
        broadcast("emergency", { active: false });
        broadcast("vrm_expression", { expression: "neutral" });
      } else if (type === "voice_stop") {
        voiceManager.stopSpeaking();
      } else if (type === "ping") {
        ws.send(JSON.stringify({ type: "pong" }));
      }
    } catch (err: any) {
      console.error("[WS] Message error:", err.message);
    }
  });

  ws.on("close", () => {
    clients.delete(ws);
  });
});

// ── REST API Endpoints ───────────────────────────────────────────
app.get("/api/status", async (_req, res) => {
  const aiHealth = await llm.health();
  const voiceSt = voiceManager.status();
  const toolsCount = registry.getAll().length;

  res.json({
    version: "2.0.0-3D-VTUBER",
    uptime_s: Math.round(process.uptime()),
    emergency_stopped: agent.stopEvent.isStopped,
    autonomy_mode: config.autonomyMode,
    checks: {
      ai: aiHealth,
      tools: { ok: toolsCount > 0, detail: `${toolsCount} tools loaded` },
      permissions: { ok: true, detail: `mode=${config.autonomyMode}` },
      screen: { ok: true, detail: "ready" },
      browser: { ok: true, detail: "ready" },
      memory: { ok: true, detail: "data/memory.json" },
      microphone: { ok: voiceSt.ok, detail: voiceSt.detail },
    },
  });
});

app.post("/api/chat", async (req, res) => {
  const { text, conversation_id } = req.body;
  if (!text) return res.status(400).json({ error: "text is required" });
  const cid = memory.ensureConversation(conversation_id);
  const result = await agent.run(text, cid, (event, payload) => broadcast(event, payload));
  let audioBase64: string | null = null;
  if (result.reply) {
    try {
      audioBase64 = await voiceManager.generateSpeechAudio(result.reply, config);
    } catch {}
  }
  res.json({ conversation_id: cid, task_id: result.taskId, reply: result.reply, audioBase64 });
});

app.get("/api/tasks", (_req, res) => {
  res.json(taskManager.list());
});

app.get("/api/screenshot", async (_req, res) => {
  const cap = await screen.captureScreen();
  const imgBuffer = Buffer.from(cap.imageBase64, "base64");
  res.setHeader("Content-Type", "image/png");
  res.send(imgBuffer);
});

app.post("/api/screenshot/capture", async (_req, res) => {
  const cap = await screen.captureScreen();
  res.json({ success: true, width: cap.width, height: cap.height });
});

app.get("/api/tools", (_req, res) => {
  res.json(
    registry.getAll().map((t) => ({
      name: t.name,
      description: t.description,
      category: t.category,
      risk: t.risk,
      parameters: t.parameters,
    }))
  );
});

app.get("/api/devices", async (_req, res) => {
  res.json(await deviceManager.listDevices());
});

app.post("/api/devices/:id/connect", async (req, res) => {
  const result = await deviceManager.connect(req.params.id, req.body.endpoint);
  res.json(result);
});

app.post("/api/devices/:id/send", async (req, res) => {
  const result = await deviceManager.send(req.params.id, req.body.payload);
  res.json(result);
});

app.get("/api/memory", (req, res) => {
  res.json(memory.listMemories(req.query.kind as string));
});

app.post("/api/memory", (req, res) => {
  const { content, kind } = req.body;
  if (!content) return res.status(400).json({ error: "content is required" });
  const id = memory.remember(content, kind);
  res.json({ id });
});

app.delete("/api/memory/:id", (req, res) => {
  const ok = memory.deleteMemory(req.params.id);
  res.json({ deleted: ok });
});

app.post("/api/emergency-stop", (_req, res) => {
  agent.stopEvent.isStopped = true;
  voiceManager.stopSpeaking();
  broadcast("emergency", { active: true });
  res.json({ stopped: true });
});

app.post("/api/reset-emergency", (_req, res) => {
  agent.stopEvent.isStopped = false;
  broadcast("emergency", { active: false });
  res.json({ reset: true });
});

app.get("/api/voice/status", (_req, res) => {
  res.json(voiceManager.status());
});

app.get("/api/voice/voices", (_req, res) => {
  res.json({ voices: voiceManager.getVoices() });
});

app.post("/api/voice/tts", async (req, res) => {
  const { text, voice, speed } = req.body;
  if (!text) {
    res.status(400).json({ ok: false, error: "text is required" });
    return;
  }
  const audioBase64 = await voiceManager.generateSpeechAudio(text, config, voice, speed);
  res.json({ ok: true, audioBase64: audioBase64 || "" });
});

app.post("/api/voice/stop", (_req, res) => {
  voiceManager.stopSpeaking();
  res.json({ ok: true, stopped: true });
});

app.post("/api/voice/config", (req, res) => {
  const { voice, speed, volume, device } = req.body;
  if (voice) config.ttsVoice = voice;
  if (speed !== undefined) config.ttsSpeed = Number(speed);
  if (volume !== undefined) config.ttsVolume = Number(volume);
  if (device) config.ttsDevice = device;
  res.json({ ok: true, status: voiceManager.status(), config });
});


// Fallback to index.html for SPA
app.get("*", (_req, res) => {
  res.sendFile(path.join(clientDir, "index.html"));
});

server.listen(config.port, config.host, () => {
  console.log(`\n======================================================`);
  console.log(`  🌸 MILA 3D VTUBER MULTIMODAL AI RUNNING`);
  console.log(`  🔗 Interface: http://${config.host}:${config.port}`);
  console.log(`  ⚡ Tools: ${registry.getAll().length} loaded`);
  console.log(`  🤖 Mode: ${config.autonomyMode.toUpperCase()}`);
  console.log(`======================================================\n`);
});
