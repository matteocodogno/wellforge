---
type: Groma Flow
title: Judge a feature in CI
groma:
  id: judge-a-feature-in-ci
---

CI runs the opt-in eval gate, which scores the feature against the central rubric with an LM judge.

## Steps

| From | To | Action |
| --- | --- | --- |
| [GitHub Actions](../externals/github-actions.md) | [Quality gate scripts](../systems/wellforge/containers/gate-scripts/container.md) | Runs |
| [Quality gate scripts](../systems/wellforge/containers/gate-scripts/container.md) | [Anthropic API](../externals/anthropic-api.md) | Calls as judge |
