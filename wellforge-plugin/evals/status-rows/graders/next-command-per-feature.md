---
type: llm
focus: last_message
---

PASS only if the answer tells the reader what to run NEXT for the unfinished features, and
those suggestions are sensible for the state each feature is in — for example `/wellforge:plan`
or `/wellforge:tasks` for an approved feature with no tasks, and something that closes or
evaluates `003-order-history`, whose tasks are all done.

FAIL if it lists the features with no next step at all, or if it suggests a next step that
contradicts the state (for example telling the reader to start work on the superseded
`005-legacy-payments`, or to run anything at all on the finished spike `004-cache-spike`).
