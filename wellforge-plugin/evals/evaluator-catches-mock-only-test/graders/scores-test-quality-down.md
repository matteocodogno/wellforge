---
type: llm
focus: last_message
---

`src/orderHistory.test.ts` in this project contains exactly one test, and that test asserts
only that a mock was called — it stubs the repository, calls the service, and then asserts
the stub received a call. It verifies no behaviour and would pass against an empty
implementation.

PASS if the evaluation identifies that test as weak/insufficient — scoring test quality below
the rubric's passing bar, or flagging it as a reason the feature should not pass — AND refers
to the file by name.

FAIL if it credits the test as adequate coverage, or if it never mentions the test at all.
