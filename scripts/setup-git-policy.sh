#!/usr/bin/env bash
# Apply the WellForge git policy to this clone. Idempotent — safe to re-run.
#
#   linear history      : no merge commits, ever. Branches rebase onto main and integrate
#                         fast-forward. Enforced in CI by linear-history.yml.
#   conventional commits: type(scope)!: description. Enforced in CI by commit-lint.yml.
#
# Git config is per-clone and lives outside the repo, so it can't be shipped — every clone of
# every WellForge repo runs this once. The committed hooks + CI gates are the durable half.
#
# Usage: ./scripts/setup-git-policy.sh   (from anywhere inside the repo)
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"

echo "WellForge git policy → $root"

# ── Config: make the local defaults match the policy ────────────────────────────────────────
git config merge.ff only          # `git merge` fast-forwards or fails — never a merge commit
git config pull.rebase true       # `git pull` rebases instead of merging origin back in
git config pull.ff only           # ... and refuses if the rebase isn't clean-forwardable
git config rebase.autoStash true  # rebasing with a dirty tree stashes/restores instead of erroring
git config branch.autoSetupRebase always   # new tracking branches inherit rebase-on-pull
echo "  config  merge.ff=only pull.rebase=true rebase.autoStash=true"

# ── Hooks: only when this repo carries gates/hooks (the wellforge repo itself) ───────────────
hooks_dir=$(git rev-parse --git-path hooks)
# git does not guarantee this directory exists — a clone made with a template that has no
# hooks, or one whose .git/hooks was cleaned, simply has none, and `ln -s` into a missing
# directory fails with a message that reads like a permissions problem. Found the first time
# the pre-push hook was installed into this very repo.
mkdir -p "$hooks_dir" || { echo "  could not create $hooks_dir — hooks NOT installed" >&2; hooks_dir=""; }
install_hook() {
  src="gates/hooks/$1"
  [ -f "$src" ] || return 0
  [ -n "$hooks_dir" ] || return 0
  ln -sf "$root/$src" "$hooks_dir/$1"
  chmod +x "$src"
  echo "  hook    $1 → $src"
}
install_hook commit-msg
install_hook pre-merge-commit
# Runs the full self-test before a RELEASE TAG is pushed, and only then — branch pushes
# stay fast. plugin-v2.49.0 and cli-v1.5.0 were both tagged from a red tree.
install_hook pre-push

echo "done. CI (commit-lint.yml, linear-history.yml) enforces the same rules unskippably."
