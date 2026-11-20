---
type: regex
pattern: '\\?"skill\\?"\s*:\s*\\?"(wellforge:)?kotlin-springboot\\?"'
target: trace
---

"create a migration" is a quoted kotlin-springboot trigger; the repo has Liquibase changesets. The `kotlin-springboot` skill must be invoked. Matched on the Skill call's input, not on the bare
name, which the session's skill listing and other skills' bodies also contain.
