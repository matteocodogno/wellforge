#!/usr/bin/env bash
# Every self-test this repository has, in one command, with one exit code.
#
# WHY THIS EXISTS
# `plugin-v2.49.0` and `cli-v1.5.0` were tagged while post-spec-guard.test.sh had a failure
# and the CLI matrix had six. Nobody weakened a gate; the gates simply were not all run,
# because running them meant remembering nine commands in four directories and each release
# path had its own idea of which ones mattered. A rule that depends on remembering is not
# enforced — which is the thesis this repo applies to the projects it generates, and had not
# applied to itself.
#
# So: one list, one entry point, and the release paths take it as a precondition
# (scripts/release-cli.sh, commands/release.md, docs/VERSIONING.md), plus a pre-push hook
# for tags and a CI release-guard job. Add a new suite HERE and every one of those picks it
# up; that is the whole point of the file.
#
#   scripts/check-all.sh                 # everything that runs without a toolchain
#   scripts/check-all.sh --preset hono-react
#                                        # ...plus that preset's OWN gates on a fresh scaffold
#   scripts/check-all.sh --quick         # skip the slow scaffold/gate work
#
# Exit 0 only when every check passed. Nothing here is advisory.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

PRESET=""
QUICK=0
while [ $# -gt 0 ]; do
  case "$1" in
    --preset) PRESET="${2:-}"; shift 2 ;;
    --preset=*) PRESET="${1#*=}"; shift ;;
    --quick) QUICK=1; shift ;;
    -h|--help)
      sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

# ── reporting ───────────────────────────────────────────────────────────────────────
# Names and outcomes are collected as we go and printed as one table at the end, so a long
# run is readable afterwards rather than only while it scrolls.
NAMES=(); OUTCOMES=(); DETAILS=()
FAILED=0; SKIPPED=0
LOGDIR="$(mktemp -d)"
trap 'rm -rf "$LOGDIR"' EXIT

BOLD=""; RED=""; GRN=""; YLW=""; DIM=""; RST=""
if [ -t 1 ]; then
  BOLD=$'\033[1m'; RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; DIM=$'\033[2m'; RST=$'\033[0m'
fi

record() { NAMES+=("$1"); OUTCOMES+=("$2"); DETAILS+=("${3:-}"); }

# run <name> <command…>
run() {
  local name="$1"; shift
  local slug log
  slug=$(printf '%s' "$name" | tr -c 'A-Za-z0-9._-' '_')
  log="$LOGDIR/$slug.log"
  printf '  %s… ' "$name"
  if "$@" > "$log" 2>&1; then
    printf '%sok%s\n' "$GRN" "$RST"
    record "$name" ok ""
  else
    local rc=$?
    printf '%sFAILED%s (rc=%s)\n' "$RED" "$RST" "$rc"
    # The last few lines are what a reader needs; the full log is printed at the end for
    # failures only, so a green run stays short.
    record "$name" failed "$log"
    FAILED=$((FAILED + 1))
  fi
}

skip() { printf '  %s… %sskipped%s (%s)\n' "$1" "$YLW" "$RST" "$2"; record "$1" skipped "$2"; SKIPPED=$((SKIPPED + 1)); }

have() { command -v "$1" >/dev/null 2>&1; }

# pyyaml is needed by most Python checks. uv is the documented fallback, as in the hooks.
pyrun() {
  if python3 -c "import yaml" >/dev/null 2>&1; then python3 "$@"
  elif have uv; then uv run --quiet --with pyyaml python "$@"
  else return 127
  fi
}

printf '\n%sWellForge self-test%s  %s(%s)%s\n\n' "$BOLD" "$RST" "$DIM" "$ROOT" "$RST"

# ── 1. drift guards ─────────────────────────────────────────────────────────────────
printf '%sguards%s\n' "$BOLD" "$RST"
if python3 -c "import yaml" >/dev/null 2>&1 || have uv; then
  run "check-routing.py" pyrun wellforge-plugin/scripts/check-routing.py --tool claude
  run "check-docs.py"    pyrun wellforge-plugin/scripts/check-docs.py
  run "check-budget.py"  pyrun wellforge-plugin/scripts/check-budget.py
else
  skip "guards (3)" "no python3+pyyaml and no uv"
fi

# ── 2. hook matrices ────────────────────────────────────────────────────────────────
printf '\n%shooks%s\n' "$BOLD" "$RST"
shopt -s nullglob
hook_tests=(wellforge-plugin/hooks/scripts/tests/*.test.sh)
if [ ${#hook_tests[@]} -eq 0 ]; then
  skip "hook matrices" "none found — did the layout move?"
  FAILED=$((FAILED + 1))   # an empty test list is a failure, not a pass
else
  for t in "${hook_tests[@]}"; do run "$(basename "$t")" bash "$t"; done
fi

# ── 3. python suites (plugin + gates) ───────────────────────────────────────────────
printf '\n%spython suites%s\n' "$BOLD" "$RST"
py_tests=(wellforge-plugin/scripts/tests/*.test.py gates/scripts/tests/*.test.py)
if [ ${#py_tests[@]} -eq 0 ]; then
  skip "python suites" "none found — did the layout move?"
  FAILED=$((FAILED + 1))
elif python3 -c "import yaml" >/dev/null 2>&1 || have uv; then
  for t in "${py_tests[@]}"; do run "$(basename "$t")" pyrun "$t"; done
else
  skip "python suites (${#py_tests[@]})" "no python3+pyyaml and no uv"
fi

# ── 3b. the adapter smoke tests ─────────────────────────────────────────────────────
# Not under any tests/ directory, so no glob above reaches them — and that is precisely why
# they were missing from the first version of this file. CI runs them (the `adapter-smoke`
# job) and `release-guard` requires that job, so leaving them out here recreated the exact
# gap this script exists to close: green locally, red on the tag.
printf '\n%sadapters%s\n' "$BOLD" "$RST"
if [ -f adapters/smoke-test.py ]; then
  if python3 -c "import yaml" >/dev/null 2>&1 || have uv; then
    for a in copilot opencode; do
      run "adapter smoke ($a)" pyrun adapters/smoke-test.py --adapter "$a"
    done
  else
    skip "adapter smoke (2)" "no python3+pyyaml and no uv"
  fi
else
  skip "adapter smoke" "adapters/smoke-test.py not found — did the layout move?"
  FAILED=$((FAILED + 1))
fi

# ── 3c. the eval-rubric mirror ──────────────────────────────────────────────────────
# Two byte-identical copies by design (a scaffold has no gates/ on disk, so the plugin
# ships a mirror). CI has a job for it; it costs one `cmp` here, and drift means two
# projects scored against different standards.
printf '\n%smirrors%s\n' "$BOLD" "$RST"
run "eval-rubric mirror" cmp -s gates/configs/eval-rubric.yml wellforge-plugin/config/eval-rubric.yml

# ── 3d. spec fixtures that CI runs ──────────────────────────────────────────────────
if [ -x specs/001-terse-mode/fixtures/run-all.sh ]; then
  run "terse-mode fixtures" specs/001-terse-mode/fixtures/run-all.sh
fi

# ── 4. the CLI matrix ───────────────────────────────────────────────────────────────
printf '\n%sCLI%s\n' "$BOLD" "$RST"
if [ -x scripts/tests/wellforge.test.sh ]; then
  run "wellforge.test.sh" bash scripts/tests/wellforge.test.sh
else
  skip "wellforge.test.sh" "not executable"
  FAILED=$((FAILED + 1))
fi

# ── 5. shellcheck — the SAME file set ci.yml uses ───────────────────────────────────
# Kept identical to the `cli` job's invocation on purpose: two lists that are meant to
# agree, maintained apart, is the failure this whole file exists to stop. If you change one,
# change the other, and the release-guard job compares them.
printf '\n%sshellcheck%s\n' "$BOLD" "$RST"
sc_files=(scripts/wellforge scripts/*.sh scripts/tests/*.sh gates/hooks/*
          wellforge-plugin/hooks/scripts/*.sh wellforge-plugin/hooks/scripts/tests/*.sh)
# `command -v shellcheck` is not enough: mise installs SHIMS on PATH, and a shim for a tool
# with no version selected resolves fine and then dies with "No version is set for shim".
# Ask whether it RUNS.
if shellcheck --version >/dev/null 2>&1; then
  run "shellcheck" shellcheck -s bash --severity=warning -f gcc "${sc_files[@]}"
elif have mise; then
  run "shellcheck (via mise)" mise x shellcheck@latest -- \
    shellcheck -s bash --severity=warning -f gcc "${sc_files[@]}"
else
  skip "shellcheck" "not installed, and no mise to fetch it"
fi
shopt -u nullglob

# ── 6. a generated project's OWN gates ──────────────────────────────────────────────
# The expensive one, and the only check that needs a toolchain. Without a --preset it is
# skipped LOUDLY rather than silently: "the scaffold gates did not run" and "the scaffold
# gates passed" must never look the same in a release decision.
printf '\n%sgenerated project%s\n' "$BOLD" "$RST"
if [ "$QUICK" = "1" ]; then
  skip "generated-gates" "--quick"
elif [ -z "$PRESET" ]; then
  skip "generated-gates" "no --preset given (use --preset spring-kotlin-react|hono-react|pulumi-gcp-ts)"
elif ! have mise; then
  skip "generated-gates ($PRESET)" "mise not installed"
elif ! have uvx && ! have copier; then
  skip "generated-gates ($PRESET)" "neither uvx nor copier installed"
else
  out="$LOGDIR/scaffold"
  copier_cmd=(uvx copier)
  have copier && copier_cmd=(copier)
  if run "scaffold $PRESET" "${copier_cmd[@]}" copy --defaults --vcs-ref HEAD \
        --data "preset=$PRESET" "$ROOT" "$out"; then
    ( cd "$out" && mise trust --all >/dev/null 2>&1 || true )
    # The same task names ci.yml's generated-gates job runs, per preset.
    case "$PRESET" in
      spring-kotlin-react)
        tasks=(frontend:install frontend:lint frontend:test frontend:build
               backend:install backend:lint backend:test backend:build) ;;
      hono-react)   tasks=(install lint test build) ;;
      pulumi-gcp-ts) tasks=(install lint test build) ;;
      *)            tasks=(install lint test build) ;;
    esac
    for t in "${tasks[@]}"; do
      run "$PRESET mise run $t" bash -c "cd '$out' && mise run '$t'"
    done
  fi
fi

# ── summary ─────────────────────────────────────────────────────────────────────────
printf '\n%s%s%s\n' "$BOLD" "──────────────────────────────────────────────────────────────" "$RST"
printf '%s%-44s %s%s\n' "$BOLD" "CHECK" "RESULT" "$RST"
i=0
while [ $i -lt ${#NAMES[@]} ]; do
  case "${OUTCOMES[$i]}" in
    ok)      printf '%-44s %sok%s\n'      "${NAMES[$i]}" "$GRN" "$RST" ;;
    failed)  printf '%-44s %sFAILED%s\n'  "${NAMES[$i]}" "$RED" "$RST" ;;
    skipped) printf '%-44s %sskipped%s %s%s%s\n' "${NAMES[$i]}" "$YLW" "$RST" "$DIM" "${DETAILS[$i]}" "$RST" ;;
  esac
  i=$((i + 1))
done

if [ "$FAILED" -gt 0 ]; then
  printf '\n%sFailing output%s\n' "$BOLD" "$RST"
  i=0
  while [ $i -lt ${#NAMES[@]} ]; do
    if [ "${OUTCOMES[$i]}" = "failed" ] && [ -s "${DETAILS[$i]}" ]; then
      printf '\n%s── %s ──%s\n' "$DIM" "${NAMES[$i]}" "$RST"
      tail -25 "${DETAILS[$i]}" | sed 's/^/    /'
    fi
    i=$((i + 1))
  done
fi

printf '\n'
if [ "$FAILED" -gt 0 ]; then
  printf '%s%d check(s) FAILED%s — this tree must not be tagged.\n' "$RED" "$FAILED" "$RST"
  exit 1
fi
if [ "$SKIPPED" -gt 0 ]; then
  printf '%sall run checks passed, %d skipped%s — a skip is not a pass; see the table above.\n' \
    "$YLW" "$SKIPPED" "$RST"
else
  printf '%sall checks passed%s\n' "$GRN" "$RST"
fi
exit 0
