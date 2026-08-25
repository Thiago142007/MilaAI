import fs from "fs";
import path from "path";
import { Config } from "../config.js";

export interface MemoryItem {
  id: string;
  kind: "fact" | "user_pref" | "procedure" | "system";
  content: string;
  importance: number;
  createdAt: number;
  data?: any;
}

export class MemoryManager {
  private filePath: string;
  private memories: MemoryItem[] = [];
  private conversations: Map<string, Array<{ role: string; content: string; time: number }>> = new Map();

  constructor(config: Config) {
    this.filePath = path.join(config.dataPath, "memory.json");
    this.load();
  }

  private load() {
    try {
      if (fs.existsSync(this.filePath)) {
        const raw = fs.readFileSync(this.filePath, "utf-8");
        this.memories = JSON.parse(raw);
      }
    } catch {
      this.memories = [];
    }
  }

  private save() {
    try {
      fs.writeFileSync(this.filePath, JSON.stringify(this.memories, null, 2), "utf-8");
    } catch (err) {
      console.error("[Memory] Save error:", err);
    }
  }

  ensureConversation(cid?: string): string {
    const id = cid || `conv_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    if (!this.conversations.has(id)) {
      this.conversations.set(id, []);
    }
    return id;
  }

  addMessage(cid: string, role: string, content: string) {
    const list = this.conversations.get(cid) || [];
    list.push({ role, content, time: Date.now() });
    if (list.length > 50) list.shift();
    this.conversations.set(cid, list);
  }

  getMessages(cid: string): Array<{ role: string; content: string }> {
    return this.conversations.get(cid) || [];
  }

  remember(content: string, kind: "fact" | "user_pref" | "procedure" = "fact", importance = 0.7): string {
    const id = `mem_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const item: MemoryItem = {
      id,
      kind,
      content,
      importance,
      createdAt: Date.now(),
    };
    this.memories.push(item);
    this.save();
    return id;
  }

  recall(query: string, limit = 5): MemoryItem[] {
    const words = query.toLowerCase().split(/\s+/).filter((w) => w.length > 2);
    if (!words.length) return this.memories.slice(-limit);

    return this.memories
      .filter((m) => words.some((w) => m.content.toLowerCase().includes(w)))
      .sort((a, b) => b.importance - a.importance)
      .slice(0, limit);
  }

  saveProcedure(name: string, steps: string[], description = ""): string {
    const id = `proc_${Date.now()}`;
    const item: MemoryItem = {
      id,
      kind: "procedure",
      content: `[Procedimento: ${name}] ${description}`,
      importance: 0.9,
      createdAt: Date.now(),
      data: { name, steps, description },
    };
    this.memories.push(item);
    this.save();
    return id;
  }

  getProcedure(name: string): { name: string; steps: string[]; description: string } | null {
    const target = name.toLowerCase();
    const found = this.memories.find((m) => m.kind === "procedure" && m.data?.name?.toLowerCase().includes(target));
    return found?.data || null;
  }

  listMemories(kind?: string): MemoryItem[] {
    if (kind && kind !== "all") {
      return this.memories.filter((m) => m.kind === kind);
    }
    return [...this.memories].reverse();
  }

  deleteMemory(id: string): boolean {
    const initialLen = this.memories.length;
    this.memories = this.memories.filter((m) => m.id !== id);
    if (this.memories.length !== initialLen) {
      this.save();
      return true;
    }
    return false;
  }
}
