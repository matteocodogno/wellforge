# Plugin migrations — project-side changes, per plugin minor

`.forge/manifest.json` (or `.forge/adoption.json`) records which **plugin** version last set
a project up. This file records what changed on the *project* side since — the things a
newer plugin expects to find that an older one never created.

**Read by `/wellforge:upgrade`**, which compares the recorded `plugin.version` against the
running one and applies or surfaces every entry in between. `/wellforge:doctor` reports the
gap without acting on it.

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
| earlier, adopted, or no manifest | **nothing changes** — the old rule still applies and batches stay sequential. Take [`TEMPLATE-MIGRATIONS.md`](TEMPLATE-MIGRATIONS.md) `v0.10.0` to get the isolation |

The skill also stopped recommending `basename` as the isolation key (it collides across
repos, is not a legal database identifier, and yields no port offset) in favour of
`sha256(checkout path)`, which is what the presets ship.

`/wellforge:upgrade` additionally reads the new
[`TEMPLATE-MIGRATIONS.md`](TEMPLATE-MIGRATIONS.md) alongside this file, so template-side
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
