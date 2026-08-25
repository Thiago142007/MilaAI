import { Config } from "../config.js";
import { ChatMessage, LLMClient } from "../llm/llmClient.js";
import { MemoryManager } from "../memory/memoryManager.js";
import { ScreenPerception } from "../perception/screenCapture.js";
import { ToolContext, ToolRegistry } from "../tools/toolRegistry.js";

export interface AgentEventCallback {
  (event: string, payload: any): void;
}

export class TaskManager {
  private tasks: Map<string, { id: string; description: string; status: string; progress: number; result?: string; error?: string }> =
    new Map();

  create(description: string): string {
    const id = `task_${Date.now()}_${Math.random().toString(36).slice(2, 5)}`;
    this.tasks.set(id, {
      id,
      description,
      status: "executing",
      progress: 0.1,
    });
    return id;
  }

  update(id: string, update: Partial<{ status: string; progress: number; result: string; error: string }>) {
    const task = this.tasks.get(id);
    if (task) {
      Object.assign(task, update);
    }
  }

  get(id: string) {
    return this.tasks.get(id);
  }

  list() {
    return Array.from(this.tasks.values()).reverse();
  }
}

export class NovaAgent {
  private config: Config;
  private llm: LLMClient;
  private registry: ToolRegistry;
  private memory: MemoryManager;
  private screen: ScreenPerception;
  private taskManager: TaskManager;
  public stopEvent = { isStopped: false };

  constructor(
    config: Config,
    llm: LLMClient,
    registry: ToolRegistry,
    memory: MemoryManager,
    screen: ScreenPerception,
    taskManager: TaskManager
  ) {
    this.config = config;
    this.llm = llm;
    this.registry = registry;
    this.memory = memory;
    this.screen = screen;
    this.taskManager = taskManager;
  }

  async run(
    userText: string,
    conversationId: string,
    onEvent?: AgentEventCallback
  ): Promise<{ reply: string; taskId: string }> {
    const taskId = this.taskManager.create(userText);
    const maxSteps = this.config.agentMaxSteps;
    const actionCounter = new Map<string, number>();

    this.memory.addMessage(conversationId, "user", userText);
    onEvent?.("agent_state", { state: "thinking", taskId });
    onEvent?.("task_update", this.taskManager.get(taskId));

    let soulPrompt = "";
    try {
      const fs = await import("fs");
      const path = await import("path");
      const soulPath = path.join(this.config.workspaceRoot, "soul.md");
      if (fs.existsSync(soulPath)) {
        soulPrompt = "\n\n[SOUL & PERSONALITY DIRECTIVES (soul.md)]:\n" + fs.readFileSync(soulPath, "utf-8");
      }
    } catch {}

    const messages: ChatMessage[] = [
      {
        role: "system",
        content:
          `You are Mila, an intelligent autonomous multimodal AI assistant and 3D VTuber companion for Windows. ` +
          `You are female, friendly, expressive, highly capable, and empathetic. ` +
          `You can see the screen, control mouse & keyboard, manage files, execute terminal commands, search the web, and manage connected devices. ` +
          `Operating loop: OBSERVE -> UNDERSTAND -> PLAN -> EXECUTE -> VALIDATE -> FINISH. ` +
          `Always answer in Portuguese (pt-BR) with a natural, feminine and friendly tone. ` +
          `Workspace root: ${this.config.workspaceRoot}. Autonomy mode: ${this.config.autonomyMode.toUpperCase()}. ` +
          `When the goal is achieved, output your final natural answer to the user without calling more tools.` +
          soulPrompt,
      },
    ];

    // Append relevant conversation history and memories
    const history = this.memory.getMessages(conversationId).slice(-10);
    for (const h of history) {
      messages.push({ role: h.role as any, content: h.content });
    }

    const relevantMemories = this.memory.recall(userText, 3);
    if (relevantMemories.length > 0) {
      const memoryText = relevantMemories.map((m) => `- ${m.content}`).join("\n");
      messages.push({
        role: "system",
        content: `Relevant memories from previous interactions:\n${memoryText}`,
      });
    }

    const toolSchemas = this.registry.getOpenAISchemas();
    const toolCtx: ToolContext = {
      config: this.config,
      screen: this.screen,
      memory: this.memory,
      stopEvent: this.stopEvent,
    };

    for (let step = 1; step <= maxSteps; step++) {
      if (this.stopEvent.isStopped) {
        this.taskManager.update(taskId, { status: "failed", error: "Emergency stopped" });
        onEvent?.("task_update", this.taskManager.get(taskId));
        return { reply: "Parada de emergência acionada: interrompi a execução.", taskId };
      }

      this.taskManager.update(taskId, { progress: Math.min(0.95, step / maxSteps) });
      onEvent?.("task_update", this.taskManager.get(taskId));

      let assistantRes: any;
      try {
        assistantRes = await this.llm.chat(messages, toolSchemas);
      } catch (err: any) {
        console.error("[Agent] LLM error:", err.message);
        this.taskManager.update(taskId, { status: "failed", error: err.message });
        return { reply: `Erro ao consultar modelo de IA: ${err.message}`, taskId };
      }

      const toolCalls = assistantRes.tool_calls || [];
      if (toolCalls.length === 0) {
        const finalReply = assistantRes.content || "(Sem resposta do modelo)";
        this.memory.addMessage(conversationId, "assistant", finalReply);
        this.taskManager.update(taskId, { status: "completed", progress: 1.0, result: finalReply });
        onEvent?.("task_update", this.taskManager.get(taskId));
        onEvent?.("agent_state", { state: "idle", taskId });
        return { reply: finalReply, taskId };
      }

      messages.push({
        role: "assistant",
        content: assistantRes.content || null,
        tool_calls: toolCalls,
      });

      for (const tc of toolCalls) {
        const name = tc.function?.name;
        let args: any = {};
        try {
          args = JSON.parse(tc.function?.arguments || "{}");
        } catch {
          args = {};
        }

        const callKey = `${name}:${JSON.stringify(args)}`;
        const count = (actionCounter.get(callKey) || 0) + 1;
        actionCounter.set(callKey, count);

        onEvent?.("tool_call", { name, args, step, taskId });

        // Loop detection
        if (count >= this.config.agentLoopThreshold + 2) {
          this.taskManager.update(taskId, { status: "failed", error: "Loop de repetição detectado" });
          return {
            reply: `Detectei que estava repetindo a ferramenta '${name}' sem progresso. Interrompi a tarefa para evitar loops.`,
            taskId,
          };
        }

        const tool = this.registry.get(name);
        let result: any = { success: false, error: `Ferramenta '${name}' não encontrada` };

        if (tool) {
          try {
            result = await tool.handler(args, toolCtx);
          } catch (err: any) {
            result = { success: false, error: `Erro de execução: ${err.message}` };
          }
        }

        onEvent?.("tool_result", { name, ok: result.success, taskId });

        messages.push({
          role: "tool",
          tool_call_id: tc.id,
          content: JSON.stringify(result).slice(0, 4000),
        });
      }
    }

    this.taskManager.update(taskId, { status: "failed", error: "Max steps reached" });
    return { reply: `Atingi o limite de ${maxSteps} passos sem concluir totalmente.`, taskId };
  }
}
