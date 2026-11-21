import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from build_config import build_config  # noqa: E402

VALUES = (
    "GOOGLE_CLIENT_ID=cid.apps.example\nGOOGLE_CAL_ID=primary-id\n"
    "STRATO_URL=https://caldav.example/\nSTRATO_USER=user1\nSTRATO_CAL_NAME=Privat\n"
)


def render(tmp_path, monkeypatch, mode):
    env = tmp_path / "real-values.env"
    env.write_text(VALUES)
    monkeypatch.setenv("VDIRSYNCER_REAL_VALUES", str(env))
    return build_config(mode, "real", tmp_path / "cfg").read_text()


def test_real_mirror_uses_keychain_and_marks_google_read_only(tmp_path, monkeypatch):
    text = render(tmp_path, monkeypatch, "mirror")
    assert "https://caldav.example/" in text
    assert 'type = "google_calendar"' in text
    assert "find-generic-password" in text
    assert "read_only = true" in text
    assert 'collections = [["main", "primary-id", "Privat"]]' in text
    assert "{{" not in text


def test_real_import_is_writable_both_ways(tmp_path, monkeypatch):
    text = render(tmp_path, monkeypatch, "import")
    assert "read_only" not in text
    assert "partial_sync" not in text
