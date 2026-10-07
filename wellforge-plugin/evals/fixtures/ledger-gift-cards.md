---
topic: gift cards at checkout
grilled: 2026-10-06
target: idea
complete: true
---

## Decision ledger — gift cards at checkout
Decided (the user chose):
- D1 A gift card is valid for 14 months from the day it is bought — "a year is too short for a Christmas gift, two is an accounting problem"
- D2 Gift cards are EUR only at launch — no other currency, no conversion
Delegated (the user deferred to the recommendation):
- D3 A gift card code is 12 characters, shown in groups of four — recommended because it survives being read out over the phone
Found (read from the repo, not asked):
- F1 Checkout already pays through a `payments` module with one PSP adapter — specs/001-checkout-flow/plan.md
Assumed (not load-bearing; strike any that is wrong):
- A1 The remaining balance is shown on the order summary
Open (unresolved — each needs an owner):
- O1 Can a partially used gift card be refunded? — owner: PO

Constraints the user volunteered (verbatim):
- "It must reuse the existing PSP adapter from the checkout flow. No second payment provider."
