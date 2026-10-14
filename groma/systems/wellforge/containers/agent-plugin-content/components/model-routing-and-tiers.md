---
type: C4 Component
title: Model routing and tiers
status: draft
groma:
  id: model-routing-and-tiers
  parent: agent-plugin-content
  group: Plugin config and evals
---

config/model-routing.yml assigns each agent a tool-neutral tier by level of judgment; config/model-tiers.yml resolves a tier to a concrete model per tool and provider. Adapters generate each agent's model from the pair, and check-routing.py verifies it.
