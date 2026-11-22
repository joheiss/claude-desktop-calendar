"""Löscht in Strato Termine, die aus Google stammen und dort nicht mehr existieren.

Nötig, weil Strato (Open-Xchange) Termine beim Speichern umschreibt: vdirsyncer
hält sie dann für "in b geändert" und gibt Löschungen aus Google nicht weiter.
"""
import base64
import os
import pathlib
import sqlite3
import ssl
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from diff_calendars import _events  # noqa: E402


class TooManyDeletions(Exception):
    pass


def find_orphans(status_db: pathlib.Path, google_dir: pathlib.Path) -> list[tuple[str, str]]:
    in_google = set(_events(google_dir))
    con = sqlite3.connect(status_db)
    try:
        rows = con.execute("SELECT ident, href_b FROM status "
                           "WHERE href_a IS NOT NULL AND href_b IS NOT NULL").fetchall()
    finally:
        con.close()
    return [(ident, href) for ident, href in rows if ident not in in_google]


def prune(status_db, google_dir, delete_href, max_deletes: int = 10) -> int:
    if not list(pathlib.Path(google_dir).glob("*.ics")):
        raise TooManyDeletions("lokale Google-Kopie ist leer, es wird nichts gelöscht")
    orphans = find_orphans(pathlib.Path(status_db), pathlib.Path(google_dir))
    if len(orphans) > max_deletes:
        raise TooManyDeletions(f"{len(orphans)} Löschungen > Grenze {max_deletes}, abgebrochen")
    for _ident, href in orphans:
        delete_href(href)
    return len(orphans)


def _strato_delete(href: str) -> None:
    base = os.environ.get("STRATO_BASE", "https://dav.webmail.strato.de")
    user = os.environ["STRATO_USER"]
    pw = subprocess.check_output(
        ["security", "find-generic-password", "-s", "vdirsyncer-strato-password", "-w"],
        text=True).strip()
    ctx = ssl.create_default_context(
        cafile=str(pathlib.Path.home() / ".config/vdirsyncer/ca-bundle.pem"))
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = urllib.request.Request(base + href, method="DELETE",
                                 headers={"Authorization": "Basic " + token})
    try:
        urllib.request.urlopen(req, context=ctx)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise


if __name__ == "__main__":
    status = pathlib.Path.home() / ".config/vdirsyncer/status/cal/main.items"
    google = pathlib.Path.home() / ".local/state/calendar-mirror/google/main"
    n = prune(status, google, _strato_delete)
    print(f"prune: {n} Termine in Strato gelöscht")
