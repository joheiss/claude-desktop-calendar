# SDD ledger — plan: docs/superpowers/plans/2026-11-21-calendar-sync.md
Pre-flight: Task 2 produces build_config, consumed by Tasks 3,5,6 (signature build_config(mode, storages, out)); Task 4 only_in_first standalone. No conflicts.
Note: Projekt ist kein Git-Repo, daher kein sdd-workspace/task-start/Commits; Ledger manuell.
Task 1: complete (uv 0.13.9, vdirsyncer 0.21.0 mit google extra; verifiziert via --version und import aiohttp_oauthlib)
Task 2: complete (tests: uv run --with pytest pytest tests → 9 passed; build_config deckt test+real ab)
Task 2: Ruling: vdirsyncer partial_sync="revert" + read_only auf Google-Seite verhindert jeden Schreibzugriff nach Google (verifiziert per Test), entfernt/revertiert Strato-eigene Termine/Änderungen aber NICHT; sie bleiben in Strato bis Google den Termin ändert (dann gewinnt Google). — Spec-Anti-Ziel (nichts landet in Google) ist erfüllt, zusätzlicher Verwerf-Code wäre YAGNI — Kosten bei Fehleinschätzung: Strato kann Zusatztermine zeigen, die Google nicht hat.
Task 2: Ruling: Löschen des letzten Termins in Google lässt vdirsyncer abbrechen (Sicherung "Storage emptied"); bleibt so, löst die Fehlermeldung aus Task 6 aus. — Schutz vor Totalverlust — Kosten: leerer Google-Kalender wird nicht gespiegelt.
Task 3 (vorbereitet): storages-real.cfg.tpl + build_config real getestet; wartet auf Josefs Zugänge
Task 4 (Teil): diff_calendars only_in_first implementiert, tests: uv run --with pytest --with icalendar pytest tests → alle grün; Sicherung/Vorschau wartet auf Zugänge
