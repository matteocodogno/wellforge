---
name: orchestrate-hands-po-the-ledger
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, Task]
---

Run /wellforge:orchestrate "gift cards at checkout" --ledger .forge/grill/gift-cards.md

Work in the current directory, which is the project root. The feature's slug must be
`gift-cards`. Nobody is here to answer a question or to approve anything: run the pipeline
up to the first human gate, then stop and report what is waiting for approval. Do not
approve the spec yourself.
