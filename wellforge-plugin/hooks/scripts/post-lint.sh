#!/bin/bash
# Advisory post-edit formatter hook. Best-effort auto-format after Write/Edit.
# NEVER blocks (never `exit 2`): a missing or misconfigured formatter is an environment
# fact, not a code error — blocking every edit in a brownfield repo (root package.json,
# no prettier/eslint config) is the bug this fixes. Enforcement lives in CI/QE, not here.
# A tool only runs when the project ACTUALLY configures it.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')
[ -z "$FILE" ] && exit 0
[[ "$FILE" != /* ]] && FILE="$PROJECT_DIR/$FILE"
[ ! -f "$FILE" ] && exit 0
EXT="${FILE##*.}"

has_prettier_config() {
  local d="$1"
  ls "$d"/.prettierrc* "$d"/prettier.config.* >/dev/null 2>&1 && return 0
  [ -f "$d/package.json" ] && grep -q '"prettier"[[:space:]]*:' "$d/package.json" && return 0
  return 1
}
has_eslint_config() {
  local d="$1"
  ls "$d"/.eslintrc* "$d"/eslint.config.* >/dev/null 2>&1 && return 0
  [ -f "$d/package.json" ] && grep -q '"eslintConfig"[[:space:]]*:' "$d/package.json" && return 0
  return 1
}

case "$EXT" in
  ts|tsx|js|jsx|json|yaml|yml)
    FRONTEND_DIR="$PROJECT_DIR/frontend"; [ ! -d "$FRONTEND_DIR" ] && FRONTEND_DIR="$PROJECT_DIR"
    command -v pnpm &>/dev/null || exit 0
    cd "$FRONTEND_DIR" || exit 0
    # Prettier: only when the project configures it; failures are advisory, never blocking.
    if has_prettier_config "$FRONTEND_DIR"; then
      pnpm exec prettier --write "$FILE" >/dev/null 2>&1 \
        || echo "post-lint: prettier skipped/failed on $FILE (advisory)" >&2
    fi
    # ESLint: only JS/TS, only when configured; report but do NOT block.
    if [[ "$EXT" == ts* || "$EXT" == js* ]] && has_eslint_config "$FRONTEND_DIR"; then
      OUT=$(pnpm exec eslint --fix "$FILE" 2>&1) \
        || { echo "post-lint: eslint issues in $FILE (advisory, not blocking):" >&2; echo "$OUT" >&2; }
    fi
    ;;
  kt|kts)
    # Walk up to find mvnw (Maven-only project — no Gradle).
    MAVEN_DIR=$(dirname "$FILE")
    while [ "$MAVEN_DIR" != "/" ]; do [ -f "$MAVEN_DIR/mvnw" ] && break; MAVEN_DIR=$(dirname "$MAVEN_DIR"); done
    if [ -f "$MAVEN_DIR/mvnw" ]; then
      (cd "$MAVEN_DIR" && ./mvnw com.github.gantsign.maven:ktlint-maven-plugin:format -q --no-transfer-progress >/dev/null 2>&1) \
        || echo "post-lint: ktlint skipped/failed on $FILE (advisory)" >&2
    elif command -v ktlint &>/dev/null; then
      ktlint --format "$FILE" >/dev/null 2>&1 || true
    fi
    ;;
esac
# SPIKE: config detection is a heuristic (top-level configs + package.json keys); doesn't
# resolve monorepo per-package or eslint flat-config edge cases. Fine for the advisory intent.
exit 0
