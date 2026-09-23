---
spec: 001-checkout-flow
status: approved
---

# Plan — checkout flow

## Architecture
A `payments` module behind an interface, one adapter for the PSP.

## Data model
`payment(id, basket_id, status, psp_ref)`.

## API contracts
`POST /baskets/{id}/payment` → 201 with the payment, 402 with the issuer reason.

## Test strategy
Integration tests against an ephemeral database; the PSP adapter is contract-tested.

## Risks
PSP sandbox flakiness.
