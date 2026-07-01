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
  echo "## WellForge specs"
  [ -d "$PROJECT_DIR/specs" ] && for spec in "$PROJECT_DIR/specs"/*/; do
    [ -d "$spec" ] || continue
    echo "### $(basename "$spec")"
    for part in brief spec plan design tasks eval-report; do
      [ -f "$spec/$part.md" ] && echo "- $part: $(wc -l < "$spec/$part.md" | tr -d ' ')L"
    done
  done
} > "$BACKUP_FILE"
echo "Snapshot → $BACKUP_FILE" >&2
exit 0
