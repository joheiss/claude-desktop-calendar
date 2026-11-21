# Kalenderpflege per Text/Sprache mit Spiegelung Google → Strato

Stand: 2026-11-21 · Status: Entwurf zur Freigabe

## Absicht (Warum)
Josef will Termine in Claude Desktop per Text und per Sprache pflegen. Google
Calendar ist der Hauptkalender. Der Strato-Kalender soll nur ein Spiegel sein,
nie eine Quelle.

## Ziele
- Termine in Claude Desktop anlegen, ändern, löschen, suchen und auflisten, per
  getipptem oder diktiertem Satz.
- Google-Änderungen erscheinen innerhalb von ca. 15 Minuten in Strato. Das gilt
  auch für Änderungen, die nicht über Claude gemacht werden (z. B. am Handy).
- Neue, geänderte und gelöschte Termine werden gespiegelt, auch Serientermine.

## Nicht-Ziele
- Kein Echtzeit-Abgleich (15 Minuten Verzögerung sind akzeptiert).
- Keine Pflege von Strato als eigenständiger Quelle.
- Keine eigene Oberfläche, keine Einladungs-/Teilnehmerlogik über das hinaus,
  was der Google-Connector ohnehin kann.

## Anti-Ziele (wäre ein Fehlschlag, auch wenn es technisch läuft)
- Ein Termin, der nur in Strato steht, taucht in Google auf oder löscht dort
  etwas.
- Termine werden doppelt angelegt oder gehen still verloren.
- Der Sync fällt unbemerkt aus (abgelaufenes Token, Mac aus).
- Zugangsdaten landen im Chat oder in Dateien, die Claude liest.

## Randbedingungen
- Mac (arm64), Homebrew, Python 3.13 und Node vorhanden. `vdirsyncer` und `uv`
  fehlen noch.
- Zeitzone Europe/Berlin, Sprache Deutsch.
- Passwörter und OAuth-Geheimnisse trägt Josef selbst ein.

## Ansätze (verworfen / gewählt)
- **A. Claude schreibt in beide Kalender (eigener MCP-Server):** schnell, aber
  Änderungen außerhalb von Claude werden nicht gespiegelt, die Kalender laufen
  auseinander. Verworfen.
- **B. Claude nur → Google, `vdirsyncer` spiegelt zeitgesteuert nach Strato:**
  Abgleich aus bewährtem Werkzeug, deckt alle Änderungsquellen ab. **Gewählt**
  von Josef.
- **C. Eigener Sync-Code im MCP-Server:** flexibel, aber Dubletten, Löschungen
  und Serientermine müssten selbst gelöst werden. Verworfen.

## Entwurf (Teile von B)
1. **Claude ↔ Google:** der offizielle Google-Calendar-Connector (im Register
   gefunden, noch nicht verbunden; Tools u. a. create_event, delete_event,
   get_event, list_events, search_events, list_calendars). Josef verbindet ihn
   in Claude Desktop. Dafür ist kein eigener Server nötig. *(Vom Builder zu
   prüfen: ob es ein Tool zum Ändern von Terminen gibt, sonst Löschen+Neu.)*
2. **Sprache:** Die Diktierfunktion von Claude Desktop liefert Text, es wird
   nichts gebaut. Eine kurze Anweisung (Claude-Projekt oder Anweisungen) legt
   Standards fest: Europe/Berlin, deutsche Datumsangaben, Standarddauer 60 Min,
   vor dem Anlegen den verstandenen Termin kurz nennen und bei Unklarheit
   (Uhrzeit, mehrere Treffer beim Löschen) nachfragen.
3. **Spiegelung:** `vdirsyncer` (per Homebrew), Konfiguration unter
   `~/.config/vdirsyncer/`: Google (OAuth) ↔ Strato (CalDAV).
   `conflict_resolution = "a wins"` mit Google als `a`. Ausgeführt per
   `launchd` alle 15 Minuten, bei verpassten Läufen holt es nach dem Aufwachen
   nach. Log in eine Datei, die Claude auf Wunsch prüfen kann.
4. **Zugänge (durch Josef):** Google-Cloud-Projekt mit OAuth-Client für die
   Calendar-API. Die OAuth-Zustimmung muss auf „In Produktion" stehen, sonst
   läuft das Refresh-Token nach 7 Tagen ab und der Sync fällt aus. Strato:
   CalDAV-Adresse und Passwort, direkt in die Konfiguration eingetragen.

## Offene Punkte für den Builder
- **Strikt einseitig?** `vdirsyncer` synchronisiert von Haus aus in beide
  Richtungen. Zu prüfen ist, wie sich das auf „Strato nur Spiegel" abbilden
  lässt (Anti-Ziel 1). Nach dem einmaligen Erstabgleich (siehe unten) gibt es
  nur noch Google als Quelle. Wenn `vdirsyncer` das nicht sauber hergibt:
  kleinen Zusatz bauen, der Strato-eigene Änderungen verwirft oder
  zurücksetzt. Mit Testtermin in beide Richtungen verifizieren.
- Verhalten bei Serienterminen und ganztägigen Terminen testen.
- Erstlauf zuerst mit `discover` und einem Testkalender, nicht gegen echte
  Daten.
- Fehlersignal bei ausgefallenem Sync (z. B. macOS-Benachrichtigung).

## Von Josef entschieden: Umgang mit bestehenden Strato-Terminen
- Der bestehende Strato-Kalender wird weiterverwendet, kein neuer Kalender.
- Er enthält möglicherweise Termine, die in Google fehlen.
- **Weg 1:** Vor dem ersten Lauf wird der Strato-Kalender als `.ics`
  gesichert (Sicherung prüfen, Datei außerhalb des Sync-Ordners ablegen). Der
  erste Abgleich läuft in beide Richtungen, damit alte Strato-Termine nach
  Google übernommen werden. Josef sieht die Termine in Google vorher bzw.
  danach durch (Dubletten, Privates). Danach wird auf strikt einseitig
  Google → Strato umgestellt (siehe offener Punkt oben).
- Der Erstlauf ist zuerst ein Trockenlauf bzw. läuft gegen Testkalender, und
  erst nach Josefs OK gegen die echten Kalender.

## Von mir gesetzt (zum Gegenlesen)
- Offizieller Connector statt eigenem Google-MCP-Server.
- 15-Minuten-Takt über `launchd`, nicht über Cron.
