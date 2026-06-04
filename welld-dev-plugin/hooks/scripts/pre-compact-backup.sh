#!/bin/bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
BACKUP_DIR="$PROJECT_DIR/.claude/transcripts"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/session_${CLAUDE_SESSION_ID:-unknown}_${TIMESTAMP}.md"
{
  echo "# Snapshot — $TIMESTAMP | $PROJECT_DIR"
  echo "## Git state"; git -C "$PROJECT_DIR" log --oneline -10 2>/dev/null
  echo "## Modified"; git -C "$PROJECT_DIR" diff --name-only 2>/dev/null
  echo "## cc-sdd specs"
  [ -d "$PROJECT_DIR/specs" ] && for spec in "$PROJECT_DIR/specs"/*/; do
    name=$(basename "$spec")
    echo "### $name"
    [ -f "$spec/requirements.md" ] && echo "- requirements: $(wc -l < "$spec/requirements.md")L"
    [ -f "$spec/design.md" ]       && echo "- design: $(wc -l < "$spec/design.md")L"
    [ -f "$spec/tasks.md" ]        && echo "- tasks: $(wc -l < "$spec/tasks.md")L"
  done
} > "$BACKUP_FILE"
echo "Snapshot → $BACKUP_FILE" >&2
exit 0
