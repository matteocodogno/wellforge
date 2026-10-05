---
description: Retro a session or feature — ranked, evidence-backed fixes to the environment, not the code
argument-hint: [NNN-slug] (default: this session)
---

Look back at the work just done and find what in the **environment** made it slower or
more wrong than it had to be — then propose the smallest change that stops it recurring.
The environment is everything the next session inherits: `CLAUDE.md` / `AGENTS.md`, the
glossary, mise tasks, hooks, permissions, docs, scripts, the template, the plugin itself.

It is not a review of the code that was written (QE and the evaluator did that) and not a
review of anyone's performance. A retro that concludes "be more careful next time" has
found nothing: **a rule that depends on remembering is not enforced.**

Scope: $ARGUMENTS

## Step 1 — Gather evidence

Two sources. Use what the scope gives you and say which you used.

**This conversation** (always, when the scope is the session). Read back through it for:

- **Corrections** — the user redirected you ("no, not that", "you forgot…", "I already
  said…"). Quote the line.
- **Repeats** — the same command failed more than once; the same file or fact was looked
  up more than once; the same permission prompt appeared again.
- **Questions the repo could have answered** — you asked, or guessed, something that was
  written down somewhere you did not look, or written nowhere.
- **Stops** — an `ENV-FAULT:`, a 3-attempt stop (`systematic-debugging`), drift, a
  worktree collision, a gate that went red for a reason unrelated to the change.
- **Detours** — work that had to be redone, a skill that fired too late or not at all.

If the conversation has been compacted, say so: the early part of the session is a summary,
and a retro built on a summary under-reports. Do not reconstruct friction you cannot see.

**Run traces** (when the scope is a feature, or the session ran `implement` / `orchestrate`).
Load the **observability** skill for the schema, then:

```bash
# Resolve the plugin root ONCE per session, then reuse $WF. ${CLAUDE_PLUGIN_ROOT} is
# substituted for HOOKS only — it is NOT exported to the Bash tool.
WF=$(python3 -c "import json,os;p=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))['plugins'];print(next(i['installPath'] for k,v in p.items() if k.startswith('wellforge@') for i in v))" 2>/dev/null)
[ -n "$WF" ] || WF="$(pwd)/wellforge-plugin"
wfpy() {
  if python3 -c "import yaml" 2>/dev/null; then python3 "$@"; else uv run --quiet --with pyyaml python "$@"; fi
}
wfpy "$WF/scripts/run-report.py" --feature <NNN-slug> --json     # per run: verdicts, result, drift_open
wfpy "$WF/scripts/run-report.py" --rework                        # rework rounds per feature and per agent
```

The report is the index: which runs exist, every `FAIL` verdict (a rework round), any
`result` other than `completed`. It does **not** carry the detail — for the runs it lists,
read `.forge/runs/<run_id>.json` itself for the `drift_events`, `env_faults` and
`collision_events` entries, which are the evidence. No `.forge/runs/` → skip this source
and say so; do not infer runs from git history.

**No evidence, no finding.** Every finding below cites a quoted line, a trace entry, or a
command and its output. A hunch about what "probably" slowed things down is not one.

## Step 2 — Find the cause in the environment

For each piece of evidence, ask what the environment was missing — not what you should
have done differently. One finding per cause; several symptoms of one cause are one
finding with several citations.

Then pick the fix from **the strongest rung that fits**, top down:

| Rung | The fix is… | Example |
|---|---|---|
| 1. **Remove the cause** | fix the thing itself | the flaky test, the script that needs an undocumented flag, the task that fails on a clean checkout |
| 2. **A mechanism** | something that runs without being remembered | a mise task, a hook or guard, a CI check, a permission allowlist entry, an env file added to the worktree carry-in |
| 3. **A document read on demand** | loaded only when relevant | a stack-skill note, a `docs/` page, an ADR, a glossary term |
| 4. **A document read every session** | `CLAUDE.md`, `AGENTS.md` | one line, and only when no lower rung fits |

Rung 4 is the reflex and the most expensive answer: it is paid for in every session by
every teammate, and it is the rung that depends on being read. Reaching for it means
saying why rungs 1–3 do not work.

## Step 3 — Rank, and keep it short

| Severity | Means |
|---|---|
| **Blocker** | work stopped, or a human had to step in — and the cause is still there for the next session |
| **Friction** | cost a retry, a rework round or a detour, and will recur |
| **Papercut** | cost seconds; worth fixing only if the fix is a one-liner |

Recurrence decides the rank, not how annoying it felt: something that happened once and
has no structural cause is an anecdote — leave it out. **Report at most five findings**,
highest severity first. A retro with fifteen items changes nothing. Zero findings is a
valid result: say `Retro: nothing structural found` and stop.

Present each as:

```
[Blocker] <one-line cause>
  Evidence: <quote / trace entry / command + output>
  Fix (rung 2): <exact change — file and the line or task to add>
  Lands in: project | user settings | upstream WellForge
```

## Step 4 — Apply only what the user picks

Ask which findings to act on. Then, per finding and only on a yes:

- **Project** (the repo's own files) → make the change. Follow the project's conventions:
  the glossary through the **domain-modeling** skill; a decision with a rejected
  alternative through `adr-writer`, not a line in `CLAUDE.md`.
- **User settings** (`~/.claude/settings.json`, a personal allowlist) → show the exact
  entry and let the user apply it. Never edit a user-level file from a retro.
- **Upstream WellForge** (a plugin skill, a command, a template) → draft the issue text:
  what happened, the evidence, the proposed change. File it with `gh` only on an explicit
  yes — it is public and outward-facing. Do not patch the installed plugin in place.

Anything not picked is left in the report as written, so it can be picked up later.

## Hard rules

- **Never propose weakening a gate.** No lowered threshold, skipped test, raised timeout or
  disabled rule as a "fix for friction". A gate that looks miscalibrated is an upstream
  finding with evidence (PR to `gates/`), never a local edit. The security floor is not
  friction.
- **Never propose re-tiering an agent on one feature.** A rework hotspot from
  `run-report.py --rework` is a candidate; `config/model-routing.yml` says what counts as
  evidence, and a human decides.
- Never edit `specs/`, `.forge/manifest.json` or `.forge/runs/`, and never set a `status:`.
- Never commit. Changes are left in the working tree for the user to review.
- Nothing is applied without a yes, one finding at a time — this is discovery and triage,
  and the human decides (the **heartbeat** skill's rule, though a retro is run by hand, not
  on a schedule).
