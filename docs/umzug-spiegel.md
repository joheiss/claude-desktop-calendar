# Spiegel auf einen anderen Mac umziehen

Wann man das braucht: Der Spiegel Google → Strato (`scripts/mirror.sh`, alle 15 Minuten
per LaunchAgent) soll auf einem anderen Mac laufen, zum Beispiel weil der bisherige Mac
ersetzt wird oder meist ausgeschaltet ist.

**Nicht nötig**, wenn du nur auf mehreren Macs Termine pflegen willst. Dafür reichen
Claude Desktop mit demselben Konto, das Projekt „Kalender" und der Google-Calendar-Connector.
Der Spiegel läuft dann weiter auf dem alten Mac.

## Wichtige Regeln

- Der Spiegel darf **nur auf einem Mac** laufen. Jeder Mac führt seinen eigenen Sync-Stand.
  Auf einem zweiten Mac mit leerem Stand würde `vdirsyncer` alle Termine als „auf beiden
  Seiten geändert" ansehen und sie in Strato neu schreiben. Mit Stratos Versionszähler
  gibt das Fehler (`Precondition Failed`).
- Der **Sync-Stand muss mit umziehen** (Schritt 3). Ohne ihn geht der Umzug nicht sauber.
- Benutzername und Pfade sollten auf dem neuen Mac gleich sein (`/Users/<name>/...`).
  Die Konfigurationsdateien enthalten absolute Pfade.
- Dieser Ablauf wurde noch nicht praktisch getestet. Beim ersten Mal in Ruhe vorgehen und
  vorher beide Kalender sichern (Schritt 0).

## Ablauf

### 0. Sicherung (alter Mac)

Beide Kalender als `.ics` sichern, zum Beispiel mit einem Sync in lokale Ordner
(schreibgeschützt, siehe Abschnitt „Erstabgleich" im `README.md`), oder die Kalender in
Google bzw. im Strato-Webmail exportieren. Erst danach weitermachen.

### 1. Job auf dem alten Mac stoppen

Damit nicht beide Macs gleichzeitig laufen:

```bash
launchctl bootout gui/$(id -u)/de.joheiss.calendar-mirror
```

Prüfen, dass er weg ist:

```bash
launchctl print gui/$(id -u)/de.joheiss.calendar-mirror
```

Erwartet: Fehlermeldung „Could not find service".

### 2. Werkzeuge auf dem neuen Mac installieren

```bash
brew install uv
uv tool install "vdirsyncer[google]"
git clone https://github.com/joheiss/claude-desktop-calendar
```

Die Version prüfen: `vdirsyncer --version`.

### 3. Sync-Stand und Zugänge vom alten Mac kopieren

Diese zwei Ordner vom alten Mac auf den neuen kopieren (gleicher Benutzername, gleicher Pfad),
zum Beispiel per `rsync`, AirDrop oder externe Platte:

- `~/.config/vdirsyncer/` mit Google-Token, Konfigurationen, Sync-Stand (`status/`),
  Zertifikatsliste (`ca-bundle.pem`) und `real-values.env`
- `~/.local/state/calendar-mirror/` mit der lokalen Google-Kopie und dem Stand dazu

Beispiel (vom neuen Mac aus, `ALT` ist der Name oder die Adresse des alten Macs):

```bash
rsync -a ALT:.config/vdirsyncer/ ~/.config/vdirsyncer/
mkdir -p ~/.local/state
rsync -a ALT:.local/state/calendar-mirror/ ~/.local/state/calendar-mirror/
```

Der Google-Token (`google_token`) und `real-values.env` sind persönlich. Die Datei
bitte nicht ins Repository legen und nicht ungesichert versenden.

### 4. Keychain-Einträge neu anlegen

Sie lassen sich nicht einfach kopieren. Das Geheimnis jeweils zweimal eingeben:

```bash
security add-generic-password -a "$USER" -s vdirsyncer-google-secret -w
security add-generic-password -a "$USER" -s vdirsyncer-strato-password -w
```

Prüfen (zeigt nur, ob der Eintrag existiert, nicht den Inhalt):

```bash
security find-generic-password -s vdirsyncer-google-secret | grep svce
security find-generic-password -s vdirsyncer-strato-password | grep svce
```

### 5. Testlauf von Hand

Aus dem geklonten Repository:

```bash
cd claude-desktop-calendar
scripts/mirror.sh
tail -8 ~/Library/Logs/calendar-mirror.log
```

Erwartet: `Syncing gcopy/main`, `Syncing cal/main`, `prune: 0 Termine in Strato gelöscht`,
`exit=0`, und **keine** Zeilen „Copying (updating)" in großer Zahl. Ist der Stand richtig
mitgekommen, bleibt der Lauf ruhig.

Bei einer Zertifikatsmeldung: Zertifikatsliste neu anlegen (siehe `README.md`, Einrichtung
Schritt 5). Bei „Detected change in config file": einmal
`vdirsyncer -c ~/.config/vdirsyncer/config-mirror discover cal` ausführen.

Läuft der Testlauf **nicht** ruhig, also viele Aktualisierungen oder Fehler, den Job nicht
installieren, sondern Ursache klären. Im Zweifel zurück zum alten Mac (Schritt 8).

### 6. Job auf dem neuen Mac installieren

```bash
sed "s|{{MIRROR_SH}}|$PWD/scripts/mirror.sh|; s|{{HOME}}|$HOME|g" \
  launchd/de.joheiss.calendar-mirror.plist.tpl \
  > ~/Library/LaunchAgents/de.joheiss.calendar-mirror.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/de.joheiss.calendar-mirror.plist
```

Prüfen:

```bash
launchctl print gui/$(id -u)/de.joheiss.calendar-mirror | grep -E "run interval|last exit"
```

Erwartet: `run interval = 900 seconds`, `last exit code = 0`.

### 7. Abnahme

Einen Testtermin in Google anlegen (zum Beispiel in einem Gespräch im Projekt „Kalender"),
nach höchstens 15 Minuten prüfen, ob er in Strato steht, dann löschen und prüfen, ob er
in Strato wieder verschwindet.

### 8. Rückweg, falls etwas schiefgeht

Auf dem neuen Mac den Job entfernen:

```bash
launchctl bootout gui/$(id -u)/de.joheiss.calendar-mirror
rm ~/Library/LaunchAgents/de.joheiss.calendar-mirror.plist
```

Auf dem alten Mac den Job wieder installieren (Schritt 6 dort). Der Sync-Stand dort ist
unverändert, solange er dort nicht weiterlief.

### 9. Aufräumen auf dem alten Mac

Wenn der neue Mac eine Weile ruhig läuft: LaunchAgent-Datei auf dem alten Mac löschen
(`rm ~/Library/LaunchAgents/de.joheiss.calendar-mirror.plist`) und die Keychain-Einträge
entfernen (`security delete-generic-password -s vdirsyncer-google-secret` und
`-s vdirsyncer-strato-password`). Das ist nicht rückgängig zu machen.
