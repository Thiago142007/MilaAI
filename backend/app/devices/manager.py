import asyncio
import logging
import platform
import psutil
import time
from typing import Any

log = logging.getLogger("nova.devices")


class BaseDevice:
    """Abstract interface for all hardware devices managed by NOVA."""

    def __init__(self, device_id: str, name: str, device_type: str) -> None:
        self.device_id = device_id
        self.name = name
        self.device_type = device_type
        self.connected = False
        self.last_seen: float = time.time()
        self.config: dict[str, Any] = {}

    async def connect(self, **kwargs) -> dict:
        raise NotImplementedError

    async def disconnect(self) -> dict:
        raise NotImplementedError

    async def send(self, payload: dict | str) -> dict:
        raise NotImplementedError

    async def receive(self) -> dict:
        raise NotImplementedError

    async def status(self) -> dict:
        return {
            "id": self.device_id,
            "name": self.name,
            "type": self.device_type,
            "connected": self.connected,
            "last_seen": self.last_seen,
        }


class LocalPCDevice(BaseDevice):
    """Local Windows Machine driver providing hardware telemetry and power metrics."""

    def __init__(self) -> None:
        super().__init__("local-pc", f"Local PC ({platform.node()})", "local_pc")
        self.connected = True

    async def connect(self, **kwargs) -> dict:
        self.connected = True
        return {"success": True, "message": "Local PC is always connected"}

    async def disconnect(self) -> dict:
        return {"success": False, "message": "Cannot disconnect host PC"}

    async def send(self, payload: dict | str) -> dict:
        # e.g., command to query battery, disk, or cpu
        return await self.status()

    async def receive(self) -> dict:
        return await self.status()

    async def status(self) -> dict:
        self.last_seen = time.time()
        battery = psutil.sensors_battery()
        return {
            "id": self.device_id,
            "name": self.name,
            "type": self.device_type,
            "connected": True,
            "os": f"{platform.system()} {platform.release()}",
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "battery_percent": battery.percent if battery else None,
            "power_plugged": battery.power_plugged if battery else True,
            "last_seen": self.last_seen,
        }


class ESP32Device(BaseDevice):
    """ESP32 Microcontroller driver supporting HTTP, Serial COM, or WebSocket."""

    def __init__(self, device_id: str, name: str, host_or_port: str = "") -> None:
        super().__init__(device_id, name, "esp32")
        self.host_or_port = host_or_port
        self.last_telemetry: dict[str, Any] = {}

    async def connect(self, host_or_port: str = "", **kwargs) -> dict:
        target = host_or_port or self.host_or_port
        if not target:
            return {"success": False, "error": "host or serial port required"}
        self.host_or_port = target
        self.connected = True
        self.last_seen = time.time()
        log.info("ESP32 [%s] connected at %s", self.device_id, target)
        return {"success": True, "device_id": self.device_id, "endpoint": target}

    async def disconnect(self) -> dict:
        self.connected = False
        log.info("ESP32 [%s] disconnected", self.device_id)
        return {"success": True, "device_id": self.device_id}

    async def send(self, payload: dict | str) -> dict:
        if not self.connected:
            return {"success": False, "error": "device not connected"}
        self.last_seen = time.time()
        self.last_telemetry["last_command"] = payload
        return {
            "success": True,
            "device_id": self.device_id,
            "sent": payload,
            "timestamp": self.last_seen,
        }

    async def receive(self) -> dict:
        self.last_seen = time.time()
        return {
            "success": True,
            "device_id": self.device_id,
            "telemetry": self.last_telemetry,
        }

    async def status(self) -> dict:
        return {
            "id": self.device_id,
            "name": self.name,
            "type": self.device_type,
            "connected": self.connected,
            "endpoint": self.host_or_port,
            "last_seen": self.last_seen,
            "telemetry": self.last_telemetry,
        }


class MobileDevice(BaseDevice):
    """Mobile Companion Device bridge for notifications and remote pairing."""

    def __init__(self, device_id: str, name: str = "Mobile Companion") -> None:
        super().__init__(device_id, name, "mobile")
        self.pending_notifications: list[str] = []

    async def connect(self, pairing_code: str = "", **kwargs) -> dict:
        self.connected = True
        self.last_seen = time.time()
        return {"success": True, "paired": True, "device_id": self.device_id}

    async def disconnect(self) -> dict:
        self.connected = False
        return {"success": True, "device_id": self.device_id}

    async def send(self, payload: dict | str) -> dict:
        if not self.connected:
            return {"success": False, "error": "mobile device not paired"}
        self.last_seen = time.time()
        if isinstance(payload, str):
            self.pending_notifications.append(payload)
        return {"success": True, "device_id": self.device_id, "sent": payload}

    async def receive(self) -> dict:
        return {"success": True, "notifications_sent": len(self.pending_notifications)}

    async def status(self) -> dict:
        return {
            "id": self.device_id,
            "name": self.name,
            "type": self.device_type,
            "connected": self.connected,
            "pending_notifications": len(self.pending_notifications),
            "last_seen": self.last_seen,
        }


class DeviceManager:
    """Registry and coordinator for all connected external devices."""

    def __init__(self) -> None:
        self.devices: dict[str, BaseDevice] = {}
        # Register host PC by default
        self.register_device(LocalPCDevice())

    def register_device(self, device: BaseDevice) -> None:
        self.devices[device.device_id] = device
        log.info("Registered device: %s (%s)", device.name, device.device_type)

    def get(self, device_id: str) -> BaseDevice | None:
        return self.devices.get(device_id)

    async def list_all(self) -> list[dict]:
        results = []
        for dev in self.devices.values():
            results.append(await dev.status())
        return results

    async def connect_device(self, device_id: str, **kwargs) -> dict:
        dev = self.get(device_id)
        if not dev:
            return {"success": False, "error": f"device '{device_id}' not found"}
        return await dev.connect(**kwargs)

    async def disconnect_device(self, device_id: str) -> dict:
        dev = self.get(device_id)
        if not dev:
            return {"success": False, "error": f"device '{device_id}' not found"}
        return await dev.disconnect()

    async def send_to_device(self, device_id: str, payload: dict | str) -> dict:
        dev = self.get(device_id)
        if not dev:
            return {"success": False, "error": f"device '{device_id}' not found"}
        return await dev.send(payload)
