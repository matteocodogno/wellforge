---
type: llm
focus: last_message
---

The run-trace's `verdicts` field records a security review as one of exactly two values,
PASS or FAIL. The owasp-reviewer can answer "PASS WITH NOTES", which is a PASS — the notes
are carried alongside, not encoded in the verdict.

PASS if the assistant says the recorded verdict value is `PASS` (not "PASS WITH NOTES", not a
third state) AND keeps the two notes somewhere rather than discarding them.

FAIL if it proposes storing the literal string "PASS WITH NOTES" as the verdict, invents a
third verdict value, treats it as a FAIL, or drops the notes.
