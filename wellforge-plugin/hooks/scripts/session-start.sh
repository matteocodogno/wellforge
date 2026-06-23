#!/bin/bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
echo "=== SESSION CONTEXT ==="
echo "## Git status"
git -C "$PROJECT_DIR" status --short 2>/dev/null || echo "(not a git repo)"
echo ""
echo "## Recent commits"
git -C "$PROJECT_DIR" log --oneline -5 2>/dev/null || echo "(no commits)"
echo ""
echo "## Branch"
git -C "$PROJECT_DIR" branch --show-current 2>/dev/null
echo ""
if [ -f "$PROJECT_DIR/.claude/context/glossary.md" ]; then
  echo "## Domain glossary"
  cat "$PROJECT_DIR/.claude/context/glossary.md"
  echo ""
fi
echo "## Monorepo services"
for dir in "$PROJECT_DIR"/*/; do
  name=$(basename "$dir")
  if [ -f "$dir/pom.xml" ]; then echo "- $name (Kotlin/Spring Boot)"
  elif [ -f "$dir/package.json" ]; then echo "- $name (Node/TypeScript)"
  fi
done
echo "======================="
