#!/usr/bin/env bash
# ==============================================================================
# run_tests.sh — run the full EscapeCircuit test suite (backend + frontend)
# with coverage, stream the console output, and print a designed summary.
#
#   ./run_tests.sh            run everything
#   ./run_tests.sh backend    backend (pytest + coverage) only
#   ./run_tests.sh frontend   frontend (vitest + types + lint) only
#
# Exit code is non-zero if any step fails.
# ==============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGDIR="$(mktemp -d)"
trap 'rm -rf "$LOGDIR"' EXIT

# ---- colours (only when attached to a terminal) -----------------------------
if [ -t 1 ]; then
  B=$'\033[1m'; DIM=$'\033[2m'; R=$'\033[0m'
  GRN=$'\033[32m'; RED=$'\033[31m'; YEL=$'\033[33m'; CYN=$'\033[36m'; BLU=$'\033[34m'
else
  B=""; DIM=""; R=""; GRN=""; RED=""; YEL=""; CYN=""; BLU=""
fi
CHECK="✔"; CROSS="✘"; DOTS="…"

banner() {  # $1 = title
  printf '\n%s╭──────────────────────────────────────────────────────────────────╮%s\n' "$CYN" "$R"
  printf '%s│%s %s%-64s%s %s│%s\n' "$CYN" "$R" "$B" "$1" "$R" "$CYN" "$R"
  printf '%s╰──────────────────────────────────────────────────────────────────╯%s\n' "$CYN" "$R"
}

human() {  # $1 = seconds -> "1m 03s" / "42s"
  local s=$1
  if [ "$s" -ge 60 ]; then printf '%dm %02ds' $((s/60)) $((s%60)); else printf '%ds' "$s"; fi
}

# draw a single carriage-return-updated progress bar
draw_bar() {  # $1 pct  $2 done  $3 name
  local pct=$1 done=$2 name=$3 width=28 i filled bar=""
  [ "$pct" -gt 100 ] && pct=100
  filled=$((pct*width/100))
  i=0
  while [ "$i" -lt "$width" ]; do
    if [ "$i" -lt "$filled" ]; then bar="${bar}█"; else bar="${bar}·"; fi
    i=$((i+1))
  done
  printf '\r  %srunning%s [%s%s%s] %3d%%  %s%4d%s  %s%-38.38s%s' \
    "$CYN" "$R" "$GRN" "$bar" "$R" "$pct" "$DIM" "$done" "$R" "$DIM" "$name" "$R"
}

# poll a growing pytest log and render the progress bar until $pid exits
progress_for() {  # $1 logfile  $2 pid
  local log="$1" pid="$2" pct done name
  while kill -0 "$pid" 2>/dev/null; do
    if [ -s "$log" ]; then
      pct=$(grep -oE '\[ *[0-9]+%\]' "$log" 2>/dev/null | tail -1 | grep -oE '[0-9]+')
      done=$(grep -cE '\[ *[0-9]+%\]$' "$log" 2>/dev/null)
      name=$(grep -E '::.* (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)' "$log" 2>/dev/null | tail -1 \
             | sed -E 's/ (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS).*//; s#^.*::##')
      draw_bar "${pct:-0}" "${done:-0}" "${name:-collecting…}"
    fi
    sleep 0.2
  done
  done=$(grep -cE '\[ *[0-9]+%\]$' "$log" 2>/dev/null)
  draw_bar 100 "${done:-0}" "done"
  printf '\n'
}

MODE="${1:-all}"

# results (filled in by the run_* functions)
BE_RUN=0; BE_OK=0; BE_PASS="-"; BE_FAIL="0"; BE_COV="n/a"; BE_TIME=0
FE_RUN=0; FE_OK=0; FE_PASS="-"; FE_COV="n/a"; FE_TIME=0
TYPE_RUN=0; TYPE_OK=0
LINT_RUN=0; LINT_OK=0

# ------------------------------------------------------------------ backend ---
run_backend() {
  BE_RUN=1
  banner "BACKEND  ·  pytest + coverage"
  local log="$LOGDIR/backend.log" start end rc
  start=$(date +%s)
  if [ -t 1 ]; then
    # Run pytest into a log and show a live progress bar (no per-test spam).
    ( cd "$ROOT/src" && python -m pytest --cov=Backend --cov-report=term-missing ) > "$log" 2>&1 &
    local pid=$!
    progress_for "$log" "$pid"
    wait "$pid"; rc=$?
    # Print the parts worth reading (coverage table, warnings, summary, any
    # failures) — the per-test lines are already represented by the bar.
    grep -vE '::.* (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) *\[ *[0-9]+%\]$' "$log"
  else
    # Not a terminal (CI / piped) — stream plainly.
    ( cd "$ROOT/src" && python -m pytest --cov=Backend --cov-report=term-missing ) 2>&1 | tee "$log"
    rc=${PIPESTATUS[0]}
  fi
  end=$(date +%s); BE_TIME=$((end-start))
  [ "$rc" -eq 0 ] && BE_OK=1

  # parse "=== N passed[, M failed] in ... ===" and the coverage TOTAL line
  local summary; summary=$(grep -E "passed|failed|error" "$log" | tail -1)
  BE_PASS=$(printf '%s' "$summary" | grep -oE '[0-9]+ passed'  | grep -oE '[0-9]+' || echo 0)
  BE_FAIL=$(printf '%s' "$summary" | grep -oE '[0-9]+ failed'  | grep -oE '[0-9]+' || echo 0)
  BE_COV=$(grep -E '^TOTAL' "$log" | tail -1 | grep -oE '[0-9]+%' | tail -1 || echo "n/a")
  [ -z "$BE_COV" ] && BE_COV="n/a"
}

# ----------------------------------------------------------------- frontend ---
run_frontend() {
  banner "FRONTEND  ·  vitest"
  local log="$LOGDIR/frontend.log" start end
  FE_RUN=1
  start=$(date +%s)
  if [ -d "$ROOT/apps/nextjs-app/node_modules/@vitest/coverage-v8" ]; then
    ( cd "$ROOT/apps/nextjs-app" && yarn test --coverage ) 2>&1 | tee "$log"
  else
    printf '%s(coverage provider @vitest/coverage-v8 not installed — running without coverage)%s\n' "$DIM" "$R"
    ( cd "$ROOT/apps/nextjs-app" && yarn test ) 2>&1 | tee "$log"
  fi
  local rc=${PIPESTATUS[0]}
  end=$(date +%s); FE_TIME=$((end-start))
  [ "$rc" -eq 0 ] && FE_OK=1
  FE_PASS=$(grep -E '^\s*Tests' "$log" | tail -1 | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo 0)
  local cov; cov=$(grep -E '^All files' "$log" | tail -1 | awk '{print $4}')
  [ -n "${cov:-}" ] && FE_COV="${cov}%"

  banner "FRONTEND  ·  type-check"
  TYPE_RUN=1
  ( cd "$ROOT/apps/nextjs-app" && yarn check-types ) 2>&1 | tee "$LOGDIR/types.log"
  [ "${PIPESTATUS[0]}" -eq 0 ] && TYPE_OK=1

  banner "FRONTEND  ·  lint"
  LINT_RUN=1
  ( cd "$ROOT/apps/nextjs-app" && yarn lint ) 2>&1 | tee "$LOGDIR/lint.log"
  [ "${PIPESTATUS[0]}" -eq 0 ] && LINT_OK=1
}

case "$MODE" in
  backend)  run_backend ;;
  frontend) run_frontend ;;
  all)      run_backend; run_frontend ;;
  *) echo "usage: $0 [all|backend|frontend]"; exit 2 ;;
esac

# -------------------------------------------------------------------- summary --
row() {  # $1 label  $2 ok(0/1, or - to skip status)  $3 detail
  local status
  if   [ "$2" = "-" ]; then status="${DIM}—${R}     "
  elif [ "$2" = "1" ]; then status="${GRN}${CHECK} PASS${R}"
  else                       status="${RED}${CROSS} FAIL${R}"; fi
  printf '  %s│%s %-26s %b   %s%s%s\n' "$BLU" "$R" "$1" "$status" "$DIM" "$3" "$R"
}

printf '\n%s' "$BLU"
printf '═══════════════════════════════ SUMMARY ═══════════════════════════════%s\n' "$R"

if [ "$BE_RUN" = 1 ]; then
  row "Backend  (pytest)"   "$BE_OK"  "$BE_PASS passed · $BE_FAIL failed · cov $BE_COV · $(human "$BE_TIME")"
fi
if [ "$FE_RUN" = 1 ]; then
  row "Frontend (vitest)"   "$FE_OK"  "$FE_PASS passed · $(human "$FE_TIME")"
  row "Frontend type-check" "$TYPE_OK" ""
  row "Frontend lint"       "$LINT_OK" ""
fi

# overall
OVERALL=0
for v in "$BE_RUN:$BE_OK" "$FE_RUN:$FE_OK" "$TYPE_RUN:$TYPE_OK" "$LINT_RUN:$LINT_OK"; do
  run="${v%%:*}"; ok="${v##*:}"
  if [ "$run" = 1 ] && [ "$ok" != 1 ]; then OVERALL=1; fi
done

printf '%s────────────────────────────────────────────────────────────────────%s\n' "$BLU" "$R"
if [ "$OVERALL" = 0 ]; then
  parts=()
  [ "$BE_RUN" = 1 ] && parts+=("backend ($BE_PASS)")
  [ "$FE_RUN" = 1 ] && parts+=("frontend ($FE_PASS)" "types" "lint")
  [ "$BE_RUN" = 1 ] && [ "$BE_COV" != "n/a" ] && parts+=("cov $BE_COV")
  joined=""
  for p in "${parts[@]}"; do
    if [ -z "$joined" ]; then joined="$p"; else joined="$joined · $p"; fi
  done
  printf '  %s%s ALL GREEN%s — %s\n\n' "$B" "$GRN" "$R" "$joined"
else
  printf '  %s%s SOME CHECKS FAILED%s — see the console output above.\n\n' "$B" "$RED" "$R"
fi
exit "$OVERALL"
