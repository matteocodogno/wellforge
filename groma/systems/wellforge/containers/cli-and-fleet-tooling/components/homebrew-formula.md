---
type: C4 Component
title: Homebrew formula
status: draft
groma:
  id: homebrew-formula
  parent: cli-and-fleet-tooling
  group: CLI
---

Formula/wellforge.rb, the tap formula that installs the CLI. Pins the sha256 of the tag tarball, which cannot exist before the tag, so the release flow bumps it in a follow-up step.
