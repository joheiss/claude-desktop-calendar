"""Prüft die Spiegel-Semantik (Google = Seite a, Strato = Seite b) mit lokalen
Dateispeichern. Keine echten Konten."""
import pathlib
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from build_config import build_config  # noqa: E402

VDIRSYNCER = shutil.which("vdirsyncer") or str(pathlib.Path.home() / ".local/bin/vdirsyncer")


def ics(uid, summary, dtstart="DTSTART:20270601T100000Z", extra=""):
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n"
        f"BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTAMP:20261121T000000Z\r\n{dtstart}\r\n"
        f"SUMMARY:{summary}\r\n{extra}END:VEVENT\r\nEND:VCALENDAR\r\n"
    )


class Env:
    def __init__(self, base: pathlib.Path, mode: str):
        self.a, self.b = base / "a", base / "b"
        self.a.mkdir()
        self.b.mkdir()
        (base / "status").mkdir()
        self.cfg = build_config(mode, f"test:{base}", base / "config")

    def run(self, *args):
        r = subprocess.run([VDIRSYNCER, "-c", str(self.cfg), *args],
                           capture_output=True, text=True, input="y\n")
        assert r.returncode == 0, r.stdout + r.stderr
        return r

    def sync(self):
        self.run("discover", "cal")
        self.run("sync", "cal")

    @staticmethod
    def put(d, uid, text):
        (d / f"{uid}.ics").write_text(text, newline="")

    @staticmethod
    def names(d):
        return sorted(p.stem for p in d.glob("*.ics"))

    @staticmethod
    def lines(d, uid):
        return (d / f"{uid}.ics").read_text().splitlines()


@pytest.fixture
def mirror(tmp_path):
    return Env(tmp_path, "mirror")


@pytest.fixture
def imp(tmp_path):
    return Env(tmp_path, "import")


def test_new_item_in_a_appears_in_b(mirror):
    mirror.put(mirror.a, "u1", ics("u1", "Test"))
    mirror.sync()
    assert mirror.names(mirror.b) == ["u1"]


def test_edit_in_a_updates_b(mirror):
    mirror.put(mirror.a, "u1", ics("u1", "Zahnarzt"))
    mirror.sync()
    mirror.put(mirror.a, "u1", ics("u1", "Zahnärztin Müller"))
    mirror.sync()
    assert "SUMMARY:Zahnärztin Müller" in mirror.lines(mirror.b, "u1")


def test_delete_in_a_removes_from_b(mirror):
    mirror.put(mirror.a, "u1", ics("u1", "Weg"))
    mirror.put(mirror.a, "u2", ics("u2", "Bleibt"))
    mirror.sync()
    (mirror.a / "u1.ics").unlink()
    mirror.sync()
    assert mirror.names(mirror.b) == ["u2"]


def test_item_created_only_in_b_never_reaches_a(mirror):
    mirror.put(mirror.a, "u1", ics("u1", "Google"))
    mirror.sync()
    mirror.put(mirror.b, "u2", ics("u2", "Nur Strato"))
    mirror.sync()
    assert mirror.names(mirror.a) == ["u1"]


def test_edit_in_b_never_reaches_a(mirror):
    mirror.put(mirror.a, "u1", ics("u1", "Original"))
    mirror.sync()
    before = mirror.lines(mirror.a, "u1")
    mirror.put(mirror.b, "u1", ics("u1", "Manipuliert"))
    mirror.sync()
    assert mirror.lines(mirror.a, "u1") == before


def test_later_edit_in_a_overwrites_edit_in_b(mirror):
    mirror.put(mirror.a, "u1", ics("u1", "Original"))
    mirror.sync()
    mirror.put(mirror.b, "u1", ics("u1", "Manipuliert"))
    mirror.put(mirror.a, "u1", ics("u1", "Neu aus Google"))
    mirror.sync()
    assert "SUMMARY:Neu aus Google" in mirror.lines(mirror.b, "u1")


def test_recurring_event_with_changed_instance_copied_unchanged(mirror):
    series = ics("r1", "Jour fixe", extra="RRULE:FREQ=WEEKLY;COUNT=4\r\n")
    override = (
        "BEGIN:VEVENT\r\nUID:r1\r\nDTSTAMP:20261121T000000Z\r\n"
        "RECURRENCE-ID:20270608T100000Z\r\nDTSTART:20270608T120000Z\r\n"
        "SUMMARY:Jour fixe (verschoben)\r\nEND:VEVENT\r\n"
    )
    text = series.replace("END:VCALENDAR\r\n", override + "END:VCALENDAR\r\n")
    mirror.put(mirror.a, "r1", text)
    mirror.sync()
    assert mirror.lines(mirror.b, "r1") == text.splitlines()
    assert mirror.names(mirror.b) == ["r1"]  # keine Dublette


def test_allday_event_and_dst_crossing_event_identical(mirror):
    allday = ics("d1", "Urlaub", dtstart="DTSTART;VALUE=DATE:20270328")
    berlin = ics("d2", "Sommerzeit",
                 dtstart="DTSTART;TZID=Europe/Berlin:20270328T013000",
                 extra="DTEND;TZID=Europe/Berlin:20270328T033000\r\n")
    mirror.put(mirror.a, "d1", allday)
    mirror.put(mirror.a, "d2", berlin)
    mirror.sync()
    assert mirror.lines(mirror.b, "d1") == allday.splitlines()
    assert mirror.lines(mirror.b, "d2") == berlin.splitlines()


def test_import_copies_b_only_item_to_a(imp):
    imp.put(imp.b, "old", ics("old", "Alter Strato-Termin"))
    imp.sync()
    assert imp.names(imp.a) == ["old"]
