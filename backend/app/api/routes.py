import asyncio
import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

log = logging.getLogger("nova.api")

router = APIRouter(prefix="/api")


def get_services(request: Request):
    return request.app.state.services


@router.get("/status")
async def status(request: Request):
    svcs = get_services(request)
    s = svcs.settings

    tools_count = len(svcs.registry.all())

    if svcs.llm.api_keys or "localhost" in s.llm_base_url or "127.0.0.1" in s.llm_base_url:
        try:
            ai = await asyncio.wait_for(svcs.llm.health(), timeout=3.5)
        except Exception:
            ai = {"ok": False, "detail": f"{s.llm_model} configured (health check timeout)"}
    else:
        ai = {"ok": False, "detail": "NOVA_LLM_API_KEY not configured"}

    screen_ok = True
    screen_detail = "ready"
    try:
        from backend.app.tools.builtin.screen import capture_screen_image

        _ = capture_screen_image()
    except Exception as exc:
        screen_ok, screen_detail = False, str(exc)

    browser_detail = "not started (starts on first browser.* tool)"
    playwright_ready = True
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        playwright_ready = False
        browser_detail = "playwright package missing"

    voice_st = svcs.voice.status()

    return {
        "version": "0.1.0",
        "uptime_s": round(time.time() - svcs.started_at, 1),
        "emergency_stopped": svcs.stop_event.is_set(),
        "autonomy_mode": svcs.permissions.mode,
        "checks": {
            "ai": ai,
            "tools": {"ok": tools_count > 0, "detail": f"{tools_count} tools loaded"},
            "permissions": {"ok": True, "detail": f"mode={svcs.permissions.mode}"},
            "screen": {"ok": screen_ok, "detail": screen_detail},
            "browser": {"ok": playwright_ready, "detail": browser_detail},
            "memory": {"ok": svcs.db.health(), "detail": str(s.db_path)},
            "microphone": {"ok": voice_st["ok"], "detail": voice_st["detail"]},
        },
    }


@router.post("/chat")
async def chat(request: Request):
    svcs = get_services(request)
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    runner = request.app.state.runner
    info = await runner.start_chat(text, body.get("conversation_id"))
    task_handle = runner.running.get(info["task_id"])
    try:
        reply = await asyncio.wait_for(task_handle, timeout=300)
    except asyncio.TimeoutError:
        raise HTTPException(504, "agent timed out")
    return {"conversation_id": info["conversation_id"], "task_id": info["task_id"], "reply": reply}


@router.get("/conversations")
async def conversations(request: Request):
    return get_services(request).memory.list_conversations()


@router.get("/conversations/{cid}/messages")
async def messages(cid: str, request: Request):
    svcs = get_services(request)
    return svcs.memory.get_messages(cid, limit=200)


@router.get("/tasks")
async def tasks_list(request: Request, limit: int = 100):
    return get_services(request).tasks.list(limit)


@router.get("/tasks/{task_id}")
async def task_get(task_id: str, request: Request):
    task = get_services(request).tasks.get(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return task


@router.get("/tasks/{task_id}/events")
async def task_events(task_id: str, request: Request):
    return get_services(request).tasks.events(task_id)


@router.post("/tasks/{task_id}/cancel")
async def task_cancel(task_id: str, request: Request):
    svcs = get_services(request)
    ok_ = await svcs.tasks.cancel(task_id)
    request.app.state.runner.cancel_task(task_id)
    if not ok_:
        raise HTTPException(409, "task cannot be cancelled")
    return {"cancelled": True}


@router.post("/tasks/{task_id}/pause")
async def task_pause(task_id: str, request: Request):
    svcs = get_services(request)
    if not svcs.tasks.get(task_id):
        raise HTTPException(404, "task not found")
    svcs.tasks.pause(task_id)
    await svcs.tasks.set_status(task_id, "waiting_confirmation")
    return {"paused": True}


@router.post("/tasks/{task_id}/resume")
async def task_resume(task_id: str, request: Request):
    svcs = get_services(request)
    await svcs.tasks.resume(task_id)
    await svcs.tasks.set_status(task_id, "executing")
    return {"resumed": True}


@router.post("/emergency-stop")
async def emergency_stop(request: Request):
    svcs = get_services(request)
    svcs.stop_event.set()
    svcs.voice.stop_speaking()
    cancelled = await request.app.state.runner.cancel_all()
    await svcs.bus.publish("emergency", {"active": True, "cancelled_tasks": cancelled})
    svcs.audit.write("security", "emergency_stop", cancelled=cancelled)
    return {"stopped": True, "cancelled_tasks": cancelled}


@router.post("/reset-emergency")
async def reset_emergency(request: Request):
    svcs = get_services(request)
    svcs.stop_event.clear()
    await svcs.bus.publish("emergency", {"active": False})
    return {"reset": True}


@router.get("/screenshot")
async def screenshot(request: Request):
    path = Path(get_services(request).screen_ctx.latest_path)
    if not path.exists():
        # Trigger auto capture so image is always available
        svcs = get_services(request)
        tool = svcs.registry.get("screen.screenshot")
        await tool.handler()
    if not path.exists():
        raise HTTPException(404, "screenshot could not be generated")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/screenshot/capture")
async def screenshot_capture(request: Request):
    svcs = get_services(request)
    tool = svcs.registry.get("screen.screenshot")
    result = await tool.handler()
    if not result.get("success"):
        return {"success": False, "error": result.get("error")}
    return {
        "success": True,
        "size": [result["data"]["width"], result["data"]["height"]],
    }


@router.get("/tools")
async def tools(request: Request):
    return get_services(request).registry.describe_all()


@router.get("/permissions")
async def permissions(request: Request):
    svcs = get_services(request)
    return {"mode": svcs.permissions.mode, "categories": svcs.permissions.status()}


@router.post("/permissions/mode")
async def set_mode(request: Request):
    svcs = get_services(request)
    body = await request.json()
    mode = body.get("mode", "")
    if not svcs.permissions.set_mode(mode):
        raise HTTPException(400, "mode must be manual|assisted|autonomous")
    await svcs.bus.publish("mode_changed", {"mode": mode})
    return {"mode": mode}


@router.post("/permissions/grant")
async def grant(request: Request):
    svcs = get_services(request)
    body = await request.json()
    category = body.get("category", "")
    scope = body.get("scope", "session")
    from backend.app.security.permissions import CATEGORIES

    if category not in CATEGORIES:
        raise HTTPException(400, f"category must be one of {CATEGORIES}")
    if scope == "session":
        svcs.permissions.add_session_grant(category)
    else:
        raise HTTPException(400, "scope must be 'session'")
    return {"granted": category, "scope": scope}


@router.post("/permissions/reset")
async def reset_grants(request: Request):
    get_services(request).permissions.reset_session()
    return {"reset": True}


@router.get("/confirmations")
async def pending_confirmations(request: Request):
    return get_services(request).confirmations.pending_list()


@router.get("/audit")
async def audit(request: Request, limit: int = 100, offset: int = 0):
    return get_services(request).audit.fetch(limit, offset)


@router.get("/logs")
async def logs(request: Request, limit: int = 200):
    from backend.app.logging_setup import get_ring

    items = list(get_ring().buffer)[-limit:]
    return list(reversed(items))


@router.get("/memory")
async def memory_list(request: Request, limit: int = 200, kind: str | None = None):
    return get_services(request).memory.list_memories(limit, kind=kind)


@router.post("/memory")
async def memory_add(request: Request):
    svcs = get_services(request)
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(400, "content required")
    mid = svcs.memory.remember(
        content,
        kind=body.get("kind", "fact"),
        importance=float(body.get("importance", 0.7)),
    )
    return {"id": mid}


@router.delete("/memory/{memory_id}")
async def memory_delete(memory_id: int, request: Request):
    deleted = get_services(request).memory.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(404, "memory not found")
    return {"deleted": memory_id}


@router.get("/memory/procedures")
async def memory_procedures_list(request: Request):
    return get_services(request).memory.list_procedures()


@router.post("/memory/procedures")
async def memory_procedures_create(request: Request):
    svcs = get_services(request)
    body = await request.json()
    name = (body.get("name") or "").strip()
    steps = body.get("steps") or []
    desc = body.get("description", "")
    if not name or not steps:
        raise HTTPException(400, "name and steps are required")
    pid = svcs.memory.save_procedure(name, steps, desc)
    return {"id": pid, "name": name, "steps_count": len(steps)}


# ── Voice API ─────────────────────────────────────────────────────────────
@router.get("/voice/status")
async def voice_status(request: Request):
    return get_services(request).voice.status()


@router.post("/voice/tts")
async def voice_tts(request: Request):
    body = await request.json()
    text = (body.get("text") or "").strip()
    wait = bool(body.get("wait", False))
    if not text:
        raise HTTPException(400, "text is required")
    spoken = await get_services(request).voice.speak(text, wait=wait)
    return {"spoken": spoken, "text": text[:200]}


@router.post("/voice/stop")
async def voice_stop(request: Request):
    get_services(request).voice.stop_speaking()
    return {"stopped": True}


# ── Devices API ───────────────────────────────────────────────────────────
@router.get("/devices")
async def devices_list(request: Request):
    return await get_services(request).devices.list_all()


@router.get("/devices/{device_id}/status")
async def device_status(device_id: str, request: Request):
    dev = get_services(request).devices.get(device_id)
    if not dev:
        raise HTTPException(404, f"device '{device_id}' not found")
    return await dev.status()


@router.post("/devices/{device_id}/connect")
async def device_connect(device_id: str, request: Request):
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    endpoint = body.get("endpoint", "")
    res = await get_services(request).devices.connect_device(device_id, host_or_port=endpoint)
    if not res.get("success"):
        raise HTTPException(400, res.get("error", "connection failed"))
    return res


@router.post("/devices/{device_id}/disconnect")
async def device_disconnect(device_id: str, request: Request):
    res = await get_services(request).devices.disconnect_device(device_id)
    if not res.get("success"):
        raise HTTPException(400, res.get("error", "disconnection failed"))
    return res


@router.post("/devices/{device_id}/send")
async def device_send(device_id: str, request: Request):
    body = await request.json()
    payload = body.get("payload")
    if payload is None:
        raise HTTPException(400, "payload is required")
    res = await get_services(request).devices.send_to_device(device_id, payload)
    if not res.get("success"):
        raise HTTPException(400, res.get("error", "send failed"))
    return res


@router.get("/settings")
async def settings_info(request: Request):
    s = get_services(request).settings
    keys = s.api_keys
    return {
        "llm_base_url": s.llm_base_url,
        "llm_protocol": s.llm_protocol,
        "llm_model": s.llm_model,
        "vision_model": s.vision_model,
        "api_keys_configured": len(keys),
        "autonomy_mode": s.autonomy_mode,
        "agent_max_steps": s.agent_max_steps,
        "workspace_root": str(s.workspace_path),
        "emergency_hotkey": s.emergency_hotkey,
    }


@router.get("/voice/status")
async def voice_status(request: Request):
    return get_services(request).voice.status()


@router.get("/voice/voices")
async def voice_voices(request: Request):
    return {"voices": get_services(request).voice.get_voices()}


@router.post("/voice/tts")
async def voice_tts(request: Request):
    body = await request.json()
    text = body.get("text", "")
    voice = body.get("voice")
    speed = body.get("speed")
    if not text:
        raise HTTPException(400, "text is required")
    audio_b64 = await get_services(request).voice.generate_audio_base64(text, voice, speed)
    return {"ok": True, "audioBase64": audio_b64}


@router.post("/voice/stop")
async def voice_stop(request: Request):
    get_services(request).voice.stop_speaking()
    return {"ok": True}


@router.post("/voice/config")
async def voice_update_config(request: Request):
    body = await request.json()
    get_services(request).voice.update_config(
        voice=body.get("voice"),
        speed=body.get("speed"),
        volume=body.get("volume"),
        device=body.get("device"),
    )
    return {"ok": True, "status": get_services(request).voice.status()}

