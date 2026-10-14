---
type: Groma Flow
title: Generate and verify an adapter
groma:
  id: generate-and-verify-an-adapter
---

The smoke test builds an OpenCode adapter the way a release would, which pulls the shared deterministic layer into the generated tree so its references can be checked.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Adapter smoke test](../systems/wellforge/containers/adapter-generators/components/smoke-test.md) | [OpenCode generator](../systems/wellforge/containers/adapter-generators/components/opencode-generate.md) | Run to produce output |
| [OpenCode generator](../systems/wellforge/containers/adapter-generators/components/opencode-generate.md) | [Deterministic layer shipper](../systems/wellforge/containers/adapter-generators/components/deterministic.md) | Reuse repointing and shipping |
| [Deterministic layer shipper](../systems/wellforge/containers/adapter-generators/components/deterministic.md) | [Feature state](../systems/wellforge/containers/plugin-runtime-scripts/components/forge-state.md) | Ship into adapter output |
