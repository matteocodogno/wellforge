---
type: regex
pattern: '\\?"skill\\?"\s*:\s*\\?"(wellforge:)?pulumi-gcp-ts\\?"'
target: trace
---

"add a bucket" is a quoted pulumi-gcp-ts trigger, in a repo that also has a TS backend. The `pulumi-gcp-ts` skill must be invoked. Matched on the Skill call's input, not on the bare
name, which the session's skill listing and other skills' bodies also contain.
