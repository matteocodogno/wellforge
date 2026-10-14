---
type: C4 Component
title: Hook post-spec-guard
status: draft
groma:
  id: hook-post-spec-guard
  parent: agent-plugin-content
  group: Hooks
---

PostToolUse hook on Write|Edit|MultiEdit|NotebookEdit. PostToolUse guard — the lifecycle rules that were only ever prompt promises. Every command was rewritten so that ONLY /wellforge:done writes `status: done` and ONLY /wellforge:promote raises `rigor:`. Nothing enforced it: one Edit to a spec's frontmatter flips either field, and the "single guarded place" stops being single the first time anyone (model or human) takes the shortcut.
