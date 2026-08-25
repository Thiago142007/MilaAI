import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger("nova.ws")


async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    app = websocket.app
    svcs = app.state.services

    sid, queue = await svcs.bus.subscribe()
    log.info("ws client connected (%s)", sid)

    async def sender():
        while True:
            msg = await queue.get()
            await websocket.send_text(json.dumps(msg, ensure_ascii=False, default=str))

    send_task = asyncio.create_task(sender())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "payload": {"message": "invalid json"}}))
                continue

            mtype = data.get("type")

            if mtype == "chat_message":
                text = (data.get("text") or "").strip()
                if not text:
                    continue
                if svcs.stop_event.is_set():
                    await websocket.send_text(
                        json.dumps({"type": "error", "payload": {"message": "emergency stop is active - reset first"}})
                    )
                    continue
                info = await app.state.runner.start_chat(text, data.get("conversation_id"))
                await websocket.send_text(json.dumps({"type": "chat_accepted", "payload": info}))

            elif mtype == "confirmation_response":
                resolved = svcs.confirmations.resolve(
                    data.get("id", ""), data.get("decision", "deny")
                )
                if not resolved:
                    await websocket.send_text(
                        json.dumps({"type": "error", "payload": {"message": "confirmation not found or already resolved"}})
                    )

            elif mtype == "cancel_task":
                await svcs.tasks.cancel(data.get("task_id", ""))

            elif mtype == "pause_task":
                svcs.tasks.pause(data.get("task_id", ""))
                await svcs.tasks.set_status(data.get("task_id", ""), "waiting_confirmation")

            elif mtype == "resume_task":
                tid = data.get("task_id", "")
                await svcs.tasks.resume(tid)
                await svcs.tasks.set_status(tid, "executing")

            elif mtype == "emergency_stop":
                svcs.stop_event.set()
                svcs.voice.stop_speaking()
                cancelled = await app.state.runner.cancel_all()
                svcs.audit.write("security", "emergency_stop", source="ui", cancelled=cancelled)
                await svcs.bus.publish("emergency", {"active": True, "cancelled_tasks": cancelled})

            elif mtype == "reset_emergency":
                svcs.stop_event.clear()
                await svcs.bus.publish("emergency", {"active": False})

            elif mtype == "voice_stop":
                svcs.voice.stop_speaking()

            elif mtype == "set_mode":
                mode = data.get("mode", "")
                if svcs.permissions.set_mode(mode):
                    await svcs.bus.publish("mode_changed", {"mode": mode})
                else:
                    await websocket.send_text(
                        json.dumps({"type": "error", "payload": {"message": "invalid mode"}})
                    )

            elif mtype == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws handler error")
    finally:
        send_task.cancel()
        await svcs.bus.unsubscribe(sid)
        log.info("ws client disconnected (%s)", sid)
