#!/usr/bin/env bash
# STAND-IN for the D2 spec gate (WP3 live-run pilot). NOT product code.
# Agent commits only (CLAUDECODE=1). Reads the staged set. Refuses a staged
# path under PREFIXES that no task file's Files: list names, either exactly
# or by a directory entry ending in "/". The refusal names the task to edit.
# [WP3 fix1 H6] Task files are read from the INDEX, as spec-check.sh reads
# them: an unstaged edit to a task file does not count.
[ "${CLAUDECODE:-}" = "1" ] || exit 0
top=$(git rev-parse --show-toplevel) || exit 0
cd "$top" || exit 0
SPECS=".claude/specs"
PREFIXES="src/ lib/ app/ test/ tests/"
log="$(git rev-parse --git-common-dir)/standin-gate.log"
tasks=$(git -c core.quotePath=false ls-files -- "$SPECS/*/tasks/*.md")
listed=$(while IFS= read -r t; do [ -n "$t" ] && git show ":$t" && echo; done <<< "$tasks" |
  awk '/^Files:[[:space:]]*$/{f=1;next} f&&/^[[:space:]]*- /{sub(/^[[:space:]]*- +/,"");gsub(/`/,"");sub(/[[:space:]].*/,"");print;next} {f=0}')
missing=""
while IFS= read -r p; do
  [ -n "$p" ] || continue
  enf=0; for x in $PREFIXES; do case "$p" in "$x"*) enf=1 ;; esac; done
  [ "$enf" = 1 ] || continue
  ok=0
  while IFS= read -r e; do
    case "$e" in "") ;; */) case "$p" in "$e"*) ok=1 ;; esac ;; *) [ "$p" = "$e" ] && ok=1 ;; esac
  done <<< "$listed"
  [ "$ok" = 1 ] || missing="$missing
  $p"
done <<< "$(git -c core.quotePath=false diff --cached --name-only)"
task=$(while IFS= read -r t; do [ -n "$t" ] && git show ":$t" | grep -q '^status: in-progress' && { echo "$t"; break; }; done <<< "$tasks")
[ -n "$task" ] || task="$SPECS/<slug>/tasks/<id>.md"
stamp="$(date -u +%FT%TZ) $(basename "$0")"
if [ -z "$missing" ]; then echo "$stamp pass" >> "$log"; exit 0; fi
echo "$stamp BLOCK$(echo $missing | sed 's/^/ /')" >> "$log"
printf 'spec-gate: commit refused. These staged files are not listed in any task'"'"'s Files: list:%s\n' "$missing" >&2
printf 'Add each path (or its directory, ending in /) to the Files: list in %s,\nthen stage that file and commit again.\n' "$task" >&2
exit 1
