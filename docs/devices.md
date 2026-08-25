# Device Manager Subsystem

NOVA includes an extensible `DeviceManager` architecture designed to interact with external hardware, microcontrollers, mobile companions, and IoT automation devices.

## Device Drivers

1. **Local PC Driver (`LocalPCDevice`)**:
   - Telemetry monitoring: CPU usage %, Virtual RAM usage %, Disk usage %, Battery level and power state.
   - OS detection and hardware statistics.

2. **ESP32 Microcontroller Driver (`ESP32Device`)**:
   - Connection via IP/HTTP, Serial COM Port, or WebSocket.
   - Sensor readings (temperature, humidity, motion, distance).
   - Actuator commands (relays, RGB LEDs, motor controllers, servo positioning).

3. **Mobile Companion Driver (`MobileDevice`)**:
   - Remote notification dispatch.
   - Pairing code negotiation.
   - Camera and mobile sensor integration bridge.

4. **Generic IoT Driver**:
   - REST webhook and MQTT broker communication for smart home automation.

## Tools

| Tool | Parameters | Description |
|---|---|---|
| `device.list` | None | Lists all registered and connected hardware devices. |
| `device.status` | `device_id: string` | Retrieves live telemetry, status and connection info for a device. |
| `device.connect` | `device_id: string`, `endpoint: string` | Establishes connection to an external device. |
| `device.send` | `device_id: string`, `payload: object` | Sends commands or data packets to a connected device. |

## REST Endpoints

- `GET /api/devices` - Returns array of all registered devices with statuses.
- `GET /api/devices/{id}/status` - Live status of a specific device.
- `POST /api/devices/{id}/connect` - Connects to device endpoint (IP/COM).
- `POST /api/devices/{id}/disconnect` - Disconnects the device.
- `POST /api/devices/{id}/send` - Transmits a command or JSON payload.
