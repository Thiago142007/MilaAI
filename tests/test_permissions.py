from backend.app.security.permissions import CATEGORIES, MODE_POLICY, PermissionManager


def make_pm(mode="assisted"):
    import tempfile
    from pathlib import Path
    from backend.app.db.database import Database

    tmp = Path(tempfile.mkdtemp())
    db = Database(tmp / "perm.db")
    return PermissionManager(db, mode=mode), db


def test_assisted_defaults():
    pm, _ = make_pm()
    assert pm.decide("SCREEN_READ").allowed
    assert pm.decide("FILE_READ").allowed
    assert pm.decide("WEB").allowed
    assert pm.decide("FILE_WRITE").action == "confirm"
    assert pm.decide("TERMINAL").action == "confirm"


def test_file_delete_always_confirms_even_autonomous():
    pm, _ = make_pm(mode="autonomous")
    assert pm.decide("FILE_DELETE").action == "confirm"
    for cat in set(CATEGORIES) - {"FILE_DELETE"}:
        assert pm.decide(cat).allowed


def test_manual_blocks_most():
    pm, _ = make_pm(mode="manual")
    assert pm.decide("SCREEN_READ").allowed
    assert pm.decide("MOUSE_CONTROL").action == "confirm"


def test_task_grant_flow():
    pm, _ = make_pm(mode="manual")
    d = pm.decide("FILE_WRITE", task_id="t1")
    assert d.action == "confirm"
    pm.add_task_grant("FILE_WRITE", "t1")
    assert pm.decide("FILE_WRITE", task_id="t1").allowed
    assert pm.decide("FILE_WRITE", task_id="t2").action == "confirm"


def test_session_grant_and_reset():
    pm, _ = make_pm()
    assert pm.decide("TERMINAL").action == "confirm"
    pm.add_session_grant("TERMINAL")
    assert pm.decide("TERMINAL").allowed
    pm.reset_session()
    assert pm.decide("TERMINAL").action == "confirm"


def test_set_mode_persists():
    pm, db = make_pm()
    assert pm.set_mode("autonomous")
    assert not pm.set_mode("banana")
    row = db.fetch_one("SELECT value FROM settings WHERE key='autonomy_mode'")
    assert row["value"] == "autonomous"


def test_unknown_category_denied():
    pm, _ = make_pm()
    assert not pm.decide("NOT_A_CATEGORY").allowed
