import fs from "fs";
import path from "path";
import screenshot from "screenshot-desktop";
import { Config } from "../config.js";
import { LLMClient } from "../llm/llmClient.js";

export class ScreenPerception {
  private config: Config;
  private llm: LLMClient;
  private latestPath: string;

  constructor(config: Config, llm: LLMClient) {
    this.config = config;
    this.llm = llm;
    this.latestPath = path.join(config.dataPath, "latest_screen.jpg");
    if (!fs.existsSync(config.dataPath)) {
      fs.mkdirSync(config.dataPath, { recursive: true });
    }
  }

  async captureScreen(): Promise<{ imageBase64: string; width: number; height: number; savedTo: string }> {
    try {
      const imgBuffer = await screenshot({ format: "png" });
      fs.writeFileSync(this.latestPath, imgBuffer);

      return {
        imageBase64: imgBuffer.toString("base64"),
        width: 1920,
        height: 1080,
        savedTo: this.latestPath,
      };
    } catch (err: any) {
      console.warn("[Screen] Native capture fallback:", err.message);
      // Fallback empty frame if locked/session-0
      const fallbackBuffer = Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "base64"
      );
      fs.writeFileSync(this.latestPath, fallbackBuffer);
      return {
        imageBase64: fallbackBuffer.toString("base64"),
        width: 1920,
        height: 1080,
        savedTo: this.latestPath,
      };
    }
  }

  async describeScreen(question: string): Promise<string> {
    const screenData = await this.captureScreen();
    const messages: any[] = [
      {
        role: "system",
        content:
          "You are NOVA's visual perception engine analyzing a Windows desktop screenshot. " +
          "Describe exactly what is visible: open windows, applications, buttons, input fields, error dialogues, and text. " +
          "Answer factually in the same language as the question.",
      },
      {
        role: "user",
        content: [
          { type: "text", text: question },
          {
            type: "image_url",
            image_url: { url: `data:image/png;base64,${screenData.imageBase64}` },
          },
        ],
      },
    ];

    const res = await this.llm.chat(messages, undefined, this.config.llmVisionModel);
    return res.content || "Sem resposta da análise de visão.";
  }

  async findElement(description: string): Promise<{ found: boolean; x?: number; y?: number; confidence?: number }> {
    const screenData = await this.captureScreen();
    const prompt =
      `Locate the UI element: "${description}" on this Windows screen. ` +
      `Respond ONLY with a JSON object in this format: ` +
      `{"found": true|false, "x": pixel_x_coordinate, "y": pixel_y_coordinate, "confidence": 0.0_to_1.0}.`;

    const messages: any[] = [
      { role: "system", content: "You are a precise computer vision UI locator." },
      {
        role: "user",
        content: [
          { type: "text", text: prompt },
          {
            type: "image_url",
            image_url: { url: `data:image/png;base64,${screenData.imageBase64}` },
          },
        ],
      },
    ];

    const res = await this.llm.chat(messages, undefined, this.config.llmVisionModel);
    try {
      const cleaned = (res.content || "{}").replace(/```json/g, "").replace(/```/g, "").trim();
      return JSON.parse(cleaned);
    } catch {
      return { found: false };
    }
  }
}
