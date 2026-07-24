---
description: One-way compression of a WellForge-owned file (memory / AGENTS.md / a skill-command-agent description) with a fact-preservation safety gate
argument-hint: <path> — memory/*.md | AGENTS.md | a skill/command/agent file (its description: frontmatter is the compression target)
---

Compress a WellForge-owned file **in place, irreversibly**, without losing any fact it
states — only phrasing gets shorter. Load the **terse** skill now: it owns the
byte-identical invariant (code blocks, shell commands, file paths, identifiers, and error
messages inside the target are never altered, even by this command) and the artifact
exemption list this command must also respect.

This is a **different thing** from the `terse` cue that commands prepend to conversational
output: that cue shapes what an agent *says*; this command permanently rewrites a *file on
disk*. There is no decompress. Git is the only undo.

Target: $ARGUMENTS

## Step 0 — Resolve and validate the target (refuse fast, refuse loud)

Resolve `$ARGUMENTS` to a single path. Then check, **in this order**, and STOP at the
first failure — do not read further into the file, do not attempt compression, report
the specific reason and take no other action:

1. **Inside a git work tree at all?** `git rev-parse --is-inside-work-tree`. If not: refuse
   — "no VCS backing available; this command never runs outside a git repo."
2. **Tracked and committed?** `git ls-files --error-unmatch -- <path>` must succeed AND
   `git log --oneline -1 -- <path>` must return at least one commit. An untracked file, a
   new file that's only staged, or a file git has never seen has no history to recover
   from — refuse: **"<path> has no VCS backing — commit it first. Compression is one-way;
   git history is the only undo, so an uncommitted target has none."**
3. **Is it a valid WellForge-owned target?** Match the path against exactly these patterns
   — nothing else qualifies, regardless of who "owns" it in spirit:
   - `memory/*.md` — a memory file.
   - `AGENTS.md` (project root) — the canonical cross-tool context file.
   - A WellForge-authored skill (`**/skills/*/SKILL.md`), command (`**/commands/*.md`), or
     agent (`**/agents/*.md`) file — but **only its `description:` frontmatter value** is
     the compression target, never the body.

   Anything else is refused, with the specific reason surfaced:
   - A **spec-driven or governance artifact** (`spec.md`, `plan.md`, `tasks.md`,
     `design.md`, an ADR, `eval.md`/`eval-report.md`) — refuse: these are explicitly
     **exempt** from all terse handling (US-3 / terse skill's artifact-exemption list),
     even though WellForge authored them. Point at that exemption; do not compress.
   - A **third-party MCP server's tool description** — refuse: those live inside the
     server's own process/config, not a file in this repo we can rewrite. WellForge has no
     middleware layer to intercept them (plan Risk R2); this is out of reach by design, not
     an oversight. If genuine third-party tool-description shrinking is wanted, that's a
     separate, larger feature — not this command.
   - Application source, README, config, or any file not matching the three patterns above
     — refuse: "not a WellForge-owned compression target."

Only after all three checks pass, proceed. State which pattern matched and what the
compression scope is (whole file vs. the `description:` value only).

## Step 1 — Extract the original fact-set

Read the target's compression scope (the whole body for `memory/*.md` / `AGENTS.md`, or
just the `description:` string for a skill/command/agent). Enumerate its **atomic
facts** — the smallest independently-checkable statements it makes: every instruction,
named condition, trigger phrase, threshold/number, exception, cross-reference, and
constraint. Number them (F1, F2, F3, …) as an explicit checklist. Be exhaustive — a fact
left off this list can't be checked for later, which defeats the gate.

## Step 2 — Compress

Produce the compressed version: drop filler, restated context, and redundant phrasing —
same spirit as the terse cue — while keeping every fact from Step 1 expressible, even if
more tersely worded. **Hold the byte-identical invariant**: any code span, shell command,
file path, identifier, or error message quoted inside the target is copied verbatim, never
paraphrased or reformatted. If the target is frontmatter, keep it valid YAML and keep every
other frontmatter key untouched.

## Step 3 — Re-extract and assert no fact was lost

Re-run the same atomic-fact extraction (Step 1's method) against the **compressed** text,
producing F1′, F2′, … Then assert, fact by fact:

```
fact-set(compressed) ⊇ fact-set(original)
```

For every original fact Fi, show which compressed fact it maps to (rewording is fine;
disappearance is not). This is the deterministic half of the gate (a list-membership
check on an LLM-produced fact list) plus your own judgment call on whether the mapping is
a faithful match, not a stretch.

**If any Fi has no faithful match in the compressed set: STOP. Do not write anything.**
Report exactly which fact(s) would be lost, quote the original wording, and either produce
a less-aggressive compression that keeps them or leave the file untouched and say so. A
partial pass is a refusal, not a partial write.

## Step 4 — Show the diff, require confirmation

Only once Step 3 passes in full:
1. Show a diff of exactly what changes (the whole file for `memory/*.md`/`AGENTS.md`; just
   the `description:` line/block for a skill/command/agent) — original vs. compressed,
   side by side or unified.
2. Show the Step 3 fact-mapping table so the confirmation is evidence-based, not a rubber
   stamp.
3. Report the size delta (characters or lines) — confirm it's actually smaller; if the
   "compressed" version isn't smaller, say so and don't claim a win.
4. **Ask the user to confirm the overwrite explicitly.** No confirmation, no write — this
   step is not skippable even when Step 3 passed cleanly, because the transform is
   irreversible.

## Step 5 — Overwrite (only on confirmation)

Write the compressed content in place:
- `memory/*.md` / `AGENTS.md`: replace the body; leave any existing frontmatter keys as
  they were.
- Skill/command/agent file: replace only the `description:` value; every other byte in the
  file (frontmatter keys, the entire body — instructions, code, examples) is untouched.

This is the one and only write. State plainly that the transform is one-way and that
`git diff` / `git checkout -- <path>` against the prior commit is the recovery path if the
result turns out wrong later — there is no command-level undo.

## Step 6 — Post-write sanity check (AC-4.2)

Because Step 3's gate guarantees every original fact is still recoverable, a later session
consuming the compressed file has the same facts available as it would from the original —
that's the mechanism this command relies on for "behavior unchanged." Where practical,
spot-check it directly rather than trusting the mechanism alone:
- Compressed a skill/command/agent `description:`? Confirm it still surfaces for the same
  trigger phrases the original was written for (the discovery listing / a quick trigger
  check).
- Compressed `memory/*.md` or `AGENTS.md`? Confirm a fresh read of the file still yields
  the same actionable guidance for the facts that matter most (spot-check a couple of F-i
  items against the new text).

Report the result of this check alongside the rest.

## Report

- Which file, which pattern matched, whole-file vs. frontmatter-only scope.
- The fact checklist and the mapping that proved no loss (or, on refusal, exactly which
  fact would have been lost and why you stopped).
- Size before → after.
- The post-write sanity check outcome (Step 6).
- Reminder: this file cannot be un-compressed by this command — git history is the undo.

## Hard rules

- Never overwrite without Step 3's fact-preservation gate passing in full — a single
  missing fact is a refusal, not a warning.
- Never overwrite without showing the diff and getting explicit confirmation, even when
  the gate passes cleanly.
- Never touch a file with no VCS backing, and never touch a file outside the three valid
  target patterns — a spec-driven artifact and a third-party MCP tool description are both
  hard refusals, not judgment calls.
- Never let compression alter a code block, shell command, file path, identifier, or error
  message inside the target — the byte-identical invariant (terse skill) applies inside
  this command exactly as it does to conversational output.
- One file per invocation. No recursive/batch compression — every write stays small enough
  for a human to actually read the diff before confirming.
