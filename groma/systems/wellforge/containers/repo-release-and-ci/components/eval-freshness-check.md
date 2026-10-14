---
type: C4 Component
title: Eval freshness check
status: draft
groma:
  id: eval-freshness-check
  parent: repo-release-and-ci
  group: Self-verification
---

scripts/check-evals-fresh.sh refuses a plugin tag whose prompt layer changed since the last recorded eval pass. The prompt evals are optional in CI because they need an API key, so the check sits on the release path.
