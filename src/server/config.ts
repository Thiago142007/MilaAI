import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export const PROJECT_ROOT = path.resolve(__dirname, "../../");

dotenv.config({ path: path.join(PROJECT_ROOT, ".env") });

export interface Config {
  host: string;
  port: number;
  llmBaseUrl: string;
  llmProtocol: "ollama" | "openai";
  llmApiKeys: string[];
  llmModel: string;
  llmVisionModel: string;
  llmTemperature: number;
  llmMaxTokens: number;
  llmTimeoutSeconds: number;
  autonomyMode: "manual" | "assisted" | "autonomous";
  agentMaxSteps: number;
  agentLoopThreshold: number;
  emergencyHotkey: string;
  workspaceRoot: string;
  dataPath: string;
  openRouterApiKey: string;
  ttsEngine: string;
  ttsVoice: string;
  ttsSpeed: number;
  ttsVolume: number;
  ttsDevice: string;
}

const rawKeys = process.env.NOVA_LLM_API_KEY || "";
const parsedKeys = rawKeys
  .replace(/\n/g, ",")
  .replace(/;/g, ",")
  .split(",")
  .map((k) => k.trim())
  .filter((k) => k.length > 0);

export const config: Config = {
  host: process.env.NOVA_HOST || "127.0.0.1",
  port: parseInt(process.env.NOVA_PORT || "8765", 10),
  llmBaseUrl: (process.env.NOVA_LLM_BASE_URL || "https://ollama.com").replace(/\/$/, ""),
  llmProtocol: (process.env.NOVA_LLM_PROTOCOL === "openai" ? "openai" : "ollama") as "ollama" | "openai",
  llmApiKeys: parsedKeys,
  llmModel: process.env.NOVA_LLM_MODEL || "minimax-m3:cloud",
  llmVisionModel: process.env.NOVA_LLM_VISION_MODEL || process.env.NOVA_LLM_MODEL || "minimax-m3:cloud",
  llmTemperature: parseFloat(process.env.NOVA_LLM_TEMPERATURE || "0.2"),
  llmMaxTokens: parseInt(process.env.NOVA_LLM_MAX_TOKENS || "4096", 10),
  llmTimeoutSeconds: parseInt(process.env.NOVA_LLM_TIMEOUT_SECONDS || "300", 10),
  autonomyMode: (process.env.NOVA_AUTONOMY_MODE as "manual" | "assisted" | "autonomous") || "assisted",
  agentMaxSteps: parseInt(process.env.NOVA_AGENT_MAX_STEPS || "25", 10),
  agentLoopThreshold: parseInt(process.env.NOVA_AGENT_LOOP_DETECTION_THRESHOLD || "3", 10),
  emergencyHotkey: process.env.NOVA_EMERGENCY_HOTKEY || "ctrl+alt+shift+x",
  workspaceRoot: process.env.NOVA_WORKSPACE_ROOT || PROJECT_ROOT,
  dataPath: path.join(PROJECT_ROOT, "data"),
  openRouterApiKey: process.env.OPENROUTER_API_KEY || "",
  ttsEngine: "Kokoro-82M",
  ttsVoice: process.env.TTS_VOICE || "pf_dora",
  ttsSpeed: parseFloat(process.env.TTS_SPEED || "1.0"),
  ttsVolume: parseFloat(process.env.TTS_VOLUME || "1.0"),
  ttsDevice: process.env.TTS_DEVICE || "auto",
};

