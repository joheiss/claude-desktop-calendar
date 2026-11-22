# Kalender-Spiegel: Google → Strato

Pflegt Termine per Text/Sprache in Claude Desktop (Google-Calendar-Connector) und
spiegelt den Google-Hauptkalender alle 15 Minuten einseitig in einen
Strato-Kalender (CalDAV). Google ist die Quelle, Strato nur der Spiegel.

Hintergrund und Entscheidungen: `docs/superpowers/specs/` (Entwurf) und
`docs/superpowers/plans/` (Plan). Anweisung für Claude Desktop:
`docs/claude-instructions.md`.

## So funktioniert es

```
Claude Desktop ──Connector──▶ Google Calendar ──mirror.sh (alle 15 Min)──▶ Strato
```

`scripts/mirror.sh` macht pro Lauf drei Schritte:
1. **Google-Kopie:** `vdirsyncer` holt den Google-Kalender in eine lokale Ordnerkopie
   (`~/.local/state/calendar-mirror/google/`). Sie dient als Referenzliste.
2. **Spiegel:** `vdirsyncer` überträgt neue und geänderte Termine nach Strato.
3. **Aufräumen:** `scripts/prune_deleted.py` löscht in Strato Termine, die aus Google
   stammen und dort nicht mehr existieren. (Nötig, weil Strato Termine beim Speichern
   umschreibt; `vdirsyncer` allein gibt Löschungen deshalb nicht weiter.)

Ohne Netz wird still übersprungen. Erst nach 24 Stunden ohne Erfolg gibt es eine
macOS-Mitteilung. Andere Fehler melden sich sofort. Protokoll:
`~/Library/Logs/calendar-mirror.log`.

## Verhalten, das man kennen sollte

- **Nur Google → Strato.** In Strato angelegte oder geänderte Termine landen nie in
  Google. Sie bleiben in Strato stehen, bis Google den Termin ändert (dann gewinnt Google).
- **In Strato von Hand gelöschte Termine** werden nicht neu angelegt, bis Google den
  Termin ändert.
- **Aufräumen hat Sicherungen:** Bei mehr als 10 Löschungen auf einmal oder leerer
  Google-Kopie bricht der Lauf ab und meldet den Fehler.
- **Leerer Google-Kalender:** `vdirsyncer` bricht aus Schutz ab, statt alles zu löschen.
- Der Mac muss laufen und angemeldet sein. Verpasste Läufe holt er nach dem Aufwachen nach.

## Einrichtung (neuer Rechner oder Neuaufbau)

Alles Geheime liegt in der macOS-Keychain bzw. unter `~/.config/vdirsyncer/`, nie im Repository.

1. **Werkzeuge:** `brew install uv`, dann `uv tool install "vdirsyncer[google]"`.
2. **Google-Zugang:** Cloud-Projekt mit aktivierter *Google Calendar API* **und** *CalDAV API*,
   OAuth-Client (Desktop-App), Zustimmungsbildschirm auf **„In Produktion"** (sonst läuft
   der Token nach 7 Tagen ab). Dafür braucht Google eine Startseite und eine
   Datenschutzerklärung (`index.html`, `datenschutz.html`, per GitHub Pages).
3. **Keychain-Einträge** (fragen das Geheimnis interaktiv ab, zweimal eingeben):
   ```bash
   security add-generic-password -a "$USER" -s vdirsyncer-google-secret -w
   security add-generic-password -a "$USER" -s vdirsyncer-strato-password -w
   ```
4. **`~/.config/vdirsyncer/real-values.env`** (keine Geheimnisse):
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CAL_ID=...            # meist die Google-Mailadresse
   STRATO_URL=https://dav.webmail.strato.de
   STRATO_USER=...              # Strato-Login (Mailadresse)
   STRATO_CAL_NAME=...          # Kennung des Strato-Terminkalenders
   ```
   Die Kennung findest du mit einer Probe-Konfiguration und `vdirsyncer discover`
   (Strato meldet mehrere Sammlungen, der Terminkalender hat `VEVENT`).
   Strato braucht ein **Business-Postfach** mit CalDAV.
5. **Zertifikatsliste** (das Python in `vdirsyncer` findet sonst keine Systemzertifikate):
   ```bash
   security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain \
     > ~/.config/vdirsyncer/ca-bundle.pem
   ```
6. **Erstanmeldung bei Google und Kollektionen finden** (öffnet den Browser; beim
   Rückfragen „Should vdirsyncer attempt to create it?" für Google/Strato mit `n`,
   für lokale Ordner mit `y` antworten):
   ```bash
   export SSL_CERT_FILE=~/.config/vdirsyncer/ca-bundle.pem
   python3 scripts/build_config.py import real ~/.config/vdirsyncer/config-import
   vdirsyncer -c ~/.config/vdirsyncer/config-import discover cal
   ```
7. **Erstabgleich (einmalig, beidseitig):** Vorher beide Kalender sichern. Nur wenn Strato
   schon Termine enthält, die in Google fehlen und übernommen werden sollen:
   ```bash
   vdirsyncer -c ~/.config/vdirsyncer/config-import sync cal
   ```
8. **Auf Spiegel-Betrieb umstellen** (einmal `discover` pro Konfiguration nötig):
   ```bash
   python3 scripts/build_config.py mirror real ~/.config/vdirsyncer/config-mirror
   yes n | vdirsyncer -c ~/.config/vdirsyncer/config-mirror discover cal
   python3 scripts/build_config.py gcopy real ~/.config/vdirsyncer/config-gcopy
   mkdir -p ~/.local/state/calendar-mirror
   yes y | vdirsyncer -c ~/.config/vdirsyncer/config-gcopy discover gcopy
   vdirsyncer -c ~/.config/vdirsyncer/config-gcopy sync gcopy
   ```
9. **15-Minuten-Job installieren:**
   ```bash
   sed "s|{{MIRROR_SH}}|$PWD/scripts/mirror.sh|; s|{{HOME}}|$HOME|g" \
     launchd/de.joheiss.calendar-mirror.plist.tpl \
     > ~/Library/LaunchAgents/de.joheiss.calendar-mirror.plist
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/de.joheiss.calendar-mirror.plist
   ```
   Wird das Projekt verschoben oder umbenannt: Job neu installieren
   (`launchctl bootout gui/$(id -u)/de.joheiss.calendar-mirror`, dann Schritt 9).
   Umzug des Spiegels auf einen anderen Mac: `docs/umzug-spiegel.md`.

## Claude Desktop

Google-Calendar-Connector verbinden (**alle** Kalenderrechte erlauben, sonst kann Claude
nur lesen). Ein Claude-Projekt anlegen, den Text aus `docs/claude-instructions.md` als
Projektanweisung einfügen und den Connector im Projekt aktivieren.

## Entwickeln und Testen

```bash
uv run --with pytest --with icalendar pytest tests
```

Die Tests nutzen lokale Ordner statt echter Konten.
`build_config.py` setzt die `vdirsyncer`-Konfiguration aus den Bausteinen in `config/` zusammen
(Modi `import`, `mirror`, `gcopy`).

## Fehlersuche

| Symptom | Ursache / Abhilfe |
|---|---|
| `CERTIFICATE_VERIFY_FAILED` | `ca-bundle.pem` fehlt oder alt (Schritt 5), `SSL_CERT_FILE` setzen |
| Google `accessNotConfigured` / `Not Found` | *CalDAV API* im Cloud-Projekt aktivieren |
| Strato `401` | Business-Paket/CalDAV prüfen, Passwort in der Keychain prüfen |
| Strato `Precondition Failed` (412) | Strato lehnt einen niedrigeren `SEQUENCE`-Zähler ab; den Zähler des Termins in Google erhöhen |
| `Detected change in config file` | `vdirsyncer -c <config> discover <pair>` einmal ausführen |
| Meldung nach 24 h Offline | Netz prüfen, Protokoll ansehen |
