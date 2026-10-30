#!/bin/bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Scope: only WellForge-managed projects (has specs/ or .forge/), else no-op. Enabled at
# user scope the plugin's hooks fire in EVERY repo, and a WellForge hook has no business
# writing files or printing WellForge context into someone's unrelated checkout.
# trace-subagent.sh has always done this; these two did not.
{ [ -d "$PROJECT_DIR/specs" ] || [ -d "$PROJECT_DIR/.forge" ]; } || exit 0

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
