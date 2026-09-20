---
name: worktree-isolation
description: >
  WellForge parallel-safety discipline — what a git worktree isolates, what it does NOT, and
  the preflight before dispatching a parallel batch. Use whenever ≥2 dependency-independent
  agents are about to be dispatched (`/wellforge:implement` Step 3, `/wellforge:orchestrate`
  implementation stages), whenever an agent in a worktree hits a failure it cannot explain,
  and whenever deciding if a batch is safe to parallelize at all. Authoritative for the
  touches-nothing-outside-itself rule, the shared-state enumeration and its three
  dispositions, the env carry-in step, file-overlap DAG edges, and the isolate → constrain →
  integrate → reconcile → prune protocol.
---

# Worktree isolation — a worktree touches nothing outside itself

**The rule:**

> **A worktree touches nothing outside itself except by explicit allowance.**

An allowance is a resource that appeared in the preflight below and was given one of three
dispositions: **isolate** (it gets a worktree-derived name of its own), **forbid** (no worktree
may reach it), or **accept** (it was *shown* to be safe under concurrent access — stated out
loud, never assumed). A resource that is present and has none of the three is not an allowance;
it is the reason the batch runs sequentially instead.

## Why this is a rule and not a list of fixes

`isolation: "worktree"` isolates exactly one thing: **the checkout**. Every other resource a
project reaches is addressed by a name that has nothing to do with which checkout you are
standing in — a database name, a port number, a compose project, a cache path, a cloud stack, a
migration counter. Two worktrees resolve those names identically and land on the same object.

Every failure of this class has the same shape: **two checkouts, one name, one object.** That is
why the instances are not worth patching individually — the two found in a real pilot batch (a
shared test database dropped mid-run by a sibling; a migration applied to the shared dev database
from a branch that was later discarded) were discovered separately, days apart, and are the same
defect. Fixing those two leaves the class intact.

**The tell.** An agent working inside a worktree gives some resource a unique name of its own to
get its work done. That workaround is the isolation the harness should have provided, and it
means the same resource is unisolated for every other agent that did not think of it.

## The enumeration

Walk this list against the project in front of you. It is the checklist the preflight runs.

| # | Shared-state class | How it's addressed (why worktrees collide) | Default disposition |
|---|---|---|---|
| 1 | **Databases** — test, dev, any named instance | host + port + database name, identical from every checkout | **already isolated** by presets from template `v0.10.0` (check the manifest — see below); otherwise test: **isolate** · dev: **forbid** |
| 2 | **Migration history** — the applied-migrations table | travels with the database it lives in | with its database |
| 3 | **Ports** — dev server, API, debugger, DB forward | a fixed number in config or compose | **isolate** (offset) or **forbid** concurrent servers |
| 4 | **Containers, compose projects, volumes, networks** | compose project name defaults to the directory (differs), but an explicit `container_name`, a fixed host port, or a named volume does not | **isolate** (explicit per-key project name) |
| 5 | **Credential stores & secret-backed env** — `.env*`, `.mise.local.toml`, `op://` refs, keychain, cloud CLI default profile / ADC | gitignored, so not *shared* — **absent**. See carry-in below | read: **carry-in** · write: **forbid** |
| 6 | **Caches & tool state outside the tree** — `~/.m2`, `~/.gradle`, the pnpm store, turbo/nx cache | built for concurrent access | **accept** — except any key the project chooses itself, which is **isolate** |
| 7 | **Sequence-numbered artifacts** — migration files, ADR numbers, spec numbers | the shared resource is the **counter**, not a file | **forbid** concurrency (a DAG edge, see below) |
| 8 | **External services & tenancies** — staging APIs, queues, buckets, cloud projects, Pulumi stacks, GitHub issues/labels | one mutable tenancy, same address from every checkout | write: **forbid** · read: **accept** |
| 9 | **Machine-global files & sockets** — fixed `/tmp` paths, lockfiles, sockets, `core.hooksPath` | a literal path, shared by construction | **isolate** (key in the path) or **forbid** |
| 10 | **The repository outside your checkout** | worktrees share ONE `.git`: refs, tags, stash, local `git config`, hooks. You own only your branch, index and HEAD | **forbid** — no tags, no `git config` writes, no stash, no deleting others' branches |

Class 7 deserves its own note because it is the one that looks safe. Two worktrees each compute
"the next migration is `0007`" and each write a *different* file. Nothing conflicts, the merge is
clean, and the numbering is now wrong — the failure surfaces later, against a database, as an
ordering nobody can explain.

Class 1's **dev** entry is a default, not a settled question: whether a worktree may reach the
dev database at all is a **project-level** decision and belongs in the project's own task
definitions (see *Where the guard lives*). Until a project states otherwise, forbid it.

The list is a floor, not a ceiling. A project reaching something these ten classes don't name
gets classified the same way, by the same rule — the rule is what generalises.

## The isolation key

One deterministic value, unique per worktree, stable for that worktree's whole life.

**In a project scaffolded from template `v0.10.0` or later, do not compute this yourself** — the
preset ships it, and a second definition is a second answer:

```bash
sh .wellforge/worktree-id.sh id       # main | wt<hash8>
sh .wellforge/worktree-id.sh port     # 5432 | 5432 + (hash mod 1000)
sh .wellforge/worktree-id.sh linked   # no | yes
mise run wt:info                      # all of it, plus the resolved database and compose project
```

The key is `sha256(git rev-parse --show-toplevel) | cut -c1-8`. For anything older, or a project
that is not WellForge-scaffolded, compute the same thing the same way:

```bash
# Am I in a linked worktree?  (git-dir and git-common-dir diverge only there)
[ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ] && echo linked

WF_WORKTREE_ID="wt$(printf %s "$(git rev-parse --show-toplevel)" | sha256sum | cut -c1-8)"
```

**Hash the path; do not use its basename.** A basename is not unique (two repos each with a
`feature-auth` worktree collide), it is not a legal identifier in every place the key is spent
(a database name, a compose project), and it is not a number, so no port offset can be derived
from it. Never derive the key from a timestamp or a random value either: a re-run inside the same
worktree must resolve to the *same* database, port and container, or cleanup silently leaks
resources and the second run is not reproducible.

See `docs/adr/0002-per-worktree-databases.md` for the decision and its failure shapes.

## The preflight — before dispatching a batch of ≥2

**Step 0 — is the database already isolated?** Read the project's template version and let it
answer class 1 for you, instead of re-deriving it:

```bash
jq -r '.version' .forge/manifest.json          # scaffolded projects; adopted ones have no template
```

| Template version | Class 1 disposition | What you write in the preflight |
|---|---|---|
| `v0.10.0` or later, `db != none` | **isolated by the preset** | `test database   isolate    Testcontainers (ephemeral, per run)`<br>`dev database    isolate    ${WF_DB_NAME} — per-checkout, guarded by mise run db:guard` |
| earlier, or adopted, or no manifest | **not isolated** | the old rule: test **isolate**, dev **forbid** — and if you cannot isolate, the batch is sequential |

Confirm rather than assume — `mise run wt:info` in the worktree prints the database, port and
compose project it actually resolved, and a project can always have overridden `WF_DB_NAME` in
`.mise.local.toml`. A version number says what the template shipped; `wt:info` says what this
checkout will really use, and only the second one is evidence.

Then walk the rest of the enumeration against this project — read the compose file, the env/mise
config, the migration directory, and the batch's own `touch:` lists — and give every class that is
**present** a disposition. State it compactly before dispatching:

```
worktree preflight — 3 agents, batch [T8, T10, T12]     (template v0.10.0 — db isolated by preset)
  test database   isolate    Testcontainers, ephemeral per run
  dev database    isolate    byline_wt<hash> per checkout + `mise run db:guard`
  ports           isolate    5432 + (hash mod 1000), per checkout
  secret env      carry-in   .mise.local.toml, .env.local → verified in all 3
  migrations      order      T8, T12 both create db/migrations/* → edge added, T12 after T8
  git refs        forbid     agents commit on their own branch only
```

**Unclassified is not a pass.** A class that is present and is neither isolated nor forbidden nor
demonstrably safe means the batch does **not** run in parallel: fall back to sequential, and say
which class forced it. The trade is not close — sequential costs a few minutes of wall-clock; an
under-isolated batch costs the whole run *and* produces confident wrong diagnoses that can lead an
agent to "fix" working code.

## Carry-in — the env that simply isn't there

A fresh worktree contains the tracked tree at HEAD and nothing else. Everything gitignored is
missing, and by WellForge policy env config *is* gitignored (`.env*`, `.mise.local.toml`, service
account files). So env does not fail loudly in a worktree — **it resolves to nothing**, and the
failure surfaces much deeper, inside application code, looking exactly like broken code.

1. **Carry the files in.** Enumerate what the main tree has and the worktree won't
   (`git status --ignored --porcelain` at the repo root, filtered to config/env files), and copy
   them into each worktree. Do not carry build output or `node_modules` — those are rebuilt. This
   adds no exposure: same machine, same repo, same user, same secrets already on disk.
2. **Verify — do not assume.** Resolve the required env inside the worktree the way the app
   resolves it (`mise env`, the config module's own parse/validate step) and diff it against the
   main tree. **Any variable that resolves in the main tree and not in the worktree is a hard
   stop**, not a warning: fix the carry-in, or dispatch sequentially. Never dispatch an agent into
   a worktree whose environment is thinner than the tree those tests were last green in.
3. **A file is only half of a secret reference.** A value fetched at run time from a credential
   store (`op://…`) also needs that store reachable from a **non-interactive** process. Check the
   resolution, not the presence of the reference.
4. **Check the derived variables too, not only the carried-in ones.** From template `v0.10.0`
   the preset *computes* `WF_DB_NAME`, `WF_DB_PORT` and `COMPOSE_PROJECT_NAME` from the checkout
   path, so they are never missing the way a copied file can be — but they can be **wrong**, and
   wrong in a way that reads as normal:

   | What you see | What it means |
   |---|---|
   | `WF_DB_NAME` identical in two worktrees | mise is not resolving the `[env]` block — usually the worktree was never `mise trust`ed, so every derived value fell back to the shell's. **Hard stop**: this is the collision, not a warning about it. |
   | `WF_DB_NAME` with no `_wt…` suffix inside a linked worktree | same cause, or a `.mise.local.toml` that pins it. Ask which before dispatching. |
   | `mise run db:guard` refuses | an override is pointing this checkout at another database. Report it as an environment fault; do **not** set `WF_DB_NAME` to silence it. |

   `mise trust` is the one carry-in step these variables need — a fresh worktree is untrusted, and
   an untrusted config resolves to nothing rather than failing loudly. Run `mise run wt:info` in
   each worktree and diff the results across the batch: two agents with one database name is the
   defect this whole skill exists to prevent, and it is visible in one line before any work starts.

An agent that meets an unresolved variable reports an **environment fault** and stops. It does not
diagnose the code, and it never reports "pre-existing breakage" on that evidence — see
[`systematic-debugging`](../systematic-debugging/SKILL.md).

## File overlap is a DAG edge

`deps:` records **logical** order — what must exist before what. It does not record two tasks
writing the same file, and two tasks can be logically independent and still unsafe to run
concurrently. Both are edges.

**Effective batching graph = declared `deps:` ∪ overlap of `touch:`.**

- Compute it *before* batching, from the `touch:` list every task carries ([`spec-driven`](../spec-driven/SKILL.md)).
- **Glob overlap counts.** Two tasks that both touch `backend/src/db/migrations/*` collide on the
  counter (class 7) even though neither names the other's file.
- **Report the edges you added** — "T8 and T12 both touch `db/migrations/*` → serialized" — the
  same way drift is surfaced. A silently different graph is not auditable.
- Where two tasks are inseparable rather than merely ordered (both must create in one numbered
  series as a single unit), the right answer is one task, not two ordered ones. That's a
  `/wellforge:tasks` re-sync.

This *prevents* the collision that merge-conflict detection *catches*. Keep both: the
merge check remains the backstop for overlap the `touch:` lists failed to declare.

## The protocol

1. **Isolate.** Spawn each agent with `isolation: "worktree"` — a fresh worktree + branch off the
   current HEAD, so it already contains the spec, `tasks.md`, and every task integrated earlier in
   this run. Set `worktree.baseRef: "head"` in settings so worktrees branch from HEAD, not the
   remote default (see the plugin `settings-snippet.jsonc`). Run the **preflight** and the
   **carry-in** before any agent starts work.
2. **Constrain the agent.** In each parallel agent's prompt: *commit your code with the standard
   message but **do NOT edit `tasks.md`*** (checkboxes are reconciled centrally, killing the one
   guaranteed conflict); *stay inside your worktree — the allowances for this batch are `<the
   preflight lines>`, and anything outside them is an environment fault to report, not to work
   around*; and *end your report with `WORKTREE-BRANCH: <git branch --show-current>` and
   `COMMITS: <n>`, and `WORKTREE-PATH: <git rev-parse --show-toplevel>`*. The dispatch result
   usually also surfaces the agent's worktree branch and path in its metadata; the self-reported
   lines are the portable fallback — use whichever you get. **The path is not optional**:
   integration (step 3) rebases inside the worktree, which git will not let you do from the
   main tree.
3. **Integrate — rebase + fast-forward, never a merge commit.** WellForge repos keep a **linear
   history** (`gates/README.md` → "Linear history gate"), so integrate each branch into the feature
   branch one at a time, in a deterministic order:

   ```bash
   # 1. Rebase INSIDE the worktree. Running `git rebase <feature> <wt-branch>` from the main
   #    tree fails — the branch is checked out in the worktree, and git refuses:
   #      fatal: '<wt-branch>' is already used by worktree at '<path>'
   git -C <worktree-path> rebase <feature-branch>

   # 2. Fast-forward the feature branch from the main tree. Safe while the worktree still
   #    exists: this advances <feature-branch>, which is not the branch checked out there.
   git switch <feature-branch>
   git merge --ff-only <worktree-branch>           # pointer move — no merge commit
   ```

   **You need the worktree's PATH, not just its branch.** Take it from the agent's
   `WORKTREE-PATH:` line (step 2) or derive it:

   ```bash
   git worktree list --porcelain \
     | awk -v b="refs/heads/<worktree-branch>" '/^worktree /{p=$2} $0=="branch "b{print p}'
   ```

   If the worktree is already gone (pruned early), the rebase can run in the main tree —
   `git rebase <feature-branch> <worktree-branch>` only fails while the branch is checked out
   somewhere. Integrate first, prune after (step 5); that order also keeps the agent's
   environment available if the rebase conflicts.

   **`--ff-only` refusing is information, not an obstacle.** `fatal: Not possible to
   fast-forward` means the branch was never rebased onto the *current* tip of
   `<feature-branch>` — usually because an earlier track integrated meanwhile. Rebase it again
   in its worktree and retry. Do **not** reach for `--no-ff`, `--no-edit`, or any other flag
   that gets the merge through: that is exactly the merge commit the repo forbids
   (`merge.ff = only`, the `pre-merge-commit` hook, and the `linear-history` CI gate), and the
   refusal is what protects it. The task's own `feat(<scope>): … (T<n>, specs/NNN)` commits
   carry the history — no integration commit is needed, and none may be created.
4. **Reconcile the checkboxes centrally.** Once every track is integrated, check the boxes for all
   completed tasks in `tasks.md` in **one** commit on the feature branch.
5. **Prune.** Remove the merged worktrees and their branches (`git worktree remove`,
   `git branch -d`), and drop anything the preflight *isolated* (per-worktree databases,
   containers, volumes) — isolation you don't clean up is a leak, and the isolation key is
   deterministic precisely so cleanup can find it.

### Collisions

A conflict during step 3 is a **collision**, not a routine merge: two tasks the DAG called
independent touched the same file, so they were never independent. Abort the rebase **in the
worktree where it is running** (`git -C <worktree-path> rebase --abort`), **surface it like
drift** — name the two tasks and the colliding files —
and resolve by adding the missing edge (`/wellforge:tasks` re-sync) and re-running the later task
in the now-integrated tree. Never auto-resolve code conflicts silently. Record it in
`collision_events` ([`observability`](../observability/SKILL.md)).

A collision after this skill shipped is also a signal about the *inputs*: the tasks' `touch:` lists
did not describe what the tasks actually did. Say so when you surface it.

## Symptoms — under-isolation is diagnosable

| What you see | Likely class |
|---|---|
| A large number of tests fail suddenly, mid-run, having passed minutes ago | 1 — a sibling worktree dropped/recreated the shared database. On `v0.10.0`+ this should be impossible: check `mise run wt:info` in both worktrees, because it means the derivation did not take |
| Tests fail in the worktree but pass on the integrated branch | 5 — carry-in missing; env resolved to nothing |
| "Port already in use" / a dev server answering with another branch's code | 3 |
| Migration history has a row for a file that doesn't exist in the tree | 1 + 7 — a discarded branch migrated a shared database |
| Green solo, red only when the batch runs in parallel | any of 1, 3, 4, 8 |
| A tag/stash/branch appearing that no agent claims | 10 |

Every row is an **environment fault**. It gets reported as one and routed — it is never fixed by
editing application code, and it never justifies a "pre-existing breakage" verdict.

## Where the guard lives

- **Dispatch-time preflight and carry-in → the plugin** (this skill). It knows a batch is about
  to run and can refuse to parallelize.
- **A guard that refuses to act on another checkout's database** (a migration task, a deploy task,
  a seed task) → the **project's own task definitions**, shipped by the template. That is the only
  layer where the guard is present for a human running the command by hand, and where it cannot be
  forgotten by whichever agent happens to dispatch. The plugin cannot enforce it, and should not
  pretend to.

  **From template `v0.10.0` this is shipped, not aspirational**: `mise run db:guard` compares the
  database anything is about to act on against the one derived for this checkout and refuses on a
  mismatch. It is wired into `dev`, `test` and every migration task in both the JVM and Hono
  presets, so the refusal happens before the work, not after. Two limits worth knowing: it sees
  the *configured* target (`DATABASE_URL` / `SPRING_DATASOURCE_URL`), so a connection string built
  by hand inside application code is invisible to it; and setting `WF_DB_NAME` makes it agree with
  you, which is the deliberate escape hatch — an agent must never reach for it to get past a
  refusal.

## Fallback and recording

- **Fallback.** If worktree isolation is unavailable (older Claude Code, the option rejected), or
  the preflight left a class unclassified, dispatch the batch **sequentially** in the main tree,
  each agent committing and checking its own box. State which mode you used and why.
- **Recording.** Record the isolation mode, each isolated agent's branch (`worktree`), any
  `collision_events`, and any environment faults in the run trace per [`observability`](../observability/SKILL.md). A batch
  that fell back to sequential records *why* — the preflight line that forced it is the finding.
