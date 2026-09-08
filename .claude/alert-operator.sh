#!/usr/bin/env bash
# Operator attention alarm for THIS repository's runbook sessions.
#
# HARNESS, NOT PROTOCOL SURFACE. It is emitted nowhere, imports nothing from
# lib/, and is cited by no protocol document (.claude/readiness-runbook.md §0).
# It is NOT the emitted `decision-required-alarm.sh`: that one ships to
# INSTALLED projects and its `audio_enabled` defaults to false because no
# emitted hook wires a player (upstream P3). This one runs on the operator's
# own machine, for sessions working ON the installer.
#
# WHY A BACKOFF AND NOT A LOOP. An alarm that repeats on a fixed interval is
# either too slow to notice or unbearable while the operator is away. This
# doubles the gap each time from START_S up to MAX_S, so it is insistent for
# the first minute and then settles to a periodic reminder that can be left
# running for hours without becoming noise.
#
# HOW IT STOPS, and the ordering matters:
#   1. A `UserPromptSubmit` hook runs `--stop`. That is the real "keypress":
#      in this environment Claude Code owns the terminal, so a background
#      process cannot read a keystroke without STEALING it from the session.
#      Reading /dev/tty here would eat the operator's own typing.
#   2. OPT-IN ONLY (ALERT_WATCH_TTY=1): /dev/pts/* mtime newer than our start.
#      MEASURED 2026-09-08 AND OFF BY DEFAULT BECAUSE IT DOES NOT WORK HERE:
#      a pts mtime moves on OUTPUT as well as input, so every line this session
#      prints looks identical to the operator typing. Under an agent driving
#      the same terminal the alarm stopped on its own first chime. It remains
#      available for a human-only shell, where it is the classic `w` idle
#      signal, but it must never be the default in this repo.
#   3. `--stop`, or SIGTERM/SIGINT.
#
# Usage:
#   .claude/alert-operator.sh "why the operator is needed" &   # start
#   .claude/alert-operator.sh --stop                           # stop
#   .claude/alert-operator.sh --status
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PIDF="$HERE/.alert-operator.pid"
START_S=${ALERT_START_S:-5}
MAX_S=${ALERT_MAX_S:-300}
SOUND="${ALERT_SOUND:-$HOME/.claude/sounds/decision-required.wav}"
[ -f "$SOUND" ] || SOUND=/usr/share/sounds/freedesktop/stereo/dialog-warning.oga

play_once() {
  # First player that exists wins; a box with none still gets the terminal bell,
  # so the alarm degrades to something rather than to silence.
  for p in paplay pw-play canberra-gtk-play ffplay mpv play aplay; do
    if command -v "$p" >/dev/null 2>&1; then
      case "$p" in
        ffplay) timeout 10 "$p" -nodisp -autoexit -loglevel quiet "$SOUND" >/dev/null 2>&1 ;;
        mpv)    timeout 10 "$p" --really-quiet --no-video "$SOUND" >/dev/null 2>&1 ;;
        *)      timeout 10 "$p" "$SOUND" >/dev/null 2>&1 ;;
      esac
      return 0
    fi
  done
  printf '\a' >&2
}

newest_pts_mtime() {
  local newest=0 m
  for d in /dev/pts/*; do
    [ -c "$d" ] || continue
    m=$(stat -c %Y "$d" 2>/dev/null) || continue
    [ "$m" -gt "$newest" ] && newest=$m
  done
  echo "$newest"
}

case "${1:-}" in
  --stop)
    if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
      kill -TERM "$(cat "$PIDF")" 2>/dev/null
      rm -f "$PIDF"; echo "alert-operator: stopped"
    else
      rm -f "$PIDF"; echo "alert-operator: not running"
    fi
    exit 0 ;;
  --status)
    if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
      echo "alert-operator: RUNNING pid=$(cat "$PIDF")"; exit 0
    fi
    echo "alert-operator: not running"; exit 1 ;;
esac

REASON="${1:-the runbook needs an operator decision}"

# Refuse to double-start. Two alarms interleaving is worse than one, and the
# O_EXCL claim is the same idiom the wrappers use for their task sentinels.
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF" 2>/dev/null)" 2>/dev/null; then
  echo "alert-operator: already running (pid $(cat "$PIDF")); not starting a second" >&2
  exit 1
fi
rm -f "$PIDF"
if ! ( set -C; echo $$ > "$PIDF" ) 2>/dev/null; then
  echo "alert-operator: could not claim $PIDF" >&2; exit 1
fi

cleanup() { rm -f "$PIDF"; exit 0; }
trap cleanup TERM INT EXIT

WATCH_TTY=${ALERT_WATCH_TTY:-0}
BASELINE=$(newest_pts_mtime)
WAIT=$START_S
N=0
echo "alert-operator: started (pid $$) — $REASON" >&2
echo "  stop with: .claude/alert-operator.sh --stop   (or type anything in the terminal)" >&2

while :; do
  N=$((N + 1))
  play_once
  printf 'alert-operator: chime %d — %s (next in %ss)\n' "$N" "$REASON" "$WAIT" >&2

  # Sleep in 1 s slices so terminal activity is noticed promptly rather than
  # only at the end of a 5-minute gap.
  slept=0
  while [ "$slept" -lt "$WAIT" ]; do
    sleep 1; slept=$((slept + 1))
    [ "$WATCH_TTY" = "1" ] || continue
    now=$(newest_pts_mtime)
    if [ "$now" -gt "$BASELINE" ]; then
      echo "alert-operator: terminal activity detected — operator is here, stopping" >&2
      cleanup
    fi
  done
  WAIT=$((WAIT * 2)); [ "$WAIT" -gt "$MAX_S" ] && WAIT=$MAX_S
done
