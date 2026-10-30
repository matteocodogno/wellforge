#!/bin/bash
# Stop hook: last check before a session finishes. Blocks (exit 2) on spec drift and on code
# that does not compile.
#
# WHAT IT LOOKS AT — read this before changing a git command here.
# The checks run against everything this branch changed relative to its MERGE BASE, plus the
# staged, unstaged and untracked working tree. A bare `git diff --name-only` (what this used
# to do) sees ONLY unstaged changes, so every dev agent's work was invisible: their standing
# instruction is to commit on completion, which moved their files out of the hook's view. The
# checks therefore passed by seeing nothing — the failure mode that looks exactly like success.
#
# COST — this runs on every Stop. The Maven check must stay cheap and bounded:
#   * no `clean` — recompiling a whole reactor from scratch on every turn is minutes of work
#     to re-derive what is already on disk; incremental `compile` is what catches the error.
#   * a wall-clock budget (see MVN_BUDGET) so a slow build REPORTS as advisory instead of
#     being killed with the hook. A killed hook exits non-2 and silently never blocks, which
#     is strictly worse than a check that says it ran out of time.
#   * hooks.json sets a matching `timeout` for this hook; keep MVN_BUDGET below it.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
[ "$(echo "$INPUT" | jq -r '.stop_hook_active // false')" = "true" ] && exit 0

git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1 || exit 0

MVN_BUDGET="${WELLFORGE_STOP_MVN_BUDGET:-240}"   # seconds, per Maven root

# ── What changed on this branch ─────────────────────────────────────────────────
# Base = merge base with the default branch, preferring the remote (which also catches
# commits made directly on a local main). If we are ON the base with nothing ahead, there is
# no committed range to compare and the working tree alone is the answer.
resolve_base() {
  local ref mb head
  head=$(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null) || return
  for ref in \
      "$(git -C "$PROJECT_DIR" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)" \
      origin/main origin/master main master; do
    [ -z "$ref" ] && continue
    git -C "$PROJECT_DIR" rev-parse --verify --quiet "$ref" >/dev/null 2>&1 || continue
    mb=$(git -C "$PROJECT_DIR" merge-base HEAD "$ref" 2>/dev/null) || continue
    [ "$mb" = "$head" ] && continue          # nothing committed ahead of this ref
    echo "$mb"; return
  done
}

BASE=$(resolve_base)
CHANGED=$(
  {
    [ -n "$BASE" ] && git -C "$PROJECT_DIR" diff --name-only "$BASE" 2>/dev/null
    git -C "$PROJECT_DIR" diff --name-only 2>/dev/null            # unstaged
    git -C "$PROJECT_DIR" diff --name-only --cached 2>/dev/null   # staged
    git -C "$PROJECT_DIR" ls-files --others --exclude-standard 2>/dev/null  # untracked
  } | sort -u
)
[ -z "$CHANGED" ] && exit 0

# ── Spec drift check (WellForge spec-driven workflow) ───────────────────────────
# spec.md/plan.md changed without re-syncing tasks.md → block (drift rule)
#
# ...unless the change is BOOKKEEPING. /wellforge:done writes `status: done` + `done:` into
# spec.md as its last step and /wellforge:promote writes `rigor:`; neither changes what the
# feature asks for, and tasks.md is rightly untouched. Without this exemption the hook
# blocked every close in a git project and told the user to re-run /wellforge:tasks for a
# status change — while forge-state.py, asked the same question, answered "no drift".
# The rule and the field list are forge-state.py's (LIFECYCLE_FIELDS / change_class), kept
# identical by case 18 of tests/stop-verify.test.sh: body identical, and only these
# top-level frontmatter fields differ.
LIFECYCLE_FIELDS="status|done|approved|superseded_by|archive_reason|rigor|plugin"

# Print a spec with its lifecycle frontmatter lines removed. Only lines INSIDE the leading
# `---` block count: `status: done` typed into the body is a body change.
strip_lifecycle() {
  awk -v re="^(${LIFECYCLE_FIELDS}):" '
    NR == 1 && $0 == "---" { fm = 1; print; next }
    fm == 1 && $0 == "---" { fm = 2; print; next }
    fm == 1 && $0 ~ re     { next }
    { print }'
}

# lifecycle_only <repo-relative path> → 0 when the file differs from its baseline ONLY in
# lifecycle fields. Baseline = the merge base when the branch has commits ahead (the drift
# check spans the branch), else HEAD. No baseline version → a new file → not exempt.
lifecycle_only() {
  local f="$1" ref="${BASE:-HEAD}" old new
  [ -f "$PROJECT_DIR/$f" ] || return 1
  old=$(git -C "$PROJECT_DIR" show "$ref:$f" 2>/dev/null) || return 1
  old=$(printf '%s\n' "$old" | strip_lifecycle)
  new=$(strip_lifecycle < "$PROJECT_DIR/$f")
  [ "$old" = "$new" ]
}

SPECS_CHANGED=$(
  echo "$CHANGED" | grep -E 'specs/[^/]+/(spec|plan)\.md' | while IFS= read -r f; do
    [ -z "$f" ] && continue
    lifecycle_only "$f" || echo "$f"
  done
)
TASKS_CHANGED=$(echo "$CHANGED" | grep -E 'specs/[^/]+/tasks\.md')
if [ -n "$SPECS_CHANGED" ] && [ -z "$TASKS_CHANGED" ]; then
  # Only block if the changed spec dir actually has a tasks.md to drift from
  for f in $SPECS_CHANGED; do
    SPEC_DIR=$(dirname "$f")
    if [ -f "$PROJECT_DIR/$SPEC_DIR/tasks.md" ]; then
      SLUG=$(basename "$SPEC_DIR")
      echo "Drift: $f changed but $SPEC_DIR/tasks.md was not re-synced." >&2
      echo "  Fix:      /wellforge:tasks $SLUG   (re-sync mode — preserves checked tasks)" >&2
      # The surprise this message exists to defuse: the check spans the BRANCH, not just
      # uncommitted work, so the spec edit may be several commits back and feel unrelated
      # to the turn being blocked.
      if [ -n "$BASE" ]; then
        echo "  Why now:  the drift check covers every change on this branch since ${BASE:0:8}," >&2
        echo "            not just uncommitted edits — this may be an earlier commit." >&2
      fi
      echo "  Note:     a re-sync that finds nothing to change still stamps \`synced:\` in" >&2
      echo "            tasks.md, which is what clears this. A cosmetic spec edit is still" >&2
      echo "            a spec edit: the rule is that the task list was RE-CHECKED, not" >&2
      echo "            that it had to change." >&2
      exit 2
    fi
  done
fi

# ── TypeScript compile check ─────────────────────────────────────────────────
# Monorepo-aware: for each changed .ts/.tsx file walk UP to the nearest directory holding BOTH
# a package.json and a tsconfig.json — that is the real compile unit. Never assume `frontend/`
# or the repo root: lerna/pnpm/nx workspaces routinely have a root package.json with no
# tsconfig and no typescript dep (tooling only), so the old fallback ran `tsc` where it cannot
# exist and blocked EVERY turn touching a .ts file.
# Blocks only on genuine type errors; a missing/unrunnable tsc is an environment fact → advisory.
#
# THIS CHECK MUST NEVER WRITE TO THE PROJECT. It used to run `pnpm exec tsc` everywhere, and in
# a Bun- or npm-managed directory pnpm created pnpm-lock.yaml + pnpm-workspace.yaml and
# reinstalled node_modules from the package.json RANGES, ignoring the real lockfile — newer
# dependencies than production pins, a type error that exists nowhere else, and stray lockfiles
# that got committed. So: the local binary first (no package manager involved, nothing to
# install), then the package manager the directory actually uses, with no-install flags.

# ts_pm <dir> — the package manager that owns <dir>: nearest lockfile walking up to the project
# root (a monorepo keeps its lockfile at the root), then package.json's `packageManager` field.
# Prints bun|pnpm|npm|yarn, or nothing.
ts_pm() {
  local d="$1" pm
  while :; do
    if   [ -f "$d/bun.lock" ] || [ -f "$d/bun.lockb" ]; then echo bun;  return
    elif [ -f "$d/pnpm-lock.yaml" ];                     then echo pnpm; return
    elif [ -f "$d/package-lock.json" ];                  then echo npm;  return
    elif [ -f "$d/yarn.lock" ];                          then echo yarn; return
    fi
    [ "$d" = "$PROJECT_DIR" ] || [ "$d" = "/" ] && break
    d=$(dirname "$d")
  done
  pm=$(sed -n 's/.*"packageManager"[[:space:]]*:[[:space:]]*"\([a-z]*\)@.*/\1/p' "$1/package.json" 2>/dev/null | head -1)
  case "$pm" in bun|pnpm|npm|yarn) echo "$pm" ;; esac
}

# ts_local_tsc <dir> — an installed tsc: <dir>/node_modules/.bin first, then hoisted ones above.
ts_local_tsc() {
  local d="$1"
  while :; do
    [ -x "$d/node_modules/.bin/tsc" ] && { echo "$d/node_modules/.bin/tsc"; return; }
    [ "$d" = "$PROJECT_DIR" ] || [ "$d" = "/" ] && break
    d=$(dirname "$d")
  done
}

# ts_check <dir> — sets TSC_OUT. Returns 0 clean, 1 type errors, 2 cannot run (TS_WHY says why).
ts_check() {
  local dir="$1" pm tsc rc
  pm=$(ts_pm "$dir"); tsc=$(ts_local_tsc "$dir"); TS_WHY=""; TSC_OUT=""
  if [ -n "$tsc" ]; then
    if ! (cd "$dir" && "$tsc" --version) >/dev/null 2>&1; then
      TS_WHY="$tsc does not run"; return 2
    fi
    # A project `typecheck` script may pass flags we cannot guess (-b, -p tsconfig.x.json).
    # Only through a package manager that is actually installed; otherwise the binary itself.
    if [ -n "$pm" ] && command -v "$pm" >/dev/null 2>&1 \
       && grep -qE '"typecheck"[[:space:]]*:' "$dir/package.json" 2>/dev/null; then
      case "$pm" in
        npm) TSC_OUT=$( (cd "$dir" && npm run --silent typecheck) 2>&1 ); rc=$? ;;
        *)   TSC_OUT=$( (cd "$dir" && "$pm" run typecheck) 2>&1 );         rc=$? ;;
      esac
    else
      TSC_OUT=$( (cd "$dir" && "$tsc" --noEmit) 2>&1 ); rc=$?
    fi
    [ "$rc" -eq 0 ] && return 0 || return 1
  fi
  # No installed tsc. Ask the owning package manager, never letting it fetch anything (yarn PnP
  # has no node_modules, which is the one case this is for).
  if [ -z "$pm" ]; then TS_WHY="no installed typescript and no package manager detected"; return 2; fi
  if ! command -v "$pm" >/dev/null 2>&1; then TS_WHY="$pm is not installed"; return 2; fi
  local -a run
  case "$pm" in
    bun)  run=(bun x --no-install tsc) ;;
    pnpm) run=(env npm_config_verify_deps_before_run=false pnpm exec tsc) ;;
    npm)  run=(npx --no-install tsc) ;;
    yarn) run=(yarn tsc) ;;
  esac
  if ! (cd "$dir" && "${run[@]}" --version) >/dev/null 2>&1; then
    TS_WHY="typescript not available via $pm"; return 2
  fi
  TSC_OUT=$( (cd "$dir" && "${run[@]}" --noEmit) 2>&1 ) && return 0
  return 1
}

CHANGED_TS=$(echo "$CHANGED" | grep -E '\.(ts|tsx)$')
if [ -n "$CHANGED_TS" ]; then
  TS_DIRS=""
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    d="$PROJECT_DIR/$(dirname "$f")"
    while [ "$d" != "/" ]; do
      if [ -f "$d/tsconfig.json" ] && [ -f "$d/package.json" ]; then
        case "$TS_DIRS" in
          *"|$d|"*) ;;
          *) TS_DIRS="$TS_DIRS|$d|"$'\n' ;;
        esac
        break
      fi
      [ "$d" = "$PROJECT_DIR" ] && break
      d=$(dirname "$d")
    done
  done <<< "$CHANGED_TS"

  if [ -z "$TS_DIRS" ]; then
    echo "stop-verify: no tsconfig.json found above the changed .ts files — type check skipped (advisory)" >&2
  fi
  while IFS= read -r marked; do
    [ -z "$marked" ] && continue
    dir="${marked#|}"; dir="${dir%|}"
    # "typescript isn't installed here" (advisory) vs "the code doesn't compile" (blocking):
    # both would otherwise be a non-zero exit.
    ts_check "$dir"; rc=$?
    if [ "$rc" -eq 2 ]; then
      echo "stop-verify: $TS_WHY in $dir — type check skipped (advisory)" >&2
    elif [ "$rc" -eq 1 ]; then
      echo "TypeScript errors in $dir — fix before finishing:" >&2
      echo "$TSC_OUT" | head -20 >&2
      exit 2
    fi
  done <<< "$TS_DIRS"
fi

# ── Kotlin/Maven compile check ───────────────────────────────────────────────
# EVERY Maven root with a changed file is compiled, not just the one holding the first changed
# file: a repo with two reactors (service-a/mvnw, service-b/mvnw) left the second unchecked.
CHANGED_MVN=$(echo "$CHANGED" | grep -E '\.(kt|kts)$|(^|/)pom\.xml$')
if [ -n "$CHANGED_MVN" ]; then
  MVN_DIRS=""
  NO_WRAPPER=""
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    d="$PROJECT_DIR/$(dirname "$f")"
    while [ "$d" != "/" ]; do
      if [ -f "$d/mvnw" ]; then
        case "$MVN_DIRS" in
          *"|$d|"*) ;;
          *) MVN_DIRS="$MVN_DIRS|$d|"$'\n' ;;
        esac
        break
      fi
      [ "$d" = "$PROJECT_DIR" ] && { NO_WRAPPER=1; break; }
      d=$(dirname "$d")
    done
  done <<< "$CHANGED_MVN"

  if [ -z "$MVN_DIRS" ] && [ -n "$NO_WRAPPER" ] && echo "$CHANGED_MVN" | grep -qE '(^|/)pom\.xml$'; then
    echo "⚠ pom.xml changed but no mvnw found. Run: mvn wrapper:wrapper -N" >&2
  fi

  # `timeout` is GNU coreutils; macOS ships it only as gtimeout (brew coreutils). Without
  # either, run unbounded and let hooks.json's timeout be the only backstop.
  TIMEOUT_BIN=$(command -v timeout || command -v gtimeout)

  while IFS= read -r marked; do
    [ -z "$marked" ] && continue
    dir="${marked#|}"; dir="${dir%|}"
    echo "Running Maven compile check in $dir..." >&2
    if [ -n "$TIMEOUT_BIN" ]; then
      COMPILE_OUT=$( (cd "$dir" && "$TIMEOUT_BIN" "$MVN_BUDGET" ./mvnw compile -q --no-transfer-progress) 2>&1 )
    else
      COMPILE_OUT=$( (cd "$dir" && ./mvnw compile -q --no-transfer-progress) 2>&1 )
    fi
    RC=$?
    if [ "$RC" -eq 124 ]; then
      # Out of budget. Say so loudly: an unreported timeout is a check that silently passed.
      echo "stop-verify: Maven compile in $dir exceeded ${MVN_BUDGET}s — NOT verified (advisory)." >&2
      echo "  Run it yourself: (cd $dir && ./mvnw compile)" >&2
      continue
    fi
    if [ "$RC" -ne 0 ]; then
      echo "Maven compile failed in $dir — fix before finishing:" >&2
      echo "$COMPILE_OUT" | grep -E "^\[ERROR\]|error:|Cannot find|does not exist" | head -30 >&2
      exit 2
    fi
    echo "✓ Maven compile passed ($dir)" >&2
  done <<< "$MVN_DIRS"
fi

exit 0
