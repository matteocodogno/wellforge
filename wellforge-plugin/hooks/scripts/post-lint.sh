#!/bin/bash
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')
[ -z "$FILE" ] && exit 0
[[ "$FILE" != /* ]] && FILE="$PROJECT_DIR/$FILE"
[ ! -f "$FILE" ] && exit 0
EXT="${FILE##*.}"
if [[ "$EXT" == "ts" || "$EXT" == "tsx" ]]; then
  FRONTEND_DIR="$PROJECT_DIR/frontend"
  [ ! -d "$FRONTEND_DIR" ] && FRONTEND_DIR="$PROJECT_DIR"
  if command -v pnpm &>/dev/null && [ -f "$FRONTEND_DIR/package.json" ]; then
    cd "$FRONTEND_DIR" || exit 0
    OUT=$(pnpm exec prettier --write "$FILE" 2>&1)
    [ $? -ne 0 ] && { echo "Prettier failed: $OUT" >&2; exit 2; }
    OUT=$(pnpm exec eslint --fix "$FILE" 2>&1)
    [ $? -ne 0 ] && { echo "ESLint errors in $FILE:" >&2; echo "$OUT" >&2; exit 2; }
  fi
elif [[ "$EXT" == "kt" || "$EXT" == "kts" ]]; then
  # Walk up to find mvnw (Maven-only project — no Gradle)
  MAVEN_DIR=$(dirname "$FILE")
  while [ "$MAVEN_DIR" != "/" ]; do
    [ -f "$MAVEN_DIR/mvnw" ] && break
    MAVEN_DIR=$(dirname "$MAVEN_DIR")
  done
  if [ -f "$MAVEN_DIR/mvnw" ]; then
    cd "$MAVEN_DIR" || exit 0
    OUT=$(./mvnw com.github.gantsign.maven:ktlint-maven-plugin:format -q --no-transfer-progress 2>&1)
    [ $? -ne 0 ] && { echo "ktlint failed on $FILE:" >&2; echo "$OUT" >&2; exit 2; }
  elif command -v ktlint &>/dev/null; then
    ktlint --format "$FILE" 2>/dev/null
  fi
elif [[ "$EXT" == "json" || "$EXT" == "yaml" || "$EXT" == "yml" ]]; then
  command -v pnpm &>/dev/null && pnpm exec prettier --write "$FILE" 2>/dev/null
fi
exit 0
