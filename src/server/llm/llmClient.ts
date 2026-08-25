import { Config } from "../config.js";

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content?: string | any[];
  tool_calls?: any[];
  tool_call_id?: string;
}

export interface ToolDefinition {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: any;
  };
}

export class LLMClient {
  private config: Config;
  private currentKeyIndex = 0;

  constructor(config: Config) {
    this.config = config;
  }

  private getAuthHeader(): Record<string, string> {
    if (this.config.llmApiKeys.length === 0) return {};
    const key = this.config.llmApiKeys[this.currentKeyIndex % this.config.llmApiKeys.length];
    return { Authorization: `Bearer ${key}` };
  }

  private rotateKey() {
    if (this.config.llmApiKeys.length > 1) {
      this.currentKeyIndex = (this.currentKeyIndex + 1) % this.config.llmApiKeys.length;
      console.log(`[LLM] Rotated to API key index ${this.currentKeyIndex}`);
    }
  }

  async health(): Promise<{ ok: boolean; detail: string }> {
    const url =
      this.config.llmProtocol === "ollama"
        ? `${this.config.llmBaseUrl}/api/tags`
        : `${this.config.llmBaseUrl}/models`;

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3500);

      const resp = await fetch(url, {
        headers: this.getAuthHeader(),
        signal: controller.signal,
      });
      clearTimeout(timeout);

      const keysNote = this.config.llmApiKeys.length ? `, ${this.config.llmApiKeys.length} chave(s)` : "";
      if (resp.ok) {
        return { ok: true, detail: `${this.config.llmModel} via ${this.config.llmProtocol}${keysNote}` };
      }
      if (resp.status === 401 || resp.status === 403) {
        return { ok: false, detail: `Auth rejected (${resp.status}) - verifique NOVA_LLM_API_KEY${keysNote}` };
      }
      return { ok: true, detail: `${this.config.llmModel} configured (${resp.status})` };
    } catch (err: any) {
      return { ok: true, detail: `${this.config.llmModel} (${err.name || "offline"})` };
    }
  }

  async chat(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    overrideModel?: string
  ): Promise<{ content?: string; tool_calls?: any[] }> {
    const model = overrideModel || this.config.llmModel;
    const attempts = Math.max(this.config.llmApiKeys.length, 1);

    for (let attempt = 0; attempt < attempts; attempt++) {
      try {
        if (this.config.llmProtocol === "ollama") {
          return await this.chatOllama(messages, tools, model);
        } else {
          return await this.chatOpenAI(messages, tools, model);
        }
      } catch (err: any) {
        console.warn(`[LLM] Attempt ${attempt + 1} failed:`, err.message);
        if (attempt < attempts - 1) {
          this.rotateKey();
          await new Promise((r) => setTimeout(r, 800));
          continue;
        }
        throw err;
      }
    }
    throw new Error("All LLM attempts failed");
  }

  private async chatOllama(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    model?: string
  ): Promise<{ content?: string; tool_calls?: any[] }> {
    const ollamaMsgs = messages.map((m) => {
      if (Array.isArray(m.content)) {
        const textParts = m.content.filter((p: any) => p.type === "text").map((p: any) => p.text).join("\n");
        const imageParts = m.content
          .filter((p: any) => p.type === "image_url")
          .map((p: any) => {
            const url = p.image_url?.url || "";
            return url.includes("base64,") ? url.split("base64,")[1] : url;
          });
        return {
          role: m.role,
          content: textParts,
          ...(imageParts.length > 0 ? { images: imageParts } : {}),
        };
      }
      return {
        role: m.role,
        content: m.content || "",
      };
    });

    const payload: any = {
      model: model || this.config.llmModel,
      messages: ollamaMsgs,
      stream: false,
      options: {
        temperature: this.config.llmTemperature,
        num_predict: this.config.llmMaxTokens,
      },
    };

    if (tools && tools.length > 0) {
      payload.tools = tools.map((t) => ({
        type: "function",
        function: {
          name: t.function.name,
          description: t.function.description,
          parameters: t.function.parameters,
        },
      }));
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.config.llmTimeoutSeconds * 1000);

    const resp = await fetch(`${this.config.llmBaseUrl}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...this.getAuthHeader(),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Ollama API error ${resp.status}: ${errText.slice(0, 200)}`);
    }

    const data: any = await resp.json();
    const msg = data.message || {};

    let tool_calls: any[] | undefined = undefined;
    if (msg.tool_calls && Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0) {
      tool_calls = msg.tool_calls.map((tc: any, idx: number) => ({
        id: `call_${Date.now()}_${idx}`,
        type: "function",
        function: {
          name: tc.function?.name,
          arguments:
            typeof tc.function?.arguments === "string"
              ? tc.function.arguments
              : JSON.stringify(tc.function?.arguments || {}),
        },
      }));
    }

    return {
      content: msg.content || undefined,
      tool_calls,
    };
  }

  private async chatOpenAI(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
    model?: string
  ): Promise<{ content?: string; tool_calls?: any[] }> {
    const payload: any = {
      model: model || this.config.llmModel,
      messages,
      temperature: this.config.llmTemperature,
      max_tokens: this.config.llmMaxTokens,
    };

    if (tools && tools.length > 0) {
      payload.tools = tools;
      payload.tool_choice = "auto";
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.config.llmTimeoutSeconds * 1000);

    const resp = await fetch(`${this.config.llmBaseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...this.getAuthHeader(),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`OpenAI API error ${resp.status}: ${errText.slice(0, 200)}`);
    }

    const data: any = await resp.json();
    const choice = data.choices?.[0]?.message || {};

    return {
      content: choice.content || undefined,
      tool_calls: choice.tool_calls || undefined,
    };
  }
}
