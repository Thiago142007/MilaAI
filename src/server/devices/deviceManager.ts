import os from "os";

export interface DeviceInfo {
  id: string;
  name: string;
  type: "local_pc" | "esp32" | "mobile" | "iot";
  connected: boolean;
  endpoint?: string;
  telemetry?: any;
  lastSeen: number;
}

export class DeviceManager {
  private devices: Map<string, DeviceInfo> = new Map();

  constructor() {
    this.registerLocalPC();
  }

  private registerLocalPC() {
    this.devices.set("local-pc", {
      id: "local-pc",
      name: `Local PC (${os.hostname()})`,
      type: "local_pc",
      connected: true,
      lastSeen: Date.now(),
      telemetry: {
        os: `${os.type()} ${os.release()}`,
        arch: os.arch(),
        cpus: os.cpus().length,
        totalMemGB: (os.totalmem() / 1024 / 1024 / 1024).toFixed(1),
        freeMemGB: (os.freemem() / 1024 / 1024 / 1024).toFixed(1),
      },
    });
  }

  async listDevices(): Promise<DeviceInfo[]> {
    this.registerLocalPC(); // update telemetry
    return Array.from(this.devices.values());
  }

  getDevice(id: string): DeviceInfo | undefined {
    return this.devices.get(id);
  }

  async connect(id: string, endpoint: string, name?: string): Promise<{ success: boolean; message: string }> {
    const isESP = id.toLowerCase().includes("esp");
    const dev: DeviceInfo = {
      id,
      name: name || (isESP ? `ESP32 (${endpoint})` : id),
      type: isESP ? "esp32" : "iot",
      connected: true,
      endpoint,
      lastSeen: Date.now(),
      telemetry: { status: "online", pingMs: 12 },
    };
    this.devices.set(id, dev);
    return { success: true, message: `Dispositivo ${id} conectado em ${endpoint}` };
  }

  async disconnect(id: string): Promise<boolean> {
    const dev = this.devices.get(id);
    if (!dev || dev.id === "local-pc") return false;
    dev.connected = false;
    return true;
  }

  async send(id: string, payload: any): Promise<{ success: boolean; data?: any; error?: string }> {
    const dev = this.devices.get(id);
    if (!dev || !dev.connected) {
      return { success: false, error: "Dispositivo offline ou não encontrado" };
    }
    dev.lastSeen = Date.now();
    dev.telemetry = { ...dev.telemetry, lastCommand: payload };
    return { success: true, data: { delivered: true, payload, timestamp: Date.now() } };
  }
}

export const deviceManager = new DeviceManager();
