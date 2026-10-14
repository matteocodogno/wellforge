---
type: C4 Component
title: quality-node workflow
status: draft
groma:
  id: quality-node-workflow
  parent: quality-gate-workflows
  group: Stack gates
---

Reusable gate for Node and TypeScript packages (frontend or Hono backend): lint with zero warnings, typecheck, Vitest coverage at 80% lines and 70% branches, a production dependency audit, semgrep SAST and a required frozen lockfile.
