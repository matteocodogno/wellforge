---
type: C4 Component
title: Skill worktree-isolation
status: draft
groma:
  id: skill-worktree-isolation
  parent: agent-plugin-content
  group: Skills
---

WellForge parallel-safety discipline — what a git worktree isolates, what it does NOT, and the preflight before dispatching a parallel batch. Use whenever ≥2 dependency-independent agents are about to be dispatched (`/wellforge:implement` Step 3, `/wellforge:orchestrate` implementation stages), whenever an agent in a worktree hits a failure it cannot explain, and whenever deciding if a batch is safe to parallelize…
