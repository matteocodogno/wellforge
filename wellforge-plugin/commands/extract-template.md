---
description: Profile an existing project's stack, gap-check it against the WellForge presets, and optionally extract a reusable org-internal Copier template from it
argument-hint: (run from the project root) [--profile-only] — --profile-only stops after the stack profile + gap check
---

Turn **this** project into a reusable template. Two parts, per the **template-extraction**
skill (load it now — it is authoritative for the schema, the gap-check heuristic, the
scrub/IP gate, and CONTRACT-compliant generation):

1. **Stack profile + gap check** — fingerprint the stack, classify it against the shipped
   presets, write `.forge/stack-profile.json`, and report the verdict.
2. **Org-internal template extraction** (opt-in) — reverse the project into a Copier template
   the **org owns**, so the team's next service starts from its own proven stack.

This never opens a PR to the WellForge repo and never ships the project's code upstream — the
output is an org-owned draft the user reviews.

## Procedure

1. **Preconditions.** A git repo. A reasonably clean tree if extraction may run (the profile
   alone is read-only). If `.forge/manifest.json` exists this is a **scaffolded** project —
   it already has template ancestry, so extraction is pointless; report that and stop
   (offer `/wellforge:upgrade` instead). Adopted projects (`.forge/adoption.json`) are fine.

2. **Part 1 — profile + gap (always).** Follow the skill: detect the stack from build files,
   lockfiles, and the source tree; write `.forge/stack-profile.json`; report the gap verdict
   (`covered` / `partial` / `novel`), the closest preset, and the recommendation. If
   `--profile-only` was passed, stop here.

3. **Offer extraction.** Present the verdict and ask whether to extract a reusable template.
   On a `covered` verdict, say up front that extraction would largely duplicate a shipped
   preset (low value) before the user decides. If they decline, stop after the profile.

4. **Part 2 — extract (if chosen).** Run the skill's extraction procedure: the **safety gate
   first** (skeleton-only, secret scrub, IP/license check), then ask for a destination path
   (refuse the source project or the WellForge repo), generate the CONTRACT-compliant Copier
   template repo, and **verify it renders with `copier copy --defaults`** before hand-off.

5. **Hand off.** Report destination, preset slug, what was parameterized, what was
   scrubbed/excluded, the verification result, and any gates gap. State it's an org-owned
   draft to review, and give the `uvx copier copy` command to use it.

## Hard rules

- **Skeleton-only, scrubbed.** Never carry domain/business logic, secrets, or licensed
  third-party code into the template. If a secret scan hits an included file, STOP.
- **Org-owned output only.** Write to a user-chosen destination outside the source project and
  outside the WellForge repo. This command never contributes to the WellForge catalog.
- **`--defaults` must render.** A template that can't generate a working project on defaults is
  not done — fix and re-verify before hand-off.
- The profile only informs; it never blocks. A `covered` verdict is a nudge, not a refusal.
