import pytest
from backend.app.devices.manager import (
    DeviceManager,
    ESP32Device,
    LocalPCDevice,
    MobileDevice,
)
from backend.app.tools.base import ToolRegistry
from backend.app.tools.builtin.devices import register_tools


@pytest.mark.asyncio
async def test_device_manager_basics():
    mgr = DeviceManager()
    devices = await mgr.list_all()
    assert len(devices) >= 1
    assert any(d["id"] == "local-pc" for d in devices)


@pytest.mark.asyncio
async def test_esp32_device():
    mgr = DeviceManager()
    esp = ESP32Device("esp-test", "ESP32 Test")
    mgr.register_device(esp)

    # Test connect
    conn_res = await mgr.connect_device("esp-test", host_or_port="192.168.1.100")
    assert conn_res["success"] is True

    # Test send
    send_res = await mgr.send_to_device("esp-test", {"command": "toggle_led", "pin": 2})
    assert send_res["success"] is True

    # Test status
    st = await esp.status()
    assert st["connected"] is True
    assert st["endpoint"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_mobile_device():
    mgr = DeviceManager()
    mobile = MobileDevice("mobile-1", "User Phone")
    mgr.register_device(mobile)

    conn = await mgr.connect_device("mobile-1", pairing_code="1234")
    assert conn["success"] is True

    send_res = await mgr.send_to_device("mobile-1", "Hello from NOVA")
    assert send_res["success"] is True


@pytest.mark.asyncio
async def test_device_tools():
    mgr = DeviceManager()
    reg = ToolRegistry()
    register_tools(reg, mgr)

    assert reg.get("device.list") is not None
    assert reg.get("device.status") is not None
    assert reg.get("device.connect") is not None
    assert reg.get("device.send") is not None

    list_res = await reg.get("device.list").handler()
    assert list_res["success"] is True
    assert len(list_res["data"]) >= 1
