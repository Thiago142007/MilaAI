import io
import json
import os
import sys
from pathlib import Path

# Force UTF-8 encoding on standard streams
try:
    if sys.stdout and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True, write_through=True)
    if sys.stdin and hasattr(sys.stdin, "buffer"):
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
except Exception:
    pass

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[3]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

def safe_write(msg_dict):
    try:
        data = json.dumps(msg_dict, ensure_ascii=False)
        sys.stdout.write(data + "\n")
        try:
            sys.stdout.flush()
        except OSError:
            pass
    except Exception:
        pass

def main():
    try:
        from backend.app.voice.kokoro_engine import KokoroEngine
        from backend.app.voice.config import get_tts_config
        from backend.app.voice.audio import audio_to_base64_data_uri
        from backend.app.voice.preprocessor import TextPreprocessor
        
        config = get_tts_config()
        engine = KokoroEngine(config)
        engine.initialize()
        
        # Send ready signal
        safe_write({"type": "ready", "voices": engine.get_available_voices()})
    except Exception as e:
        safe_write({"type": "ready", "voices": ["pf_dora", "pm_alex", "af_heart"], "error": str(e)})
        return

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = {}
        try:
            req = json.loads(line)
            req_id = req.get("id")
            action = req.get("action", "generate")

            if action == "generate":
                text = req.get("text", "")
                voice = req.get("voice", config.voice)
                speed = req.get("speed", config.speed)
                lang = req.get("lang")

                cleaned = TextPreprocessor.clean_text(text)
                if not cleaned:
                    safe_write({"id": req_id, "ok": True, "audioBase64": ""})
                    continue

                samples, sr = engine.generate(cleaned, voice=voice, speed=speed, lang=lang)
                if len(samples) > 0:
                    audio_b64 = audio_to_base64_data_uri(samples, sr, config.volume)
                else:
                    audio_b64 = ""

                safe_write({"id": req_id, "ok": True, "audioBase64": audio_b64})

            elif action == "status":
                resp = {
                    "id": req_id,
                    "ok": True,
                    "engine": "Kokoro-82M",
                    "device": config.device,
                    "voice": config.voice,
                    "speed": config.speed,
                    "voices": engine.get_available_voices(),
                }
                safe_write(resp)

            elif action == "voices":
                safe_write({"id": req_id, "ok": True, "voices": engine.get_available_voices()})

            elif action == "stop":
                safe_write({"id": req_id, "ok": True})

        except Exception as e:
            req_id = req.get("id") if isinstance(req, dict) else None
            safe_write({"id": req_id, "ok": False, "error": str(e)})

if __name__ == "__main__":
    main()
