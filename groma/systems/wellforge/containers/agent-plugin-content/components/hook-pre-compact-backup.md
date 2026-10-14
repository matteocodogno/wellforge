---
type: C4 Component
title: Hook pre-compact-backup
status: draft
groma:
  id: hook-pre-compact-backup
  parent: agent-plugin-content
  group: Hooks
---

PreCompact hook. Scope: only WellForge-managed projects (has specs/ or .forge/), else no-op. Enabled at user scope the plugin's hooks fire in EVERY repo, and a WellForge hook has no business writing files or printing WellForge context into someone's unrelated checkout. trace-subagent.sh has always done this; these two did not.
