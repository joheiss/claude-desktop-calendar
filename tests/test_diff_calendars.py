import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from diff_calendars import only_in_first  # noqa: E402


def ev(uid, summary, recurrence_id=None):
    rid = f"RECURRENCE-ID:{recurrence_id}\r\n" if recurrence_id else ""
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//t//EN\r\nBEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n{rid}DTSTART:20270601T100000Z\r\nSUMMARY:{summary}\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )


def put(d, name, text):
    d.mkdir(exist_ok=True)
    (d / name).write_text(text, newline="")


def test_lists_only_uids_missing_in_second(tmp_path):
    first, second = tmp_path / "s", tmp_path / "g"
    put(first, "1.ics", ev("known", "Bekannt"))
    put(first, "2.ics", ev("only", "Nur Strato Müller"))
    put(second, "x.ics", ev("known", "Bekannt"))
    assert only_in_first(first, second) == [("only", "Nur Strato Müller")]


def test_ignores_instance_overrides_of_known_series(tmp_path):
    first, second = tmp_path / "s", tmp_path / "g"
    put(first, "1.ics", ev("series", "Serie", recurrence_id="20270608T100000Z"))
    put(second, "x.ics", ev("series", "Serie"))
    assert only_in_first(first, second) == []
