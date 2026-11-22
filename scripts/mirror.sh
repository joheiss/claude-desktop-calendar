#!/bin/zsh
# Ein Spiegel-Durchlauf Google -> Strato. Meldet Fehler per macOS-Benachrichtigung.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin"
export SSL_CERT_FILE="$HOME/.config/vdirsyncer/ca-bundle.pem"
LOG="$HOME/Library/Logs/calendar-mirror.log"
CFG="$HOME/.config/vdirsyncer/config-mirror"
CFG_GC="$HOME/.config/vdirsyncer/config-gcopy"
DIR="${0:A:h:h}"

notify_fail() {
  osascript -e "display notification \"$1 – Details: ~/Library/Logs/calendar-mirror.log\" with title \"Kalender-Sync fehlgeschlagen\""
}

fail() { echo "FEHLER: $1"; notify_fail "$1"; exit 1; }

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
  python3 "$DIR/scripts/build_config.py" mirror real "$CFG" || fail "Konfiguration (mirror)"
  python3 "$DIR/scripts/build_config.py" gcopy real "$CFG_GC" || fail "Konfiguration (gcopy)"
  # 1) lokale Referenzkopie des Google-Kalenders
  vdirsyncer -c "$CFG_GC" sync gcopy || fail "Google-Kopie (vdirsyncer)"
  # 2) Spiegel Google -> Strato (neu, geändert)
  vdirsyncer -c "$CFG" sync cal || fail "Spiegel Google nach Strato (vdirsyncer)"
  # 3) Löschungen aus Google nach Strato weitergeben
  export STRATO_USER="$(sed -n 's/^STRATO_USER=//p' "$HOME/.config/vdirsyncer/real-values.env")"
  uv run --quiet --with icalendar python "$DIR/scripts/prune_deleted.py" || fail "Löschungen weitergeben (prune)"
  echo "exit=0"
} >> "$LOG" 2>&1
