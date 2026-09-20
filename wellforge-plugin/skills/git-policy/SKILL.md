---
name: git-policy
description: >
  WellForge git policy — linear history (no merge commits) and Conventional Commits, in every
  WellForge repo including generated ones. Use whenever writing a commit message, integrating
  a branch, opening or merging a PR, setting up a fresh clone, fixing a rejected commit or a
  red commit-lint / linear-history gate, or configuring branch protection. Authoritative
  reference for the commit format, the four enforcement layers (local config, committed
  hooks, CI gates, branch protection), the rebase-not-merge integration rule, and what to do
  when a gate rejects your commit.
---

# Git policy — linear history and Conventional Commits

Two rules, non-negotiable in every WellForge repo and every project WellForge generates:

1. **Linear history.** No merge commits. Rebase onto the base branch, integrate with
   `--ff-only`, and land PRs as squash or rebase.
2. **Conventional Commits.** Every commit subject is `type(scope)!: description`.

They are not style preferences. A linear history makes `git log` a readable sequence of
changes and `git bisect` meaningful; Conventional Commits is what `/wellforge:release`
derives the version bump and CHANGELOG from, so a malformed subject silently produces a
wrong release.

## The commit format

```
<type>(<optional scope>)<optional !>: <description>

<optional body>

<optional footers>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
`revert`. `!` (or a `BREAKING CHANGE:` footer) marks a breaking change and drives a major
bump. Merge, revert, fixup, squash and amend commits are exempt — git generates them.

- **`feat` and `fix` move the version**, everything else does not. Choose the type by what
  the change *does* to users, not by how much work it was.
- The description says what changed, in the imperative. The body says **why**, and is where
  the failure shape belongs — the thing a future reader needs and `git log --oneline` can
  never carry.
- Reference the task and spec when there is one: `feat(export): add CSV serializer (T1,
  specs/002)`.

## Integration — rebase, never merge

```bash
git fetch origin
git rebase origin/main            # replay your work on top
git switch main && git merge --ff-only <branch>
```

`git merge --no-ff` is refused by config, by hook, and by CI. If `--ff-only` fails with
`fatal: Not possible to fast-forward`, the branch was not rebased onto the current tip —
rebase again and retry. That refusal is the policy working; reaching for a flag that forces
the merge through is the one response that is always wrong.

For a parallel batch integrating several worktree branches, [`worktree-isolation`](../worktree-isolation/SKILL.md) owns the
protocol (the rebase runs **inside** each worktree — the main tree cannot rebase a branch
that is checked out elsewhere).

## Four enforcement layers

Each catches what the previous one misses; none is sufficient alone.

| Layer | What it is | Catches |
|---|---|---|
| **Local config** | `merge.ff=only`, `pull.rebase=true`, `rebase.autoStash=true` | A merge commit before it exists. Per-clone, so it ships as a script, not a file. |
| **Committed hooks** | `gates/hooks/commit-msg`, `gates/hooks/pre-merge-commit` | A malformed subject at commit time, when fixing it is free. |
| **CI gates** | `commit-lint.yml`, `linear-history.yml`, called at **every** rigor tier | What a contributor's unconfigured clone let through. History hygiene is tier-independent — unlike coverage, it cannot be repaired after the fact without rewriting published history. |
| **Branch protection** | `required_linear_history`, `allow_merge_commit=false` | The merge button in the GitHub UI, which no local setting can reach. |

Run **`./scripts/setup-git-policy.sh`** once per clone (generated projects: `mise run
git-policy`) — it applies the config and installs the hooks. A fresh clone has none of it.

## When a gate rejects you

- **`commit-msg` hook rejected the subject** → `git commit --amend` with a conforming
  subject. The validator prints the expected shape and the type list.
- **`linear-history` CI is red** → the PR range contains a merge commit. Rebase the branch
  (`git rebase origin/main`) and force-push **with `--force-with-lease`**, which refuses if
  the remote moved under you. Plain `--force` is blocked by the plugin's bash guard for that
  reason.
- **`commit-lint` CI is red on an old commit** → rebase interactively and reword it. Fixing
  the tip alone leaves the range red.
- **You are mid-rebase and lost** → `git rebase --abort` returns you to where you started.
  Nothing is lost; the branch is unchanged until the rebase completes.

## What this does not cover

Squash-merging a PR in the GitHub UI produces one commit whose subject is the **PR title** —
so the PR title must be a Conventional Commit too. Branch protection cannot enforce that;
review it like any other line of the change.
