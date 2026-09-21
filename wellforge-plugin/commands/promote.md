---
description: Graduate a feature (or the project) up a rigor tier — pay the deferred debt (retro plan, backfill tests, blocking gates, eval)
argument-hint: <feature> --to mvp|production   |   --project --to mvp|production   [--dry-run]
---

Raise the rigor tier of a feature (or the whole project) and **pay the rigor it deferred**.
A lower tier was tracked debt (the `rigor:` frontmatter / manifest); promotion settles it.
Load the **rigor-tiers** and **spec-driven** skills now. This mirrors `/wellforge:upgrade`:
clean-tree pre-flight → plan of record → execute → verify → one revertable commit.

Arguments: $ARGUMENTS

## `--dry-run` — show the plan, change nothing

With `--dry-run` anywhere in the arguments, run every **read** step below and none of the
writes, then stop with the plan of record. Promotion is the expensive, multi-agent path: it backfills tests, raises gates from advisory to blocking, and for a project promotion re-renders copier answers. Knowing the size of that before starting is the point.

1. **What would change** — every file written, created or deleted, one line of reason each.
   For `--project`, include the copier answer that changes (`rigor`) and every generated file the re-render would touch.
2. **What would run** — the exact commands and **which agents would be spawned**, in order.
3. **What would be irreversible** — called out separately; if nothing is, say so.
4. **What it cannot predict** — the honest half. Agent work is not predictable: how many tests a backfill needs, whether the eval passes, and what the QE verdict will be are all unknown until it runs. Say which gates would become blocking, not whether they would pass.

End with the exact command to run for real (this invocation minus `--dry-run`).

**Hard rule:** a dry run writes nothing and **spawns no agents** — an agent that runs has
already changed the world (tokens, traces, and often files). Naming the agents you *would*
spawn is the deliverable.

## Step 0 — Resolve scope, current tier, target

- **Feature scope** (default): leading token = a `specs/NNN-slug/` feature. Read its
  `brief.md` (spike) or `spec.md` frontmatter `rigor:`. `--project` scope instead promotes
  the project default in `.forge/manifest.json`.
- Target tier = the `--to` value. Tiers are ordered `spike < mvp < production`.
- **Refuse** if target ≤ current (promotion only RAISES — never lower a tier, ever) or if
  already at target. State current → target and the scope before continuing.
- **`post-spec-guard.sh` enforces the raise-only rule mechanically** (PostToolUse on
  Write/Edit/MultiEdit): any edit that moves a spec's `rigor:` down is blocked with the
  three legitimate alternatives — `--mode` for one cheaper run, a new feature at the lower
  tier, or nothing. If it fires while you are promoting, you are writing the tier in the
  wrong direction; revert and re-read the transition. The hook runs after the write, so its
  message names the revert rather than preventing the edit.

## Pre-flight (all must pass)

0. **Read the state once**, and take every fact below from it rather than from the files:

   ```bash
   # Resolve the plugin root ONCE per session, then reuse $WF. ${CLAUDE_PLUGIN_ROOT} is
   # substituted for HOOKS only — it is NOT exported to the Bash tool (measured: unset), so
   # interpolating it here silently runs `python3 /scripts/...`.
   WF=$(python3 -c "import json,os;p=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))['plugins'];print(next(i['installPath'] for k,v in p.items() if k.startswith('wellforge@') for i in v))" 2>/dev/null)
   # Running from a checkout (claude --plugin-dir) installs nothing; fall back to the repo.
   [ -n "$WF" ] || WF="$(pwd)/wellforge-plugin"
   # A FUNCTION, not a variable holding a command: `WFPY="uv run ... python"` then `wfpy x`
   # relies on word splitting, which zsh does not do for unquoted parameters — measured, it
   # fails with `command not found: uv run --quiet --with pyyaml python`.
   # uv first because forge-state needs pyyaml to read frontmatter and the system python3
   # usually lacks it; without it every field reads as unknown.
   wfpy() {
     if python3 -c "import yaml" 2>/dev/null; then python3 "$@"; else uv run --quiet --with pyyaml python "$@"; fi
   }
   wfpy "$WF/scripts/forge-state.py" --json --feature <token>
   ```

   It gives the feature's current `rigor` (and `rigor_from`), `status`, `tasks`,
   `verdicts.qe` / `verdicts.eval`, `artifacts` (which of plan/design/tasks/eval-report
   exist — i.e. exactly the debt this promotion has to pay), `done_gate` and `problems`.
   The `→ production` step below ends by calling `/wellforge:done`, which reads the same
   envelope: the promotion and the close agree because they are looking at one answer.

   Refuse on a non-empty **`features[].problems[]`** — promoting a feature whose frontmatter
   does not validate writes a higher tier on top of a broken record.

   Two neighbours of that field are NOT refusal conditions, and confusing them was a real
   failure. The envelope's top-level **`warnings[]`** carries environment facts — chiefly
   "pyyaml unavailable" — which used to be reported as a problem on *every* feature, so on a
   machine without system pyyaml this rule refused every promotion that could ever be
   attempted. Report a warning, do not refuse on it. (Use the runner in the block above and
   it will not arise.) The top-level **`problems[]`** lists run traces that would not load;
   those DO block, because a trace that did not load takes its verdicts with it and the gate
   then reads a real PASS as absent — say which file, and stop.

1. `git status` clean — require commit/stash first. Promotion must be ONE reviewable,
   revertable commit (no exceptions).
2. Compute the **debt** = the gap between current and target. `artifacts` names it
   concretely (no `plan` for an mvp feature going to production, no `eval_report`, and so
   on); the rigor-tiers levers table says what each gap costs to close. One tier at a time: a
   `spike → production` jump runs `spike → mvp` then `mvp → production` in sequence.
3. **Plan of record** — present exactly what will be done for this transition (the steps
   below that apply), and that it ends in one commit. Ask the user to confirm.

## Pay the debt — feature promotion

Run only the steps the transition requires. Each missing artifact is produced by its owning
agent (handoff contract from the **orchestrate** flow); you coordinate, agents do the work.
Prepend the **target tier's** effort cue (rigor-tiers skill) to each agent's task — you're
raising rigor, so agents work at the destination tier's effort, not the source's.

### → mvp  (from spike)
1. **brief.md → spec.md** — spawn `wellforge:product-owner` with the brief + the code already
   built: write a real `spec.md` (problem, user stories, **verifiable ACs**, non-goals),
   frontmatter `rigor: mvp`. The spike's `## Findings` inform the spec; keep the brief.
2. **Tasks** — run the `/wellforge:tasks` procedure against the spec; mark tasks already
   satisfied by the spike code as done (verify each `done when:` actually holds — don't
   check boxes on faith).
3. **QE (light)** — spawn `wellforge:quality-engineer` in advisory mode (SAST-high, lint,
   typecheck and the **security floor** block; coverage reported as a gap). On FAIL, route
   per the **rigor-tiers** skill's *"Routing a QE FAIL"* section — blocking rows only.

### → production  (from mvp)
1. **plan.md** — spawn `wellforge:architect` with the spec + the existing code: write the
   retro `plan.md` capturing the architecture the code already embodies (data model, API
   contracts, test strategy, risks), `status: approved` only on the user's gate. If UI,
   spawn `wellforge:designer` for `design.md`.
2. **Re-sync tasks** to the plan (`/wellforge:tasks` re-sync — preserves checked tasks).
3. **QE (full)** — backfill tests to the **enforced** floors: 80% line coverage, SAST,
   dependency audit, lint, typecheck — all **blocking** now. On FAIL, route per the
   **rigor-tiers** skill's *"Routing a QE FAIL"* section (owner table, 2-round cap).
4. **Eval** — run the `/wellforge:eval` procedure (LM-judge). **A PASS is the gate into
   `done`** — QE alone is not enough. FAIL → route failing dimensions to the dev agents
   (same bounded loop), re-eval.
4b. **Security review** — before the close, at the TARGET tier. `promote` never ran this,
   and then invoked a production gate that requires `verdicts.security == PASS`: an
   `mvp → production` promotion could only pass if some earlier `/wellforge:implement`
   happened to have reviewed the code, and otherwise refused with "security review is
   absent" and no way to satisfy it from inside promote. The tier being promoted TO is the
   one that decides, and `production` is in `always_at_tier`, so this always dispatches on
   a `→ production` promotion.

   ```bash
   # $WF / wfpy as resolved in the block above.
   wfpy "$WF/scripts/security-triggers.py" \
     --tier <target tier> --diff-base <the base this promotion's work branched from> --json
   ```

   `dispatch: true` → spawn **`wellforge:owasp-reviewer`** over `scope[]`. Findings ≥ medium
   are defects and route exactly like a QE FAIL (rigor-tiers, *"Routing a QE FAIL"*, 2-round
   cap). Record `verdicts.security` in the trace **mapped** — `PASS WITH NOTES` → `"PASS"`
   with `security.notes[]`, `REVIEW REQUIRED` → `"FAIL"` (agents/owasp-reviewer.md).
   A non-zero exit means the script could not read the diff; it dispatches anyway and says
   why — do not treat that as a skip.

5. **Close** — only on PASS. First **write the run trace** (Close §3 below): the production
   gate reads `verdicts.qe` and `verdicts.security` *from the trace*, so a close that
   precedes the trace is judged against a feature that appears to have no QE and no security
   review, and `/wellforge:done` refuses work that just passed both. Then set
   `rigor: production` in the frontmatter (the tier field is yours), and **run the
   `/wellforge:done` procedure**, which re-verifies the *production*
   gate against the artifacts on disk and records the close. Do not set `status: done`
   yourself: the feature was already `done` at mvp, so the transition here must be re-earned
   at the new tier — and the production branch also checks **every task is ticked**, which
   this flow previously skipped.

## Pay the debt — project promotion (`--project`)

**Adopted projects** (`.forge/adoption.json`, no template ancestry): there's no copier to
re-render. Just update the `rigor` field in `adoption.json` to the target tier (a one-line
edit) and, if the project took the gates layer, adjust its CI to the target tier's strictness
by hand. Skip the copier steps below.

**Scaffolded projects** (`.forge/manifest.json`): the `rigor` is a copier answer, so flip it
through copier (re-renders the tier-conditional `quality.yml`, README badge, AGENTS note,
manifest) WITHOUT a version bump:

```bash
uvx copier update --trust --skip-answered --conflict inline \
  --vcs-ref <current _commit from .copier-answers.yml> --data rigor=<target>
```

- Pinning `--vcs-ref` to the recorded `_commit` keeps this a pure rigor change, not a
  template upgrade (that's `/wellforge:upgrade`'s job — don't bundle them).
- Resolve any conflict markers (keep project behavior, adopt template structure); zero
  `<<<<<<<` may remain. Verify `.forge/manifest.json` now reads the new `rigor`.
- Promoting the project to `production` raises CI to full gates: run them once and make
  them green before committing (a project promoted to production must pass production CI).

## Verify

- The gates appropriate to the **target** tier, run for real: mvp → advisory coverage +
  blocking SAST/lint/floor; production → full blocking gates + eval PASS.
- `mise run install && mise run build && mise run test` green where the change touches code.

## Close

1. One revertable commit: `chore(rigor): promote <feature|project> <old> → <new>` — body
   lists artifacts created (spec/plan/design), tests backfilled, gate + eval results.
2. Frontmatter/manifest now read the target tier (verify; never hand-edit the manifest).
3. **Record the run** — write `.forge/runs/<run_id>.json` per the **observability** skill:
   `command: promote`, the agents run, QE + eval verdicts, `from`/`to` tiers, `result`.
   Written in step 5 *before* `/wellforge:done`, not here — it is listed in this section
   because it belongs to the close, but the gate reads it, so it cannot follow it.
4. Report: tier delta, debt paid (artifacts, coverage before→after, eval verdict), and what
   (if anything) the user still owns. If a feature reached production, it's now `done`.

## Hard rules

- Promotion only RAISES. A downgrade request is refused — lower rigor is re-declared
  deliberately at creation, never via promote.
- Production is never reached without an eval **PASS** — no auto-approve, no "pass with
  remarks". The eval is the gate, same as the normal flow.
- The security floor was always on; promotion ADDS the deferred gates, never removes a check.
- Bounded loops only (QE/eval fix loop max 2 rounds, then escalate). Dirty tree → no
  promotion; fully done or fully reverted.

  **To revert, do not reach for the destructive reset this line used to prescribe.** The
  plugin's own `pre-bash-guard.sh` blocks `git reset --hard` at any target, so the command
  written here could never run in a WellForge session — the document prescribed something
  its own guard refuses, and the guard has no ask-path to route through. The
  non-destructive equivalents, in order of preference:

  ```bash
  git restore --source=HEAD --staged --worktree -- <paths>   # undo tracked edits, keep the rest
  git stash push -u -m "promote <feature> — aborted"          # keep the work, recoverable
  git revert <sha>                                            # already committed: revert, do not erase
  ```

  If a hard reset is genuinely what you want, the user runs it themselves outside the agent
  — which is exactly the case the guard exists to force.
- Never weaken a gate or delete a test to make a tier pass — that defeats the promotion.
