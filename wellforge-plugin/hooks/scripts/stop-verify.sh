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
SPECS_CHANGED=$(echo "$CHANGED" | grep -E 'specs/[^/]+/(spec|plan)\.md')
TASKS_CHANGED=$(echo "$CHANGED" | grep -E 'specs/[^/]+/tasks\.md')
if [ -n "$SPECS_CHANGED" ] && [ -z "$TASKS_CHANGED" ]; then
  # Only block if the changed spec dir actually has a tasks.md to drift from
  for f in $SPECS_CHANGED; do
    SPEC_DIR=$(dirname "$f")
    if [ -f "$PROJECT_DIR/$SPEC_DIR/tasks.md" ]; then
      echo "$f changed but $SPEC_DIR/tasks.md not re-synced. Run /wellforge:tasks to sync (drift rule)." >&2
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
CHANGED_TS=$(echo "$CHANGED" | grep -E '\.(ts|tsx)$')
if [ -n "$CHANGED_TS" ] && command -v pnpm >/dev/null 2>&1; then
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
    # `pnpm exec tsc --version` separates "typescript isn't installed here" (advisory) from
    # "the code doesn't compile" (blocking) — both would otherwise be a non-zero exit.
    if ! (cd "$dir" && pnpm exec tsc --version) >/dev/null 2>&1; then
      echo "stop-verify: typescript not available in $dir — type check skipped (advisory)" >&2
      continue
    fi
    if ! TSC_OUT=$( (cd "$dir" && pnpm exec tsc --noEmit) 2>&1 ); then
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
