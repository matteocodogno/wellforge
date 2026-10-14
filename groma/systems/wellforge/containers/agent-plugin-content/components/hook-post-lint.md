---
type: C4 Component
title: Hook post-lint
status: draft
groma:
  id: hook-post-lint
  parent: agent-plugin-content
  group: Hooks
---

PostToolUse hook on Write|Edit|MultiEdit|NotebookEdit. Advisory post-edit formatter hook. Best-effort auto-format after Write/Edit. NEVER blocks (never `exit 2`): a missing or misconfigured formatter is an environment fact, not a code error — blocking every edit in a brownfield repo (root package.json, no prettier/eslint config) is the bug this fixes. Enforcement lives in CI/QE, not here. A tool only runs when the project ACTUALLY configures it.
