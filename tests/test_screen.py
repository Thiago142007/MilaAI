from backend.app.tools.builtin.screen import ScreenContext, capture_screen_image


def test_capture_screen_fallback(tmp_path):
    img = capture_screen_image()
    assert img is not None
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_screen_context_jpeg(tmp_path):
    from unittest.mock import MagicMock

    llm = MagicMock()
    ctx = ScreenContext(tmp_path, llm, "vision-model")
    jpeg, size = ctx.capture_jpeg()
    assert isinstance(jpeg, bytes)
    assert len(jpeg) > 100
    assert size[0] > 0 and size[1] > 0
