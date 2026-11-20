---
type: regex
pattern: '\\?"skill\\?"\s*:\s*\\?"(wellforge:)?hono-ts-backend\\?"'
target: trace
---

"add a route" in a Hono service is the small-task trigger the description quotes. The `hono-ts-backend` skill must be invoked. Matched on the Skill call's input, not on the bare
name, which the session's skill listing and other skills' bodies also contain.
