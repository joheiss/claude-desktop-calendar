"""Listet Termine, die nur in einem Kalenderordner (.ics-Dateien) stehen."""
import pathlib
import sys

import icalendar


def _events(directory: pathlib.Path) -> dict:
    found = {}
    for path in sorted(pathlib.Path(directory).glob("*.ics")):
        cal = icalendar.Calendar.from_ical(path.read_bytes())
        for comp in cal.walk("VEVENT"):
            uid = str(comp.get("UID"))
            found.setdefault(uid, str(comp.get("SUMMARY", "")))
    return found


def only_in_first(first_dir: pathlib.Path, second_dir: pathlib.Path) -> list[tuple[str, str]]:
    second = _events(second_dir)
    return [(uid, summary) for uid, summary in _events(first_dir).items()
            if uid not in second]


if __name__ == "__main__":
    rows = only_in_first(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
    for uid, summary in rows:
        print(f"{summary}\t{uid}")
    print(f"-- {len(rows)} nur im ersten Ordner", file=sys.stderr)
