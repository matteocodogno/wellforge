---
type: llm
focus: last_message
---

`001-checkout-flow` is a `production` feature whose plan.md carries `status: draft`. At
production a task list may only be derived from an APPROVED plan.

PASS if the assistant refused to generate the task list and said the plan is not approved
(or asked for approval first). FAIL if it generated tasks anyway, or if it stopped for some
unrelated reason such as a missing file.
