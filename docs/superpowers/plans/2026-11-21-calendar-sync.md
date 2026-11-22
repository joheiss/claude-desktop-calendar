# Kalenderpflege mit Spiegel Google → Strato – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Termine per Text/Sprache in Claude Desktop in Google Calendar pflegen und alle 15 Minuten einseitig nach Strato (CalDAV) spiegeln.

**Architecture:** Claude nutzt den offiziellen Google-Calendar-Connector. `vdirsyncer` (Google OAuth → Strato CalDAV) läuft per `launchd` alle 900 s. Einmaliger Erstabgleich in beide Richtungen (Strato-Altbestand nach Google), danach strikt einseitig. Konfiguration wird aus Bausteinen erzeugt, damit die Einseitigkeit gegen lokale Dateispeicher testbar ist, ohne echte Konten.

**Tech Stack:** vdirsyncer (via `uv tool`, Extra `google`), Python 3.13 + pytest (nur Tests/Hilfsskripte), zsh, launchd, macOS Keychain.

**Spec:** `docs/superpowers/specs/2026-11-21-calendar-sync-design.md`

**Hinweis:** Das Projekt ist kein Git-Repository, daher gibt es keine Commit-Schritte. Alle Konfigurationen mit Geheimnissen liegen unter `~/.config/vdirsyncer/`, nie im Projekt.

## Global Constraints

- Google ist die einzige Quelle; Strato ist nur Spiegel (nach dem Erstabgleich).
- Sync-Intervall: 15 Minuten (`StartInterval` 900).
- Zeitzone Europe/Berlin, Sprache Deutsch, Standarddauer 60 Min.
- Der bestehende Strato-Kalender wird weiterverwendet, kein neuer.
- Vor dem Erstabgleich: Strato-Sicherung als `.ics`, geprüft und außerhalb des Sync-Ordners.
- Erstlauf nie ohne Josefs ausdrückliches OK gegen die echten Kalender.
- Passwörter/OAuth-Geheimnisse trägt Josef selbst ein (Keychain); sie erscheinen nie im Chat, in Logs oder Projektdateien.
- Google-OAuth-Zustimmung muss auf „In Produktion" stehen (sonst Token-Ablauf nach 7 Tagen).

## Review Focus

- Serientermine mit geänderter/gelöschter Einzelinstanz: Google-Änderung kommt unverändert in Strato an, keine Dubletten.
- Ganztägige Termine und Termine über die Sommerzeitumstellung: Datum/Uhrzeit in Strato identisch.
- Nur in Strato angelegter oder geänderter Termin: wird nach Google nicht übernommen und in Strato zurückgesetzt/entfernt.
- In Google gelöschter Termin verschwindet in Strato, und Umlaute/Sonderzeichen im Titel bleiben erhalten.
- Sync scheitert (Token abgelaufen, offline): Josef bekommt eine sichtbare Meldung statt stillem Ausfall.

---

## File Structure

- `config/pair-import.cfg`, `config/pair-mirror.cfg` – nur der Pair-Abschnitt (Import beidseitig, Mirror einseitig)
- `config/storages-real.cfg.tpl` – Google- und Strato-Speicher mit Keychain-Abruf, Platzhalter für IDs/URL
- `config/storages-test.cfg.tpl` – zwei `filesystem`-Speicher für Tests
- `scripts/build_config.py` – setzt eine vdirsyncer-Konfiguration zusammen
- `scripts/mirror.sh` – ein Syncdurchlauf mit Log und Fehlermeldung
- `scripts/diff_calendars.py` – listet UIDs, die nur im Strato-Export stehen
- `launchd/de.joheiss.calendar-mirror.plist.tpl` – 15-Minuten-Job
- `docs/claude-instructions.md` – Anweisung für Claude Desktop (Sprache/Standards)
- `tests/test_mirror_semantics.py`, `tests/test_diff_calendars.py`

---

### Task 1: Werkzeuge und Projektgerüst

**Files:**
- Create: Verzeichnisse `config/ scripts/ tests/ launchd/`

**Interfaces:**
- Produces: `vdirsyncer` und `uv` im PATH, `vdirsyncer` mit Google-Unterstützung.

- [ ] **Step 1:** `brew install uv`, dann `uv tool install "vdirsyncer[google]"`.
- [ ] **Step 2:** Verifikation: `vdirsyncer --version` gibt eine Version aus; `uv tool run --from "vdirsyncer[google]" python -c "import aiohttp_oauthlib"` endet ohne Fehler.
- [ ] **Step 3:** Verzeichnisse aus „File Structure" anlegen.

### Task 2: Einseitige Spiegelung festlegen (Test zuerst)

**Files:**
- Create: `config/pair-import.cfg`, `config/pair-mirror.cfg`, `config/storages-test.cfg.tpl`, `scripts/build_config.py`
- Test: `tests/test_mirror_semantics.py`

**Interfaces:**
- Produces: `build_config(mode: str, storages: str, out: pathlib.Path) -> pathlib.Path` – `mode` ist `"import"` oder `"mirror"`, `storages` ist `"real"` oder `"test:<basisverzeichnis>"` (Unterordner `a/` = Google-Seite, `b/` = Strato-Seite, `status/`); schreibt die zusammengesetzte Konfiguration nach `out`, gibt `out` zurück.

- [ ] **Step 1: Failing tests** in `tests/test_mirror_semantics.py`, jeweils mit zwei `.ics`-Ordnern und `vdirsyncer sync` (nach `vdirsyncer discover`), Modus `mirror`:
  - `test_new_item_in_a_appears_in_b`
  - `test_edit_in_a_updates_b` (Titel mit Umlaut „Zahnärztin Müller")
  - `test_delete_in_a_removes_from_b`
  - `test_item_created_only_in_b_never_reaches_a_and_is_reverted_in_b`
  - `test_edit_in_b_is_reverted_and_a_unchanged`
  - `test_recurring_event_with_changed_instance_copied_unchanged` (RRULE + RECURRENCE-ID)
  - `test_allday_event_and_dst_crossing_event_identical` (Europe/Berlin, 2027-03-28)
  - Modus `import`: `test_import_copies_b_only_item_to_a`
- [ ] **Step 2:** `uv run --with pytest pytest tests/test_mirror_semantics.py -v` → FAIL (`build_config` fehlt).
- [ ] **Step 3: Implement `build_config`** in `scripts/build_config.py`. `pair-mirror.cfg` setzt `conflict_resolution = "a wins"`, Google-Seite `read_only = true` mit `partial_sync = "revert"` laut vdirsyncer-Doku; die Doku zu `partial_sync`/`read_only` zuerst lesen und die Optionen so wählen, dass die Tests grün werden. Gelingt strikte Einseitigkeit damit nicht, kleinen Zusatzschritt in `scripts/mirror.sh` vorsehen (Strato-eigene Änderungen verwerfen) und das im Spec unter „Offene Punkte" vermerken.
- [ ] **Step 4:** Dieselbe Pytest-Zeile → PASS (alle Tests).

### Task 3: Zugänge einrichten (Josef führt aus)

**Files:**
- Create: `config/storages-real.cfg.tpl`

**Interfaces:**
- Consumes: `build_config(..., storages="real")` aus Task 2.
- Produces: Keychain-Einträge `vdirsyncer-google-secret`, `vdirsyncer-strato-password`; Datei `~/.config/vdirsyncer/real-values.env` (Google-Client-ID, Google-Kalender-ID, Strato-URL, Strato-Benutzer, Strato-Kalendername).

- [ ] **Step 1:** Josef legt in der Google Cloud Console ein Projekt an, aktiviert die Calendar-API, erstellt einen OAuth-Client (Typ „Desktop") und setzt die Zustimmung auf „In Produktion". Claude gibt die Klickfolge im Chat vor.
- [ ] **Step 2:** Josef trägt Secret und Strato-Passwort selbst ein: `security add-generic-password -a "$USER" -s vdirsyncer-google-secret -w` (fragt interaktiv) und analog `vdirsyncer-strato-password`.
- [ ] **Step 3:** Template so schreiben, dass Geheimnisse nur über `fetch = ["command", "security", "find-generic-password", "-s", "<name>", "-w"]` kommen; `build_config(..., "real")` ersetzt die Platzhalter aus `real-values.env`.
- [ ] **Step 4:** Verifikation (ohne Ausgabe von Geheimnissen): `vdirsyncer -c <generierte-import-config> discover cal` listet den Google-Kalender und den Strato-Kalender; Google fordert dabei einmalig die Browser-Zustimmung an.

### Task 4: Sicherung und Vorschau des Strato-Altbestands

**Files:**
- Create: `scripts/diff_calendars.py`
- Test: `tests/test_diff_calendars.py`

**Interfaces:**
- Produces: `only_in_first(first_dir: pathlib.Path, second_dir: pathlib.Path) -> list[tuple[str, str]]` – liefert `(uid, summary)` aller Termine in `first_dir`, deren UID in `second_dir` fehlt.

- [ ] **Step 1: Failing test** `test_lists_only_uids_missing_in_second` (zwei Ordner mit `.ics`, erwartet genau die fehlende UID samt Titel) und `test_ignores_instance_overrides_of_known_series`.
- [ ] **Step 2:** `uv run --with pytest pytest tests/test_diff_calendars.py -v` → FAIL.
- [ ] **Step 3: Implement `only_in_first`**, Parsing mit `icalendar`-Bibliothek (`uv run --with icalendar`).
- [ ] **Step 4:** Test → PASS.
- [ ] **Step 5:** Strato nach `~/Backups/strato-calendar-2026-11-21/` sichern (vdirsyncer-Pair Strato ↔ lokaler `filesystem`-Speicher), Google ebenso nach `~/Backups/google-calendar-2026-11-21/`. Erwartet: Anzahl `.ics` > 0 und stimmt mit der Anzahl im Strato-Webkalender überein (Josef bestätigt).
- [ ] **Step 6:** `only_in_first(strato_backup, google_backup)` ausgeben und Josef zeigen: „Diese N Termine kämen nach Google." **Stopp: Josefs OK abwarten**, ggf. vorher Altlasten in Strato löschen.

### Task 5: Erstabgleich (beidseitig, einmalig)

**Files:**
- Modify: keine

**Interfaces:**
- Consumes: Konfiguration aus `build_config("import", "real", ...)`.

- [ ] **Step 1:** Nach Josefs OK aus Task 4: `vdirsyncer -c <import-config> sync cal`.
- [ ] **Step 2:** Verifikation: Strato-Einzeltermine (Stichprobe aus der Liste von Task 4) erscheinen in Google; Zahl der Termine in beiden Kalendern gleich (erneuter Export + `only_in_first` in beide Richtungen → leere Listen).

### Task 6: Dauerbetrieb einseitig mit Fehlermeldung

**Files:**
- Create: `scripts/mirror.sh`, `launchd/de.joheiss.calendar-mirror.plist.tpl`

**Interfaces:**
- Consumes: `build_config("mirror", "real", ...)`.
- Produces: `scripts/mirror.sh` (ohne Argumente; Exit 0 bei Erfolg, sonst ≠ 0 plus macOS-Benachrichtigung `osascript -e 'display notification ...'`); Log `~/Library/Logs/calendar-mirror.log`.

- [ ] **Step 1:** `mirror.sh` schreiben: Mirror-Konfiguration erzeugen, `vdirsyncer sync cal` mit Zeitstempel ins Log, bei Fehler Benachrichtigung „Kalender-Sync fehlgeschlagen" mit Hinweis auf das Log.
- [ ] **Step 2:** Verifikation Fehlerfall: Netzwerk aus bzw. falscher Keychain-Name → Benachrichtigung erscheint, Exit-Code ≠ 0.
- [ ] **Step 3:** Verifikation Erfolgsfall und Einseitigkeit: Testtermin in Google anlegen, `mirror.sh` → erscheint in Strato; Testtermin direkt in Strato anlegen, `mirror.sh` → erscheint nicht in Google und ist in Strato entfernt/zurückgesetzt. Testtermine danach löschen.
- [ ] **Step 4:** Plist-Template mit `StartInterval` 900, `RunAtLoad` true, Pfad zu `mirror.sh`; installieren nach `~/Library/LaunchAgents/de.joheiss.calendar-mirror.plist`, `launchctl bootstrap gui/$(id -u) <plist>`.
- [ ] **Step 5:** Verifikation: `launchctl print gui/$(id -u)/de.joheiss.calendar-mirror` zeigt den Job; nach spätestens 15 Minuten steht ein neuer Logeintrag.

### Task 7: Claude Desktop – Connector, Anweisung, Abnahme

**Files:**
- Create: `docs/claude-instructions.md`

**Interfaces:**
- Produces: Text zum Einfügen in ein Claude-Projekt.

- [ ] **Step 1:** Josef verbindet den Google-Calendar-Connector in Claude Desktop (Einstellungen → Connectoren). Prüfen, welche Tools er bietet, insbesondere ob es ein Tool zum Ändern von Terminen gibt (sonst Anweisung: ändern = löschen + neu anlegen, nach Rückfrage).
- [ ] **Step 2:** `docs/claude-instructions.md` auf Deutsch schreiben: Zeitzone Europe/Berlin, deutsche Datumsangaben, Standarddauer 60 Min, vor dem Anlegen den verstandenen Termin nennen, bei Unklarheit (Uhrzeit, mehrere Treffer beim Löschen) nachfragen, Zugriff nur auf den Hauptkalender, Josef kopiert den Text in ein Claude-Projekt.
- [ ] **Step 3:** Abnahme per Text: „Zahnarzt nächsten Dienstag um 15 Uhr" → Termin korrekt in Google; nach ≤ 15 Min auch in Strato.
- [ ] **Step 4:** Abnahme per Diktat mit denselben Sätzen, zusätzlich Ändern, Löschen und „Was steht morgen an?"; nach ≤ 15 Min stimmt Strato überein.

---

## Self-Review

- **Spec-Abdeckung:** Connector/Sprache → Task 7; Spiegelung/Intervall/launchd → Task 6; Zugänge/Produktionsstatus → Task 3; Sicherung, Erstabgleich, Testkalender-Vorsicht → Tasks 4–5; strikt einseitig + Verifikation → Task 2 und 6.3; Fehlersignal → Task 6; Serientermine/Ganztägig → Tests in Task 2.
- **Offene Punkte des Spec:** Strikte Einseitigkeit wird in Task 2 durch Tests entschieden, Fallback beschrieben. Connector-Änderungstool wird in Task 7 geprüft.
- **Abweichung vom Spec:** Statt eines Testkalenders in Strato (wäre ein neuer Kalender) testet Task 2 mit lokalen Dateispeichern; echte Kalender werden erst nach Sicherung und OK angefasst.

---

## Abweichungen bei der Umsetzung (2026-11-22)

- Task 2: `partial_sync = "ignore"` statt `revert`; Strato-eigene Änderungen werden nicht
  zurückgesetzt.
- Task 3/6: Zertifikatsliste (`ca-bundle.pem`, `SSL_CERT_FILE`) war nötig; für Google
  zusätzlich die CalDAV API.
- Task 4/5: Strato-CalDAV erst nach Upgrade auf Business nutzbar.
- Task 6: zusätzlich `scripts/prune_deleted.py` und der Modus `gcopy` in `build_config`
  (Löschungen aus Google an Strato weitergeben); stille Behandlung von Offline-Läufen.
- Task 7: Der Connector bietet `update_event`; die Anweisung in
  `docs/claude-instructions.md` nutzt es direkt.

Details: Abschnitt „Umsetzungsstand" im Entwurf und `README.md`.
