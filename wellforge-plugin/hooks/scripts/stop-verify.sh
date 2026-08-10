#!/bin/bash
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
[ "$(echo "$INPUT" | jq -r '.stop_hook_active // false')" = "true" ] && exit 0

# ── spec drift check (WellForge spec-driven workflow) ────────────────────────────
# spec.md/plan.md changed without re-syncing tasks.md → block (drift rule)
SPECS_CHANGED=$(git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -E 'specs/[^/]+/(spec|plan)\.md')
TASKS_CHANGED=$(git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -E 'specs/[^/]+/tasks\.md')
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
CHANGED_TS=$(git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -E '\.(ts|tsx)$')
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
CHANGED_KOTLIN=$(git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -E '\.(kt|kts)$')
CHANGED_POM=$(git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -E 'pom\.xml$')

if [ -n "$CHANGED_KOTLIN" ] || [ -n "$CHANGED_POM" ]; then
  # Find the Maven root: walk up from the first changed file to find mvnw
  FIRST_CHANGED=$(echo "${CHANGED_KOTLIN}${CHANGED_POM}" | tr ' ' '\n' | head -1)
  MAVEN_DIR="$PROJECT_DIR/$(dirname "$FIRST_CHANGED")"

  # Walk up directory tree to find mvnw
  while [ "$MAVEN_DIR" != "/" ] && [ "$MAVEN_DIR" != "$PROJECT_DIR/.." ]; do
    [ -f "$MAVEN_DIR/mvnw" ] && break
    MAVEN_DIR=$(dirname "$MAVEN_DIR")
  done

  if [ -f "$MAVEN_DIR/mvnw" ]; then
    cd "$MAVEN_DIR" || exit 0
    echo "Running Maven compile check in $MAVEN_DIR..." >&2
    COMPILE_OUT=$(./mvnw clean compile -q --no-transfer-progress 2>&1)
    if [ $? -ne 0 ]; then
      echo "Maven compile failed — fix before finishing:" >&2
      # Show only ERROR lines to keep output readable
      echo "$COMPILE_OUT" | grep -E "^\[ERROR\]|error:|Cannot find|does not exist" | head -30 >&2
      exit 2
    fi
    echo "✓ Maven compile passed" >&2
  elif [ -n "$CHANGED_POM" ]; then
    # pom.xml changed but no mvnw — warn about missing wrapper
    echo "⚠ pom.xml changed but no mvnw found. Run: mvn wrapper:wrapper -N" >&2
  fi
fi

exit 0
