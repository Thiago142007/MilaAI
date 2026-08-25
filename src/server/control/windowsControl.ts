import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export class WindowsControl {
  /**
   * Move mouse cursor to screen (x, y)
   */
  async mouseMove(x: number, y: number): Promise<void> {
    const ps = `
      Add-Type -AssemblyName System.Windows.Forms
      [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(${Math.round(x)}, ${Math.round(y)})
    `;
    await this.runPowerShell(ps);
  }

  /**
   * Mouse click (left, right, middle)
   */
  async click(x: number, y: number, button: "left" | "right" | "middle" = "left", clicks: number = 1): Promise<void> {
    await this.mouseMove(x, y);
    const downFlag = button === "right" ? 0x08 : button === "middle" ? 0x20 : 0x02;
    const upFlag = button === "right" ? 0x10 : button === "middle" ? 0x40 : 0x04;

    const ps = `
      $code = @'
      using System;
      using System.Runtime.InteropServices;
      public class MouseClicker {
        [DllImport("user32.dll")]
        public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
      }
'@
      Add-Type -TypeDefinition $code
      for ($i=0; $i -lt ${clicks}; $i++) {
        [MouseClicker]::mouse_event(${downFlag}, 0, 0, 0, 0)
        Start-Sleep -Milliseconds 40
        [MouseClicker]::mouse_event(${upFlag}, 0, 0, 0, 0)
        Start-Sleep -Milliseconds 60
      }
    `;
    await this.runPowerShell(ps);
  }

  /**
   * Type text into active window
   */
  async keyboardType(text: string): Promise<void> {
    const escaped = text.replace(/[`$"{}]/g, "`$&");
    const ps = `
      Add-Type -AssemblyName System.Windows.Forms
      [System.Windows.Forms.SendKeys]::SendWait("${escaped}")
    `;
    await this.runPowerShell(ps);
  }

  /**
   * Press key (e.g. '{ENTER}', '{ESC}', '{TAB}')
   */
  async pressKey(key: string): Promise<void> {
    const cleanKey = key.startsWith("{") ? key : `{${key.toUpperCase()}}`;
    const ps = `
      Add-Type -AssemblyName System.Windows.Forms
      [System.Windows.Forms.SendKeys]::SendWait("${cleanKey}")
    `;
    await this.runPowerShell(ps);
  }

  /**
   * Press hotkey combination (e.g. Ctrl+Shift+Esc, Alt+F4)
   */
  async hotkey(keys: string[]): Promise<void> {
    const clean = keys.map((k) => k.toLowerCase().trim());
    let prefix = "";
    let mainKey = "";

    for (const k of clean) {
      if (k === "ctrl" || k === "control") prefix += "^";
      else if (k === "alt") prefix += "%";
      else if (k === "shift") prefix += "+";
      else mainKey = k.length === 1 ? k : `{${k.toUpperCase()}}`;
    }

    const sendStr = `${prefix}${mainKey}`;
    const ps = `
      Add-Type -AssemblyName System.Windows.Forms
      [System.Windows.Forms.SendKeys]::SendWait("${sendStr}")
    `;
    await this.runPowerShell(ps);
  }

  /**
   * List visible top-level windows
   */
  async listWindows(): Promise<Array<{ title: string; pid: number; process: string }>> {
    const ps = `
      Get-Process | Where-Object MainWindowTitle | Select-Object MainWindowTitle, Id, ProcessName | ConvertTo-Json
    `;
    try {
      const { stdout } = await this.runPowerShell(ps);
      const parsed = JSON.parse(stdout.trim() || "[]");
      const list = Array.isArray(parsed) ? parsed : [parsed];
      return list.map((w: any) => ({
        title: w.MainWindowTitle,
        pid: w.Id,
        process: w.ProcessName,
      }));
    } catch {
      return [];
    }
  }

  /**
   * Bring window containing title to foreground
   */
  async focusWindow(title: string): Promise<boolean> {
    const ps = `
      $code = @'
      using System;
      using System.Runtime.InteropServices;
      public class WinFocus {
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
      }
'@
      Add-Type -TypeDefinition $code
      $procs = Get-Process
      foreach ($p in $procs) {
        if ($p.MainWindowTitle -like "*${title}*") {
          [WinFocus]::ShowWindowAsync($p.MainWindowHandle, 9)
          [WinFocus]::SetForegroundWindow($p.MainWindowHandle)
          return $true
        }
      }
      return $false
    `;
    const { stdout } = await this.runPowerShell(ps);
    return stdout.includes("True");
  }

  /**
   * Close a window by process/title
   */
  async closeWindow(title: string): Promise<boolean> {
    const ps = `
      $procs = Get-Process
      foreach ($p in $procs) {
        if ($p.MainWindowTitle -like "*${title}*") {
          $p.CloseMainWindow()
          return $true
        }
      }
      return $false
    `;
    const { stdout } = await this.runPowerShell(ps);
    return stdout.includes("True");
  }

  private async runPowerShell(script: string): Promise<{ stdout: string; stderr: string }> {
    const encoded = Buffer.from(script, "utf16le").toString("base64");
    return await execAsync(`powershell -NoProfile -NonInteractive -EncodedCommand ${encoded}`);
  }
}

export const windowsControl = new WindowsControl();
