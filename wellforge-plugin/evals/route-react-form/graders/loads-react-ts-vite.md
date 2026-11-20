---
type: regex
pattern: '\\?"skill\\?"\s*:\s*\\?"(wellforge:)?react-ts-vite\\?"'
target: trace
---

"create a form" is one of react-ts-vite's quoted small-task triggers. The `react-ts-vite` skill must be invoked. Matched on the Skill call's input, not on the bare
name, which the session's skill listing and other skills' bodies also contain.
