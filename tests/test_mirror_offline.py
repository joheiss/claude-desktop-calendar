"""mirror.sh bei fehlendem Netz: still überspringen, erst nach 24 h ohne Erfolg melden."""
import os
import pathlib
import subprocess
import time

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "mirror.sh"


def run(tmp_path, last_success_age_hours=None):
    home = tmp_path / "home"
    state = home / ".local/state/calendar-mirror"
    (home / "Library/Logs").mkdir(parents=True)
    state.mkdir(parents=True)
    if last_success_age_hours is not None:
        f = state / "last-success"
        f.write_text("")
        t = time.time() - last_success_age_hours * 3600
        os.utime(f, (t, t))
    marker = tmp_path / "notified"
    notify = tmp_path / "notify.sh"
    notify.write_text(f'#!/bin/sh\necho "$1" > "{marker}"\n')
    notify.chmod(0o755)
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
           "MIRROR_NET_URL": "http://127.0.0.1:9", "NOTIFY_CMD": str(notify)}
    r = subprocess.run(["/bin/zsh", str(SCRIPT)], env=env, capture_output=True, text=True)
    log = (home / "Library/Logs/calendar-mirror.log").read_text()
    return r.returncode, log, marker.exists()


def test_offline_is_skipped_silently(tmp_path):
    rc, log, notified = run(tmp_path, last_success_age_hours=1)
    assert rc == 0
    assert "offline" in log
    assert not notified


def test_offline_for_more_than_24h_notifies(tmp_path):
    rc, log, notified = run(tmp_path, last_success_age_hours=30)
    assert rc == 0
    assert notified
