---
type: llm
focus: last_message
---

The user had already answered an interview: a decision ledger at `.forge/grill/gift-cards.md`
recorded the validity period (14 months), the currency (EUR only) and the code format.
`/wellforge:spec --ledger` must treat that file as the interview.

PASS if the assistant wrote the spec from the ledger without asking the user again about
validity, currency or code format. Mentioning the one question the ledger left open (whether
a partially used gift card can be refunded) is correct and is not a re-interview.

FAIL if it asked the user to decide validity, currency or code format again, said it could
not write the spec without an interview, or reported the spec as approved.
