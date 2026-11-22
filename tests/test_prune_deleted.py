import pathlib
import sqlite3
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from prune_deleted import TooManyDeletions, find_orphans, prune  # noqa: E402

SCHEMA = """CREATE TABLE status ("ident" TEXT PRIMARY KEY NOT NULL, "href_a" TEXT, "href_b" TEXT,
"hash_a" TEXT NOT NULL, "hash_b" TEXT NOT NULL, "etag_a" TEXT, "etag_b" TEXT)"""


def make_status(path, rows):
    con = sqlite3.connect(path)
    con.execute(SCHEMA)
    for ident, a, b in rows:
        con.execute("INSERT INTO status VALUES (?,?,?,?,?,?,?)", (ident, a, b, "h", "h", "e", "e"))
    con.commit()
    con.close()
    return path


def make_google(d, uids):
    d.mkdir(exist_ok=True)
    for uid in uids:
        (d / f"{uid}.ics").write_text(
            f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//t//EN\r\nBEGIN:VEVENT\r\nUID:{uid}\r\n"
            "DTSTART:20270601T100000Z\r\nSUMMARY:x\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n", newline="")
    return d


def test_find_orphans_returns_items_missing_in_google(tmp_path):
    st = make_status(tmp_path / "s.db", [("u1", "/a/u1", "/b/u1.ics"), ("u2", "/a/u2", "/b/u2.ics")])
    g = make_google(tmp_path / "g", ["u1"])
    assert find_orphans(st, g) == [("u2", "/b/u2.ics")]


def test_items_never_from_google_are_ignored(tmp_path):
    st = make_status(tmp_path / "s.db", [("u1", None, "/b/u1.ics")])
    g = make_google(tmp_path / "g", ["other"])
    assert find_orphans(st, g) == []


def test_prune_deletes_orphans_via_callback(tmp_path):
    st = make_status(tmp_path / "s.db", [("u1", "/a/u1", "/b/u1.ics"), ("u2", "/a/u2", "/b/u2.ics")])
    g = make_google(tmp_path / "g", ["u1"])
    deleted = []
    assert prune(st, g, deleted.append) == 1
    assert deleted == ["/b/u2.ics"]


def test_prune_refuses_mass_deletion(tmp_path):
    rows = [(f"u{i}", f"/a/u{i}", f"/b/u{i}.ics") for i in range(12)]
    st = make_status(tmp_path / "s.db", rows)
    g = make_google(tmp_path / "g", ["u0"])
    deleted = []
    with pytest.raises(TooManyDeletions):
        prune(st, g, deleted.append, max_deletes=10)
    assert deleted == []


def test_prune_refuses_when_google_copy_is_empty(tmp_path):
    st = make_status(tmp_path / "s.db", [("u1", "/a/u1", "/b/u1.ics")])
    (tmp_path / "g").mkdir()
    deleted = []
    with pytest.raises(TooManyDeletions):
        prune(st, tmp_path / "g", deleted.append)
    assert deleted == []
