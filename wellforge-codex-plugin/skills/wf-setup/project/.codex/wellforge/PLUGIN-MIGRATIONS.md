# Plugin migrations — project-side changes, per plugin minor

`.forge/manifest.json` (or `.forge/adoption.json`) records which **plugin** version last set
a project up. This file records what changed on the *project* side since — the things a
newer plugin expects to find that an older one never created.

**Read by `/wellforge:upgrade`**, which compares the recorded `plugin.version` against the
running one and applies or surfaces every entry in between. `/wellforge:doctor` reports the
gap without acting on it.

**It ships inside the plugin** (`<plugin root>/PLUGIN-MIGRATIONS.md`), so the plugin that
runs always carries exactly the notes up to its own version — in a project, with no
wellforge checkout and no network. It lived in the repo's `docs/` until 2.62.1, and a
marketplace install (which ships only `wellforge-plugin/`) could not read it: an upgrade
from 1.6 reported the notes unreachable and, correctly, refused to call the project migrated.

## What belongs here

Only changes a **project** must absorb: a `.forge/` schema bump, a new hook that needs a
`.gitignore` entry, a renamed frontmatter field, a file the plugin now expects. Plugin-internal
changes — a reworded skill, a new command, a tighter guard — do **not** belong here: they
travel with the plugin and need nothing from the project.

The test: *would a project set up by the older plugin be wrong, incomplete, or noisy under
the newer one?* If no, it is not a migration.

## Format

Each entry: the minor it landed in, whether it is automatic or needs a human, and what to do.
An entry with no project-side action still gets a line saying so — silence is ambiguous
between "nothing to do" and "nobody wrote it down".

---

## 2.63.1 — the `pulumi-gcp-ts` skill pins the Pulumi CLI exactly

- The skill's pinned-versions table now says Pulumi CLI `3.274.1 (exact)`, matching template
  `v0.13.1`: a floating `"3"` resolved to 3.275.0, whose re-uploaded asset failed mise's
  cached checksum and broke `mise install` in every pulumi project. Agents that scaffold or
  review a Pulumi project now propose the exact pin instead of the floating major.
- **Action:** none for the plugin. Pulumi projects take the pin with template `v0.13.1`
  (`/wellforge:upgrade`).

---

## 2.63.0 — `/wellforge:release` loads the project's `RELEASING.md`

- `/wellforge:release` reads `RELEASING.md` at the project root: `## Before` checks run
  before the dry-run, `## After` steps after the tag (each outward-facing one with its own
  go), `## Never` rules beside the hard ones, and an optional `## Release` section that
  drives a project's own release tool instead of release-it. The file can add steps and
  rules, never remove the dry-run, the confirmation or the clean-tree check. Command-only
  lines are named as candidates for `.release-it.json` hooks.
- `/wellforge:adopt` writes `RELEASING.md` in the Release management layer — from the team's
  answers, commands into hooks — and, for a project that already has a release tool, a
  runbook describing that tool instead of stopping. An adoption that already has the
  release layer is offered "Release runbook" alone.
- The same text reaches Codex, Copilot and OpenCode: their generated release commands are
  checked to still name the file (`adapters/smoke-test.py`, check g).
- **Action:** scaffolded projects get the file with template `v0.13.0` (`/wellforge:upgrade`);
  adopted ones with `/wellforge:adopt` → "Release runbook". Without the file, the command
  works as before and says so.
- **CI note:** the `plugin-v2.63.0` tag's CI is red in one job, `generated-gates
  (pulumi-gcp-ts)`, from a stale mise checksum for Pulumi 3.275.0 — outside the plugin, whose
  content is unaffected. Fixed in template `v0.13.1` (exact Pulumi pin); the tag was kept, not
  re-cut, because it was already published.

---

## 2.62.2 — the last prompts that still predicted a sequential ADR number

`/wellforge:plan` and the architect predicted an ADR path as "the next free 4-digit number",
the counter 2.62.0 retired; they now predict `docs/adr/YYYYMMDD-slug.md`. `/wellforge:grill-me`,
`/wellforge:improve-architecture` and the product-owner lose their last counter wording.
Prompt text only. **Nothing to do on upgrade.**

---

## 2.62.1 — the migration notes ship with the plugin

This file moved from the wellforge repo's `docs/` into the plugin, so `/wellforge:upgrade`
and `/wellforge:doctor` read it from the plugin root instead of needing a wellforge
checkout. `/wellforge:upgrade` also finds `docs/TEMPLATE-MIGRATIONS.md` on its own (checkout,
then `_src_path`, then a shallow clone at the target tag), and accepts the pre-2.42 string
form of `plugin` in the manifest. Projects are unaffected. **Nothing to do on upgrade** —
except that an upgrade which stopped earlier for want of these notes can now be re-run.

---

## 2.62.0 — feature and ADR ids are dates, not counters

New features are `specs/YYYYMMDD-slug/` and new ADRs `docs/adr/YYYYMMDD-title.md`: a
sequential `NNN` collided whenever two people created a feature or an ADR on parallel
branches. The frontmatter schema accepts both forms, so a project that does nothing keeps
working — legacy ids sort before the dated ones.

**Human — offer the rename, do not run it unasked.** It is one repo-wide commit that every
open branch has to rebase over, so the team picks the moment (ideally few open branches).

1. Dry run, and show the user the plan (old → new, and where each date came from):
   `wfpy "$WF/scripts/migrate-ids.py"` (the `$WF` / `wfpy` resolver from `/wellforge:done`
   Step 1). A non-zero exit lists what blocks it: two items mapping to the same
   `date-slug`, or a target that already exists — rename that slug by hand, then re-run.
2. On a yes, on a clean tree: `wfpy "$WF/scripts/migrate-ids.py" --apply`. It `git mv`s
   every legacy feature and ADR, rewrites the references (`NNN-slug` tokens, `specs/NNN`,
   `ADR NNNN`, the `[NNNN]` tags in `AGENTS.md`, `id:` / `spec:` frontmatter, `.forge/runs/`
   traces) and writes `.forge/id-migration.json` (old → new — commit messages keep the old
   ids, this is how they are read back). It refuses while a non-terminal feature has drift
   or a stale eval, because the rename commit would erase both signals: resolve them first
   (`--force` only if the user accepts losing them).
3. Show `git diff --cached -M --stat` and the "check by hand" lines (bare ADR numbers in
   prose, left alone because `0001` alone is ambiguous), then commit it alone:
   `refactor: date-based ids for features and ADRs`.
4. Teammates rebase onto it; git's rename detection carries their edits into the renamed
   directories. A feature created as `NNN-` on a branch that predates the rename is still
   valid — re-run step 1 after it lands; the script is idempotent.

---

## 2.61.1 — `/wellforge:release` names all four WellForge series

Wording only: inside the wellforge repo, `/wellforge:release` now lists the template,
gates, plugin and CLI series with their `mise run release:<series>` command. Projects are
unaffected. **Nothing to do on upgrade.**

---

## 2.61.0 — agents declare what they decided for you

- `backend-dev`, `frontend-dev` and `devops` end every report with a `DECISIONS:` block:
  the defaults, scope cuts, reinterpretations and unchecked assumptions the spec, plan and
  task did not dictate (or `DECISIONS: none — <why>`). A new `SubagentStop` hook,
  `subagent-decisions-guard.sh`, sends the agent back once when the block is missing; it
  never loops and fails open when it cannot read the report.
- `/wellforge:implement` and `/wellforge:orchestrate` append those blocks to
  `specs/NNN-slug/decisions.md` (format in the `spec-driven` skill); `/wellforge:done`
  prints them when it closes the feature.
- **Nothing to do on upgrade.** Features already in flight simply have no `decisions.md`
  until their next dispatch, and `done` says so in one line. The file is not a gate input.

---

## 2.60.0 — leaner sessions: two MCP servers gone, side-effect commands user-only

- The plugin no longer starts the `sequential-thinking` and `github` MCP servers.
  `sequential-thinking` did what the effort level does now, and its tool definitions sat in
  every session; `github` duplicated the `gh` CLI that every GitHub-touching command already
  fell back to. **Action, only if you used them:** run `gh auth login` (GitHub is reached
  through `gh`), or declare either server in the project's own `.mcp.json`.
- `release`, `new`, `upgrade`, `promote`, `adopt`, `extract-template` and `terse-compress`
  are user-only (`disable-model-invocation: true`): Claude suggests them, you type them.
  Nothing to do on upgrade.
- `adr-writer` runs on the `cheap` tier (haiku) as a trial — see `config/model-routing.yml`
  for when it reverts. Nothing to do on upgrade.

---

## 2.59.0 — a new `tasks.md` needs an approved upstream

`post-spec-guard` (PostToolUse) now refuses the **creation** of `specs/NNN-slug/tasks.md`
unless what it derives from is approved: `plan.md` at `production`, `spec.md` at `mvp`; at
`spike` a `tasks.md` is always refused. The tier resolves like `forge-state.py`: the spec's
`rigor:`, then `.forge/manifest.json` / `.forge/adoption.json`, then `production`. This was
already the rule in `/wellforge:tasks`; only the prompt kept it.

**Nothing to do on upgrade.** Existing `tasks.md` files are never gated (only a file with no
version at HEAD is), so re-syncing after drift works as before. A hand-written `tasks.md` on
a draft plan will now be refused — approve the plan, or set the feature's `rigor:` honestly.

---

## 2.50.0 — MCP servers are pinned to exact versions

`wellforge-plugin/.mcp.json` launched `@playwright/mcp@latest` and
`@modelcontextprotocol/server-sequential-thinking` (no version at all) through `npx`. Both
now name an exact version, checked against the npm registry on 2026-09-23:

| Server | Was | Now |
|---|---|---|
| `playwright` | `@playwright/mcp@latest` | `@playwright/mcp@0.0.82` |
| `sequential-thinking` | `@modelcontextprotocol/server-sequential-thinking` | `…@2026.8.31` |

**Nothing to do on upgrade.** `npx` fetches the pinned version on next use; no session
config changes and no project file is touched. If you had one of these cached at a newer
version, npx will fetch the pinned one instead — that is the point.

`check-docs.py` now fails CI if any npx-launched server in `.mcp.json` carries a moving tag
(`@latest`, `@next`, …) or no version. Bumping a pin is a plugin patch release; see
SECURITY.md for why the pin exists and CONTRIBUTING.md for how to bump one.


## 2.47.0 — the security review now actually runs where the gate demands it

**Action: none automatic. Expect more reviews to be dispatched, and one previously
impossible promotion to become possible.**

The production done gate has required `verdicts.security == PASS` since 2.4x, and two of the
three commands that close work never dispatched the review:

- **`/wellforge:promote`** ran no trigger check at all, then invoked the production gate.
  An `mvp → production` promotion could only pass if some earlier `/wellforge:implement`
  happened to have reviewed the same code; otherwise it refused with "security review is
  absent" and there was no way to satisfy that from inside promote. It now runs the check at
  the **target** tier before the close, which at `production` always dispatches.
- **`/wellforge:orchestrate`'s mvp pipeline** skipped the check entirely, so the same batch
  was reviewed under `/wellforge:implement` and not under `/wellforge:orchestrate`. The step
  is now in both pipelines.

**More batches will be reviewed than before**, at mvp especially. `config/security-triggers.yml`
gained `auth`, `jwt`, `crypto`, `rbac` and `permission` to `path_contains`, because the
`auth/**` globs need a *directory* called auth: measured at mvp, `src/Authorization.kt`,
`src/OAuthClient.ts`, `src/rbac/policy.ts`, `src/jwt/verify.ts`, `src/crypto/hash.ts` and
`src/permissions/check.ts` all reported "no trigger matched". Known and accepted: `auth`
also matches `author`, so a blog's `src/authors/` costs one unnecessary mid-tier agent.

**A `touch:` glob is now expanded against the working tree.** `--touch 'src/**'` covers
`src/auth/login.ts` but names no trigger, so a literal match missed it and a batch declaring
the broader glob was never reviewed. Declaring a trigger glob still dispatches before any
code exists — the intent half is unchanged.

**A bad `--diff-base` no longer reads as "nothing matched".** It returned `[]` with no note
and exit 0, so a typo'd ref silently turned every match into a miss — the exact failure the
function's own docstring forbade. It now dispatches, prints the git error, and exits 2.
**If you script around this, check for exit 2**: it means the answer rests on incomplete
input, not that something is broken.

**`verdicts.security` is two values, and the reviewer speaks three.** `PASS WITH NOTES` →
`"PASS"` with the low-severity findings in `security.notes[]`; `REVIEW REQUIRED` → `"FAIL"`.
Written through verbatim, `PASS WITH NOTES` failed the gate's `!= "PASS"` test — so a review
that found only low-severity issues blocked the close. `forge-state.py` now reports any
verdict outside `PASS`/`FAIL` under that feature's `problems[]`, so a producer writing the
wrong value is diagnosable instead of surfacing as an unexplained refusal.

**"Not dispatched" is an ABSENT key, never `null`.** `implement.md` said `null`, the
observability skill said absent, and both read identically to `forge-state.py` — which is
why the disagreement survived. Absent is the rule; `security.dispatched: false` records the
fact positively. Old traces containing `null` still read correctly.

`/wellforge:triage` gains a signal for the shape all of this produced: **"QE green, never
security-reviewed"** — a production feature with a QE PASS and no security verdict. It is
the most comfortable-looking failure in the set, because everything on the dashboard is
green.

---

## 2.46.0 — the done gate gained a condition it had always claimed

**Action: none automatic, but expect some closed features to report a blocked gate.**

`/wellforge:done` has always listed "eval is not stale (newer than the last code change)" as
a production condition, and nothing computed it — so an `eval-report.md` written before a
rewrite still counted as a PASS. `forge-state.py` now computes it (eval-report timestamp vs
the newest change outside `specs/` and `.forge/`, from git, falling back to mtime for files
with uncommitted changes) and includes it in `done_gate.failing`.

Consequences for an existing project:

- A feature already `status: done` may now show `GATE blocked` in `/wellforge:status`. That
  is reporting, not a reopening: nothing rewrites a closed feature's status, and the guard
  refuses any edit that would. It means the eval on record predates the current code.
- A feature you are about to close may now be refused where it previously passed. Re-run
  `/wellforge:eval <feature>` and close again. This is the condition doing its job.

Also in this release, and visible to a project:

- **Timestamps are UTC with a `Z`.** `last_activity` and the drift timestamps used to be
  printed in whatever zone the machine was in, unlabelled, so two people comparing the same
  feature read times an hour apart. Anything that parsed the old format needs the new one.
- **Drift now sees the working tree.** An uncommitted `spec.md` edit is drift; an
  uncommitted `tasks.md` re-sync clears it. Both were previously judged on last-commit time
  alone, which got each one backwards.
- **`.forge/runs/` tolerates a malformed trace.** One unreadable file used to raise
  `AttributeError` and exit 1 in `forge-state.py`/`run-report.py` — which the
  `post-spec-guard` hook read as "could not evaluate the done gate" and **allowed the edit
  unverified**. Bad files are now skipped and listed under the envelope's top-level
  `problems[]`; the hook refuses rather than falls open when the script actually crashes.
  If `/wellforge:triage` starts naming a trace file, that file has been silently ignored all
  along — fix or delete it.

---

## 2.43.1 — the notify hook documents where its token comes from

**Action: none.** A comment-only change to `hooks/scripts/notify.sh`, recorded because the
comment was asserting something that had become false: it said the Telegram env file is
"also sourced from ~/.zshrc". `wellforge` 1.3.0 removed that wiring — sourcing the file
from a shell exported `TELEGRAM_BOT_TOKEN` into every process the user starts, Claude
Code's children included, while this hook was already reading the file itself.

Nothing in a project changes. If your shell still has the old `source` line, `wellforge
telegram` offers to remove it.

## 2.43 — the preflight trusts the template for database isolation

**Action: none in the project — but the plugin now behaves differently, and it is worth
knowing which way.**

The `worktree-isolation` skill's shared-state class 1 (databases) used to be "test: isolate,
dev: forbid", which in practice meant a backend batch of ≥2 fell back to **sequential**
dispatch. From template `v0.10.0` the presets isolate the database themselves, so the
preflight now reads `.forge/manifest.json` and decides:

| Your template version | What changes |
|---|---|
| `v0.10.0` or later | class 1 counts as **isolated**; parallel dispatch is available for backend batches that were previously serialized |
| earlier, adopted, or no manifest | **nothing changes** — the old rule still applies and batches stay sequential. Take `docs/TEMPLATE-MIGRATIONS.md` (wellforge repo) `v0.10.0` to get the isolation |

The skill also stopped recommending `basename` as the isolation key (it collides across
repos, is not a legal database identifier, and yields no port offset) in favour of
`sha256(checkout path)`, which is what the presets ship.

`/wellforge:upgrade` additionally reads the new
`docs/TEMPLATE-MIGRATIONS.md` (wellforge repo) alongside this file, so template-side
notes reach a project the same way plugin-side ones already did.

## 2.42 — the plugin is installable, and projects declare it

**Action: automatic, one field + one settings block.**

Three things changed that a project can absorb:

1. **`.forge/manifest.json` → `plugin.marketplace`.** The `plugin` object gains a field
   recording where the plugin came from: `wellforge@wellforge` (a marketplace install,
   reproducible by a teammate) or `local` (a `--plugin-dir` checkout, reproducible by
   nobody). `/wellforge:upgrade` writes it; **absent means "recorded before 2.42, unknown"**
   and is reported as unknown, never as a mismatch.

2. **`.claude/settings.json` → the plugin declaration.** New scaffolds carry
   `extraKnownMarketplaces.wellforge` and `enabledPlugins["wellforge@wellforge"]`, so a
   clone states which plugin it expects instead of relying on onboarding lore. Existing
   projects: `/wellforge:upgrade` re-renders the file (**merge** — never drop a project's
   own `permissions.allow` entries or its other marketplaces). `/wellforge:doctor` WARNs
   when it is missing.

   What this does **not** do is install anything. Whether Claude Code installs, prompts, or
   merely enables-once-present from a project-scope setting is undocumented, so treat the
   block as a declaration a human and doctor can read, not as automation.

3. **The plugin is now installed from git, not a path.** `.claude-plugin/marketplace.json`
   points at a `git-subdir` source pinned to a `plugin-vX.Y.Z` tag. **If you installed
   WellForge by registering a local checkout as a marketplace, that install is
   machine-local** — `/wellforge:doctor` now says so. Re-point it once:

   ```bash
   claude plugin marketplace add matteocodogno/wellforge
   claude plugin install wellforge@wellforge --scope user
   ```

**Worth knowing:** the plugin cache is keyed by version
(`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`), so an edit to an installed
plugin without a version bump takes effect for nobody, including the person who made it.

## 2.38 — session-injection budget

**Action: none.** `config/budget.yml` and `check-budget.py` govern the plugin's own
descriptions. Nothing in a project changes.

## 2.37 — lifecycle rules enforced by a hook

**Action: automatic, informational.** A new PostToolUse hook (`post-spec-guard.sh`) refuses
edits that write `status: done` without a passing gate, lower `rigor:`, or reopen a closed
feature. It ships with the plugin and needs nothing installed in the project.

**Worth knowing:** a project whose specs have frontmatter that predates the schema — a typo'd
status, a `superseded` with no `superseded_by` — will start seeing the hook refuse *edits to
those files*. Run `forge-state.py` (or `/wellforge:doctor`) to list them, and fix the
frontmatter; the guard is reporting real breakage, not new strictness.

## 2.36 — deterministic feature state

**Action: automatic.** `forge-state.py` reads `specs/` and `.forge/runs/` and validates
frontmatter against `config/spec-frontmatter.schema.json`. No project file changes.

**Worth knowing:** as above, pre-existing invalid frontmatter becomes *visible* for the first
time in `/wellforge:status` and `/wellforge:triage` (as `problems[]`). That is discovery, not
regression.

## 2.33 — `.forge/runs/` trace envelope gained `rigor_recorded`

**Action: automatic, backward compatible.** Traces written by older plugins have no
`rigor_recorded` field; `run-report.py` treats its absence as "the run matched the feature's
recorded tier", which is what it meant. Nothing to rewrite.

## 2.31 — `.forge/runs/.events.jsonl` should be gitignored

**Action: one line, applied by `/wellforge:upgrade`.** The raw token-event buffer is
transient and was never meant to be committed; scaffolds from 2.31 on ignore it. Older
projects may have it tracked.

```gitignore
.forge/runs/.events.jsonl
```

If the file is already tracked: `git rm --cached .forge/runs/.events.jsonl`. The semantic
`.forge/runs/*.json` traces stay committed — they are the audit trail.

---

## Adding an entry

Add it in the **same commit** as the plugin change that needs it, at the top, under the minor
being released. An entry written later is one an upgrade already skipped.
