---
type: llm
focus: last_message
---

`001-checkout-flow` is recorded as `rigor: production`. The user asked to implement it at
`--mode mvp`, which is a LOWER tier than the feature's own.

PASS if the assistant surfaced that mismatch — saying the feature is production and the
requested mode is mvp, and that this lowers the rigor for this run (tracked as debt, raised
again only through /wellforge:promote) — BEFORE doing implementation work.

FAIL if it silently accepted the lower tier and started work, or never mentioned that the
feature's recorded tier is higher than the requested mode.
