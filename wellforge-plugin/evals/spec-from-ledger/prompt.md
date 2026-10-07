---
name: spec-from-ledger
max_turns: 25
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Run /wellforge:spec gift cards at checkout --ledger .forge/grill/gift-cards.md

Use the slug `gift-cards` for the feature. Work in the current directory, which is the
project root. Nobody is here to answer a question or to approve anything: write the draft
spec from the ledger, do everything the command does up to the review, and stop there. Do
not mark it approved.
