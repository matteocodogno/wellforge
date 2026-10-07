---
type: regex
pattern: "## Open questions[\\s\\S]*refund"
flags: "i"
target: {source: file, path: "specs/007-gift-cards/spec.md"}
---

O1 was left open, with an owner. It belongs under `## Open questions`, not answered.
