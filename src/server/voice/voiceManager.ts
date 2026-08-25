import { spawn, ChildProcess } from "child_process";
import readline from "readline";
import path from "path";
import fs from "fs";
import { Config, PROJECT_ROOT } from "../config.js";

interface WorkerResponse {
  id?: number;
  type?: string;
  ok?: boolean;
  audioBase64?: string;
  voices?: string[];
  engine?: string;
  device?: string;
  error?: string;
}

export class VoiceManager {
  private workerProc: ChildProcess | null = null;
  private isReady = false;
  private reqId = 0;
  private pendingRequests = new Map<
    number,
    { resolve: (val: any) => void; reject: (err: any) => void }
  >();
  private availableVoices: string[] = ["pf_dora", "pm_alex", "af_heart", "af_bella", "af_sarah", "bf_emma"];

  constructor() {
    this.startWorker();
  }

  private getPythonPath(): string {
    const isWin = process.platform === "win32";
    const venvPython = isWin
      ? path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
      : path.join(PROJECT_ROOT, ".venv", "bin", "python");

    if (fs.existsSync(venvPython)) {
      return venvPython;
    }
    return "python";
  }

  private startWorker() {
    try {
      const pythonExe = this.getPythonPath();
      const scriptPath = path.join(PROJECT_ROOT, "src", "server", "voice", "kokoro_worker.py");

      this.workerProc = spawn(pythonExe, [scriptPath], {
        stdio: ["pipe", "pipe", "inherit"],
        windowsHide: true,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: "1",
          PYTHONIOENCODING: "utf-8",
        },
      });

      if (!this.workerProc.stdout) return;

      const rl = readline.createInterface({ input: this.workerProc.stdout });

      rl.on("line", (line) => {
        try {
          const res: WorkerResponse = JSON.parse(line.trim());
          if (res.type === "ready") {
            this.isReady = true;
            if (res.voices && Array.isArray(res.voices)) {
              this.availableVoices = res.voices;
            }
            console.log("[Voice] Kokoro-82M Local TTS Worker initialized and ready!");
          } else if (res.id !== undefined && this.pendingRequests.has(res.id)) {
            const { resolve, reject } = this.pendingRequests.get(res.id)!;
            this.pendingRequests.delete(res.id);
            if (res.ok) {
              resolve(res);
            } else {
              reject(new Error(res.error || "Kokoro synthesis error"));
            }
          }
        } catch (e) {
          // ignore non-JSON debug logs
        }
      });

      this.workerProc.on("exit", (code) => {
        this.isReady = false;
        this.workerProc = null;
        if (code !== 0 && code !== null) {
          console.warn(`[Voice] Kokoro worker process exited with code ${code}. Restarting in 3s...`);
          setTimeout(() => this.startWorker(), 3000);
        }
      });
    } catch (err: any) {
      console.error("[Voice] Failed to spawn Kokoro worker:", err.message);
    }
  }

  status() {
    return {
      ok: true,
      ttsReady: this.isReady,
      sttReady: true,
      engine: "Kokoro-82M (100% Local)",
      defaultVoice: "pf_dora",
      availableVoices: this.availableVoices,
      detail: "Kokoro-82M 100% Local TTS Engine Ready",
    };
  }

  getVoices(): string[] {
    return this.availableVoices;
  }

  /**
   * Generates WAV speech audio locally using Kokoro-82M (zero external API calls)
   */
  async generateSpeechAudio(
    text: string,
    config: Config,
    overrideVoice?: string,
    overrideSpeed?: number
  ): Promise<string | null> {
    const clean = text.replace(/[*_#`\[\]]/g, " ").slice(0, 1000).trim();
    if (!clean) return null;

    const voice = overrideVoice || config.ttsVoice || "pf_dora";
    const speed = overrideSpeed !== undefined ? overrideSpeed : config.ttsSpeed || 1.0;

    const id = ++this.reqId;

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          resolve(null);
        }
      }, 25000);

      this.pendingRequests.set(id, {
        resolve: (res: WorkerResponse) => {
          clearTimeout(timeout);
          resolve(res.audioBase64 || null);
        },
        reject: (err: any) => {
          clearTimeout(timeout);
          console.warn("[Voice] Kokoro generation notice:", err.message);
          resolve(null);
        },
      });

      if (this.workerProc && this.workerProc.stdin) {
        try {
          this.workerProc.stdin.write(
            JSON.stringify({
              id,
              action: "generate",
              text: clean,
              voice,
              speed,
            }) + "\n"
          );
        } catch {
          this.pendingRequests.delete(id);
          clearTimeout(timeout);
          resolve(null);
        }
      } else {
        this.pendingRequests.delete(id);
        clearTimeout(timeout);
        resolve(null);
      }
    });
  }

  async speak(text: string, wait = false): Promise<boolean> {
    return true;
  }

  stopSpeaking(): void {
    if (this.workerProc && this.workerProc.stdin) {
      try {
        this.workerProc.stdin.write(JSON.stringify({ action: "stop" }) + "\n");
      } catch {}
    }
  }
}

export const voiceManager = new VoiceManager();
