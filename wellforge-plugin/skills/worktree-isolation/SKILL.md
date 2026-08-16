---
name: worktree-isolation
description: >
  WellForge parallel-safety discipline — what a git worktree isolates, what it does NOT, and the
  preflight that must run before dispatching a parallel batch. Use whenever ≥2 dependency-
  independent agents are about to be dispatched (`/wellforge:implement` Step 3,
  `/wellforge:orchestrate` implementation stages), whenever an agent working in a worktree hits
  a failure it cannot explain, and whenever deciding if a batch is safe to parallelize at all.
  Authoritative reference for the touches-nothing-outside-itself rule, the shared-state
  enumeration and its three dispositions, and the
  isolate → constrain → integrate → reconcile → prune protocol.
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
why the instances are not worth patching individually — the two found in the Phase 7 pilot (a
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
| 1 | **Databases** — test, dev, any named instance | host + port + database name, identical from every checkout | test: **isolate** · dev: **forbid** |
| 2 | **Migration history** — the applied-migrations table | travels with the database it lives in | with its database |
| 3 | **Ports** — dev server, API, debugger, DB forward | a fixed number in config or compose | **isolate** (offset) or **forbid** concurrent servers |
| 4 | **Containers, compose projects, volumes, networks** | compose project name defaults to the directory (differs), but an explicit `container_name`, a fixed host port, or a named volume does not | **isolate** (explicit per-key project name) |
| 5 | **Credential stores & secret-backed env** — `.env*`, `.mise.local.toml`, `op://` refs, keychain, cloud CLI default profile / ADC | gitignored, so not *shared* — **absent** from a fresh worktree | read: **must be provided** · write: **forbid** |
| 6 | **Caches & tool state outside the tree** — `~/.m2`, `~/.gradle`, the pnpm store, turbo/nx cache | built for concurrent access | **accept** — except any key the project chooses itself, which is **isolate** |
| 7 | **Sequence-numbered artifacts** — migration files, ADR numbers, spec numbers | the shared resource is the **counter**, not a file | **forbid** concurrency (two such tasks are ordered, never batched) |
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

One deterministic value, unique per worktree, stable for that worktree's whole life:

```bash
# Am I in a linked worktree?  (git-dir and git-common-dir diverge only there)
[ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ] && echo linked

# The key — the worktree's own directory name
WF_WORKTREE_ID="$(basename "$(git rev-parse --show-toplevel)")"
```

Derive it from the worktree path or branch — never from a timestamp or a random value. A re-run
inside the same worktree must resolve to the *same* database, the same port, the same container,
or cleanup silently leaks resources and the second run is not reproducible.

## The preflight — before dispatching a batch of ≥2

Walk the enumeration against this project — read the compose file, the env/mise config and
the migration directory — and give every class that is **present**
a disposition. Then state it compactly before dispatching:

```
worktree preflight — 3 agents, batch [T8, T10, T12]
  test database   isolate    byline_test_${WF_WORKTREE_ID}
  dev database    forbid     no task in this batch migrates dev
  ports           n/a        no dev server in this batch
  git refs        forbid     agents commit on their own branch only
```

**Unclassified is not a pass.** A class that is present and is neither isolated nor forbidden nor
demonstrably safe means the batch does **not** run in parallel: fall back to sequential, and say
which class forced it. The trade is not close — sequential costs a few minutes of wall-clock; an
under-isolated batch costs the whole run *and* produces confident wrong diagnoses that can lead an
agent to "fix" working code.

## The protocol

1. **Isolate.** Spawn each agent with `isolation: "worktree"` — a fresh worktree + branch off the
   current HEAD, so it already contains the spec, `tasks.md`, and every task integrated earlier in
   this run. Set `worktree.baseRef: "head"` in settings so worktrees branch from HEAD, not the
   remote default (see the plugin `settings-snippet.jsonc`). Run the **preflight** before any agent starts
   work.
2. **Constrain the agent.** In each parallel agent's prompt: *commit your code with the standard
   message but **do NOT edit `tasks.md`*** (checkboxes are reconciled centrally, killing the one
   guaranteed conflict); *stay inside your worktree — the allowances for this batch are `<the
   preflight lines>`, and anything outside them is an environment fault to report, not to work
   around*; and *end your report with `WORKTREE-BRANCH: <git branch --show-current>` and
   `COMMITS: <n>`*. The dispatch result usually also surfaces the agent's worktree branch in its
   metadata; the self-reported line is the portable fallback — use whichever you get.
3. **Integrate — rebase + fast-forward, never a merge commit.** WellForge repos keep a **linear
   history** (`gates/README.md` → "Linear history gate"), so integrate each branch into the feature
   branch one at a time, in a deterministic order:

   ```bash
   git rebase <feature-branch> <worktree-branch>   # replay the task's commits on top
   git switch <feature-branch>
   git merge --ff-only <worktree-branch>           # pointer move — no merge commit
   ```

   `git merge --no-ff` is **forbidden**: the repo sets `merge.ff = only`, a `pre-merge-commit` hook
   refuses merge commits, and the `linear-history` CI gate fails the PR. The task's own
   `feat(<scope>): … (T<n>, specs/NNN)` commits carry the history — no integration commit is
   needed, and none may be created. (Merge-back that *does* need a message must use git's default
   via `--no-edit`; the Conventional-Commits `commit-msg` hook rejects a hand-written merge
   subject.)
4. **Reconcile the checkboxes centrally.** Once every track is integrated, check the boxes for all
   completed tasks in `tasks.md` in **one** commit on the feature branch.
5. **Prune.** Remove the merged worktrees and their branches (`git worktree remove`,
   `git branch -d`), and drop anything the preflight *isolated* (per-worktree databases,
   containers, volumes) — isolation you don't clean up is a leak, and the isolation key is
   deterministic precisely so cleanup can find it.

### Collisions

A conflict during step 3 is a **collision**, not a routine merge: two tasks the DAG called
independent touched the same file, so they were never independent. Abort the rebase
(`git rebase --abort`), **surface it like drift** — name the two tasks and the colliding files —
and resolve by adding the missing edge (`/wellforge:tasks` re-sync) and re-running the later task
in the now-integrated tree. Never auto-resolve code conflicts silently. Record it in
`collision_events` ([[observability]]).

## Where the guard lives

- **Dispatch-time preflight → the plugin** (this skill). It knows a batch is about
  to run and can refuse to parallelize.
- **A guard that refuses to run at all from a linked worktree** (a migration task, a deploy task,
  a seed task) → the **project's own task definitions**, shipped by the template. That is the only
  layer where the guard is present for a human running the command by hand, and where it cannot be
  forgotten by whichever agent happens to dispatch. The plugin cannot enforce it, and should not
  pretend to.

## Fallback and recording

- **Fallback.** If worktree isolation is unavailable (older Claude Code, the option rejected), or
  the preflight left a class unclassified, dispatch the batch **sequentially** in the main tree,
  each agent committing and checking its own box. State which mode you used and why.
- **Recording.** Record the isolation mode, each isolated agent's branch (`worktree`) and any
  `collision_events` in the run trace per [[observability]]. A batch
  that fell back to sequential records *why* — the preflight line that forced it is the finding.
