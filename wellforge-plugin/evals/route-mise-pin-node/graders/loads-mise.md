---
type: regex
pattern: '\\?"skill\\?"\s*:\s*\\?"(wellforge:)?mise\\?"'
target: trace
---

"pin the node version" and "add a task for" are quoted mise triggers. The `mise` skill must be invoked. Matched on the Skill call's input, not on the bare
name, which the session's skill listing and other skills' bodies also contain.
