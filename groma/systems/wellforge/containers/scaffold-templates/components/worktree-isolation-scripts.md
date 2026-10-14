---
type: C4 Component
title: Worktree isolation scripts
status: draft
groma:
  id: worktree-isolation-scripts
  parent: scaffold-templates
  group: Generated in every project
---

.wellforge/worktree-id.sh and db-guard.sh, shipped by the two application presets. Derive a per-checkout database name, port and compose project from the checkout path, and refuse to act on another checkout's database (ADR 0002).
