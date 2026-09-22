# Releasing the `wellforge` CLI

The procedure for the `cli-vX.Y.Z` series. **Why** it is a series of its own, and the rules
it shares with the other three, are in [`VERSIONING.md`](VERSIONING.md) — that page is the
authority on versioning; this one is the authority on the steps.

`scripts/release-cli.sh` performs all of this and prints each step as it goes, so the
script and this file cannot drift far: if they disagree, the script is what ran.

```bash
scripts/release-cli.sh patch            # plan only — prints every step, changes nothing
scripts/release-cli.sh patch --execute  # do it
```

## Why it is two commits

The Formula pins the sha256 of GitHub's generated tarball. That tarball **does not exist
until the tag is pushed**, and it is **not reproducible locally** — measured on the
existing `v0.9.0` tag:

```
GitHub   b61eafcb2f37753faea37c836ecce6aa4e53ccd207ef39b719a3d04a09115bc6   ← what the Formula pins
local    746cc34fd84f6563a3ad4c688b1c195852b3a9d7969e7d8538232b4098010441   ← git archive, same tree
```

So the order is forced: **tag first, sha second.** Commit 1 sets the constant and carries
the tag; commit 2 points the Formula at the tarball that now exists. Anything promising one
commit is either not pinning a sha or not checking it.

## The checklist

### 1 — decide the increment

Semver by **user-visible CLI behaviour**: patch = a fix or clearer output, minor = a new
subcommand, flag or check, major = a removed subcommand, a renamed flag, or a changed
exit-status contract. That last one matters more than it looks: scripts wrap this CLI, and
`wellforge doctor` returning 1 instead of 0 is an interface change.

### 2 — bump the constant

`WELLFORGE_CLI_VERSION` at the top of `scripts/wellforge`. It is the single source:
`wellforge version` prints it, the Formula's `test` block asserts it, and CI asserts it
equals the newest `cli-v*` tag. Nothing else carries the CLI version.

### 3 — prove it before tagging

```bash
scripts/tests/wellforge.test.sh
shellcheck -s bash --severity=warning -f gcc scripts/wellforge scripts/*.sh
brew style Formula/wellforge.rb
brew audit --strict --online matteocodogno/wellforge/wellforge   # needs the tap, see below
```

`-f gcc` is not cosmetic: shellcheck's default format dies rendering a source line that
contains a non-ASCII character, and these scripts are full of em dashes. It exits 2 with
the output cut mid-line, which reads like a parse error in the script.

`brew audit` refuses a **path** (*"Calling `brew audit [path ...]` is disabled"*) — it takes
a formula *name*, so the repo has to be tapped once:

```bash
brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
```

Audit then reads the **tap's** checkout, not your working tree. To audit an unreleased
change, copy the file in, audit, and put it back:

```bash
TAP=$(brew --repository matteocodogno/wellforge)
cp Formula/wellforge.rb "$TAP/Formula/wellforge.rb"
brew audit --strict --online matteocodogno/wellforge/wellforge
git -C "$TAP" checkout -- Formula/wellforge.rb        # always restore
```

### 4 — commit and tag

```bash
git commit -m "chore(cli): release X.Y.Z"      # the constant only
git tag cli-vX.Y.Z
git tag --points-at HEAD                        # MUST print exactly one tag
```

One series per commit. A second tag here would make `git describe` answer with the wrong
one, which is how a scaffold records the wrong template version.

### 5 — push the tag, then compute the sha

```bash
git push origin main cli-vX.Y.Z
curl -fsSL https://github.com/matteocodogno/wellforge/archive/refs/tags/cli-vX.Y.Z.tar.gz \
  | shasum -a 256
```

This is the step that cannot be reordered. Until the tag is on the remote there is no
tarball to hash.

### 6 — point the Formula at it

`url` (the `cli-vX.Y.Z` tarball), `version` (explicit — see below), `sha256`. Then:

```bash
git commit -m "chore(cli): formula for cli-vX.Y.Z"
git push origin main
```

`version` is stated explicitly rather than parsed out of the url, for two reasons: brew's
guess at `cli-v1.0.0.tar.gz` is not something to depend on, and the number must stay
**monotonic** across the change of series — the Formula used to resolve `0.9.0` from the
template tag, so anything lower would make `brew upgrade` a silent no-op for everyone who
had already installed it. That is why the series starts at 1.0.0.

### 7 — smoke the package, not just the script

```bash
brew install --build-from-source Formula/wellforge.rb
brew test wellforge
brew uninstall wellforge        # if you were not already a user
```

`brew test` is where the packaged CLI is exercised: `help` mentions doctor, `version`
matches the Formula's version, `doctor` with an empty HOME prints its full report and exits
**1**, and an unknown subcommand exits non-zero. The repo's own suite covers the script;
this covers the script *as installed*.

### 8 — after the tap catches up

```bash
brew audit --strict --online matteocodogno/wellforge/wellforge
```

Run it again once the tap has the new commit, because that is the copy your teammates
actually install.

## What CI does and does not cover

| Check | Where | Note |
|---|---|---|
| CLI regression matrix | `cli` job, ubuntu | every push |
| shellcheck | `cli` job, ubuntu | every push, `-f gcc` |
| constant == newest `cli-v*` tag | CLI matrix | needs `fetch-depth: 0` |
| `brew install --build-from-source` + `brew test` | `formula` job, macos-latest | **non-blocking** (`continue-on-error`) — a macOS runner is billed at 10× and this only needs to be right at release time |
| `brew audit --strict --online` | `formula` job, macos-latest | every push, same job, same caveat |

The formula job being advisory is deliberate: it tells you the package is broken without
making every unrelated push wait on a 10×-cost runner. Read it before you tag.

**Advisory does not mean unread.** It was red for four pushes in a row and said nothing:
Homebrew 7 stopped accepting a formula by path (*"Homebrew requires formulae to be in a tap,
rejecting"*), so `brew install Formula/wellforge.rb` had not run at all. The job now taps the
checkout at `GITHUB_SHA` and installs by name, which is both what a user does and what lets
`brew audit` run — it needs a tap, which is why the table used to say "nowhere".

So step 3 and step 8 below are now **confirmations**, not discoveries: if CI is green on the
commit you are tagging, both have already passed on a macOS runner. Run them anyway at step
8, because the tap is the copy teammates install.
