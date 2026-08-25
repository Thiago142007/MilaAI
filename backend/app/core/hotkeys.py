import logging

log = logging.getLogger("nova.hotkeys")


def start_emergency_hotkey(settings, on_trigger) -> bool:
    try:
        import keyboard
    except Exception as exc:
        log.warning("global hotkey unavailable: %s", exc)
        return False

    combo = settings.emergency_hotkey

    def _trigger():
        log.warning("EMERGENCY HOTKEY PRESSED: %s", combo)
        try:
            on_trigger()
        except Exception:
            log.exception("emergency trigger callback failed")

    try:
        keyboard.add_hotkey(combo, _trigger, suppress=False)
        log.info("emergency hotkey registered: %s", combo)
        return True
    except Exception as exc:
        log.warning("failed to register hotkey %s: %s", combo, exc)
        return False
