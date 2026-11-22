#!/bin/zsh
# Ein Spiegel-Durchlauf Google -> Strato. Meldet Fehler per macOS-Benachrichtigung.
# Ohne Netz wird still übersprungen; erst nach 24 h ohne Erfolg gibt es eine Meldung.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin"
export SSL_CERT_FILE="$HOME/.config/vdirsyncer/ca-bundle.pem"
LOG="$HOME/Library/Logs/calendar-mirror.log"
CFG="$HOME/.config/vdirsyncer/config-mirror"
CFG_GC="$HOME/.config/vdirsyncer/config-gcopy"
STATE="$HOME/.local/state/calendar-mirror"
DIR="${0:A:h:h}"

notify_fail() {
  if [ -n "$NOTIFY_CMD" ]; then
    "$NOTIFY_CMD" "$1"
  else
    osascript -e "display notification \"$1 – Details: ~/Library/Logs/calendar-mirror.log\" with title \"Kalender-Sync fehlgeschlagen\""
  fi
}

fail() { echo "FEHLER: $1"; notify_fail "$1"; exit 1; }

mkdir -p "$STATE"
{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
  if ! curl -s -m 8 -o /dev/null "${MIRROR_NET_URL:-https://www.googleapis.com}"; then
    echo "offline – Lauf übersprungen"
    if [ -f "$STATE/last-success" ] && [ -n "$(find "$STATE/last-success" -mmin +1440)" ]; then
      notify_fail "Seit über 24 Stunden kein erfolgreicher Sync (offline)"
    fi
    exit 0
  fi
  python3 "$DIR/scripts/build_config.py" mirror real "$CFG" || fail "Konfiguration (mirror)"
  python3 "$DIR/scripts/build_config.py" gcopy real "$CFG_GC" || fail "Konfiguration (gcopy)"
  # 1) lokale Referenzkopie des Google-Kalenders
  vdirsyncer -c "$CFG_GC" sync gcopy || fail "Google-Kopie (vdirsyncer)"
  # 2) Spiegel Google -> Strato (neu, geändert)
  vdirsyncer -c "$CFG" sync cal || fail "Spiegel Google nach Strato (vdirsyncer)"
  # 3) Löschungen aus Google nach Strato weitergeben
  export STRATO_USER="$(sed -n 's/^STRATO_USER=//p' "$HOME/.config/vdirsyncer/real-values.env")"
  uv run --quiet --with icalendar python "$DIR/scripts/prune_deleted.py" || fail "Löschungen weitergeben (prune)"
  touch "$STATE/last-success"
  echo "exit=0"
} >> "$LOG" 2>&1
