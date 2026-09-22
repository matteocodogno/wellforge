# Versioning — the four tag series

WellForge ships four things that version independently, so `git tag -l` shows four
interleaved series. This page is the authoritative
explanation; the enforcement rules live in
[`templates/_shared/CONTRACT.md`](../templates/_shared/CONTRACT.md).

| Version | What it versions | Who reads it | Format | Where it lives |
|---|---|---|---|---|
| `vX.Y.Z` | the **template** file tree (`copier.yml` + `templates/`) | Copier, when scaffolding and upgrading | semver, PEP440-parseable | git tag |
| `gates-vN` | the **reusable gate workflows** + their configs | generated projects' `quality.yml`, via `uses: …@gates-vN` | plain incrementing integer | git tag |
| `plugin-vX.Y.Z` | the **Claude Code plugin** (commands, agents, skills, hooks) | the plugin marketplace, when a teammate installs or updates | semver | git tag **and** `wellforge-plugin/.claude-plugin/plugin.json` **and** the `ref` in `.claude-plugin/marketplace.json` |
| `cli-vX.Y.Z` | the **`wellforge` CLI** (`scripts/wellforge` + `Formula/wellforge.rb`) | Homebrew, on install and `brew upgrade` | semver | git tag **and** `WELLFORGE_CLI_VERSION` in `scripts/wellforge` **and** the `url`/`version` in the Formula |

## Before ANY tag: `scripts/check-all.sh`

Every release in every series has one precondition, and it is not a checklist item:

```sh
mise run check              # scripts/check-all.sh — every self-test, one exit code
mise run check:full         # ...plus one preset's OWN gates on a fresh scaffold
```

**Red means no tag.** This is enforced in four places, deliberately overlapping, because the
first three are all bypassable by one flag:

| Where | What it does | Bypass |
|---|---|---|
| `scripts/release-cli.sh` | runs it before writing anything | `--skip-checks`, which prints a banner and records the skip in the commit body AND the tag |
| `gates/hooks/pre-push` | runs it when the push carries a `v*` / `plugin-v*` / `gates-v*` / `cli-v*` tag; branch pushes are untouched | `git push --no-verify` |
| `/wellforge:release` | the procedure's first step | it is a prompt |
| **`release-guard` in ci.yml** | requires **every** other job green, on tag pushes only | **none** |

`release-guard` also reads `needs.formula.result` explicitly: the `formula` job is
`continue-on-error` so that a 10x macOS runner never blocks an ordinary push, which means
`needs:` alone would be satisfied by a FAILED formula. Advisory on a branch, blocking on a
tag.

### A tag whose CI is red is deleted and re-cut — never left

A tag is what other people install. Leaving a red one in place and "fixing it forward"
means the artifact named by that version is permanently not the artifact that was tested.

```sh
git push origin :refs/tags/<tag>     # delete the remote tag FIRST
git tag -d <tag>                     # then the local one
# fix, commit, and cut the tag again
```

Do not move a tag with `git tag -f` and force-push: anyone who already fetched it keeps the
old object and no command they run will tell them. Delete, then re-cut.

**This rule exists because it was broken, twice.**

`plugin-v2.49.0` and `cli-v1.5.0` were tagged from a tree where `post-spec-guard.test.sh`
had one failure and the CLI matrix had six. Nothing was weakened; the suites were simply
not all run, because running them meant remembering nine commands in four directories. The
repo tells every project it generates that a rule enforced by remembering is not enforced —
this is that rule applied to itself.

**`cli-v1.5.1` and `plugin-v2.49.2` were then tagged from a red tree as well**, which is
worse, because by then `scripts/check-all.sh` existed and was printing `1 check(s) FAILED —
this tree must not be tagged`. The gate was built and the tag was cut past it. Both tags
stay where they are: deleting a tag other people may already have fetched trades a recorded
mistake for an unrecorded one, and this paragraph is the honest version.

What was actually red at those two commits, reproduced on Linux afterwards:

| Case | Cause |
|---|---|
| `doctor, 3 commits behind` | the fixture's bare origin took its default branch from the HOST's `init.defaultBranch`; where that is unset (git's own default `master` — CI and a stock Mac) the upstream silently never advanced |
| `a pull that fails shows git's reason` | same cause |
| `telegram: env file 600, its directory 700` | the BSD and GNU spellings of `stat` do not fall through to one another: on Linux the BSD form exits 0 with empty stdout, so the assertion compared `""` against `"600"` |

All three were host-dependence in the harness, not defects in the CLI, and all three are
fixed — the suite now neutralises the global and system git config outright rather than
pinning one setting at a time.

Two further cases, `setup registers the GIT marketplace, not the local checkout` and
`WELLFORGE_MARKETPLACE overrides it`, were reported red in a full run on two Linux hosts
while passing in isolation. **They could not be reproduced here**: 58/58 green on macOS,
Debian, Ubuntu 24.04, GitHub's runner, under CPU starvation, run twice consecutively, and
with the two cases moved to the top of the file. Rather than guess at a fix, the harness
defects that could produce that shape were removed and the next occurrence was made
self-diagnosing — see the `harness:` self-check cases and `assert_file_has`, which now
prints grep's own exit status and stderr instead of hiding them behind `2>/dev/null`.

### Why it cannot happen again by remembering

Three layers, none of which is a checklist item:

- `scripts/release-cli.sh` runs `check-all.sh` before it writes anything (`--skip-checks`
  prints a banner and records the skip in the commit body *and* the tag).
- `gates/hooks/pre-push` runs it when the push carries a `v*` / `plugin-v*` / `gates-v*` /
  `cli-v*` tag, so a red tree cannot reach the remote along with its tag.
- CI's `release-guard` requires every other job green and only exists on tag pushes. It is
  the copy that skipping the local hooks cannot reach.

## Why the template and the gates are separate series

Because they change at different rates, for different reasons, and reach projects through
different mechanisms.

- A **gate** change (a threshold, a tool version, a new check) must reach every project
  *without* re-templating it. Projects consume it by bumping one ref in their own
  `quality.yml` — no `copier update`, no file-tree churn, nothing to merge.
- A **template** change alters files inside the project. It only lands through
  `copier update`, with conflict resolution against whatever the team has edited since.

A single series would force a template release for every threshold tweak, and imply that
CI tooling changed on every template release. Both directions happened in one day
(2026-07-29):

- The semgrep crash was gate-only. It shipped as `gates-v9`; downstream projects fixed
  their red CI with a one-line ref bump, touching nothing else.
- The compose-services wiring changed generated workflow files, so it needed `v0.9.0` and
  a `copier update`.

## Why `gates-vN` is deliberately not `gates-1.2.3`

Copier resolves "latest version" from **PEP440-parseable** tags. `gates-v11` is not
parseable, so Copier ignores the whole series — which is the point. A `gates-1.0` tag would
be read as a candidate template version and offered as an upgrade.

It is also not semver on purpose: it is a **pin**, not a product version. There is no
meaningful "breaking vs additive" distinction for "the configs the gate reads" — you are
either on a ref or you are not.

## They move independently — including on upgrade

This surprises people, so it is worth stating plainly: **a template release does not carry a
gate bump to existing projects.**

`gates_ref` is a recorded Copier *answer*, and `/wellforge:upgrade` runs
`copier update --skip-answered`, which preserves recorded answers. Verified end-to-end:
updating a project from `v0.7.0` to `v0.8.0` re-rendered every workflow and still pinned
`@gates-v7`. Bumping the default in `copier.yml` only affects **new** scaffolds.

So a project has two independent currencies:

```
.copier-answers.yml   _commit: v0.9.0      ← template currency
.copier-answers.yml   gates_ref: gates-v7  ← gate currency   (can be years apart)
```

Moving each one:

```bash
# template → latest
uvx copier update --trust

# gates → latest (rewrites the recorded answer AND every call site)
uvx copier update --trust --data gates_ref=gates-v11
```

`/wellforge:upgrade` now does both: it updates the template, then compares `gates_ref`
against the newest `gates-v*` tag and offers the bump as an explicit, **raise-only** step.
Never lower a gate pin to make CI green — that is the discretion the ratchet exists to
remove.

## Why the plugin became a tag series too

It was not one until `2.42.0`, and the reason it had to become one is the whole point of a
release series: **the marketplace entry has to name something immutable.**

`.claude-plugin/marketplace.json` used to read `"source": "./wellforge-plugin"` — a path
relative to whatever checkout you happened to register. That install works on exactly one
machine: the one holding the clone. A teammate had nothing to add. The fix is a git source:

```json
"source": { "source": "git-subdir",
            "url": "https://github.com/matteocodogno/wellforge.git",
            "path": "wellforge-plugin",
            "ref": "plugin-v2.42.0" }
```

`ref` is what makes an install reproducible, and a ref has to be a tag — pinning `main`
means two teammates installing an hour apart get different plugins and neither can say
which. So the plugin now cuts `plugin-vX.Y.Z` alongside the `plugin.json` bump.

**The version appears in three files and they must agree.** `check-docs.py` fails CI
otherwise, because the symptom is silent: a teammate installs a plugin that isn't the one
this repo describes.

| File | Field | Value at 2.42.0 |
|---|---|---|
| `wellforge-plugin/.claude-plugin/plugin.json` | `version` | `2.42.0` |
| `.claude-plugin/marketplace.json` | `version` | `2.42.0` |
| `.claude-plugin/marketplace.json` | `source.ref` | `plugin-v2.42.0` |
| `CLAUDE.md` | the quoted plugin version | `2.42.0` |
| git | the tag | `plugin-v2.42.0` |

The manifest must point at its **own** tag, so the order is: bump all three files, commit,
then tag *that* commit. The commit tagged `plugin-v2.42.0` contains a manifest whose `ref`
reads `plugin-v2.42.0`. That looks circular and isn't — it is how the default branch's
manifest names the current release.

### `plugin-v*` is invisible to copier, deliberately

Same reasoning as `gates-v*`: copier resolves "latest version" from PEP440-parseable tags,
and `plugin-v2.42.0` is not parseable. Naming the series `2.42.0` — bare semver — would put
it straight into the template's version list and offer the plugin as a template upgrade.

**Invisible when *resolving* a version is not the same as invisible to `git describe`**, and
the difference is measurable. Scaffolding from a commit that carries `plugin-v2.42.0`, with
an explicit `--vcs-ref HEAD`:

```
.copier-answers.yml   _commit: plugin-v2.42.0     ← the plugin tag, recorded as the template ref
.forge/manifest.json  "version": "0.9.0"          ← still the template version
```

The manifest — what `/wellforge:upgrade` and `fleet-status.sh` read — is correct, because it
comes from the `template_version` answer rather than from `git describe`. But `_commit` is
polluted, and `_commit` is what a future `copier update` diffs from.

This does **not** affect a normal scaffold: with no `--vcs-ref`, copier resolves the newest
PEP440 tag and records `_commit: v0.9.0` regardless of what else is tagged. The exposure is
scaffolding from a *branch* — which the CI self-test now deliberately does, so it tests the
branch rather than the last release. That is a throwaway `/tmp` project, so a polluted
`_commit` costs nothing there; the job asserts the manifest version is still template-shaped
so the pollution cannot spread to the field anyone reads.

The rule that follows: **cut user-facing scaffolds from a `vX.Y.Z` tag, never from HEAD.**

### What `plugin update` actually resolves to is undocumented

Honest gap, stated here so nobody reads more into the tag than it carries. The published
plugin-marketplace docs specify the manifest schema and the pinning keys but do **not**
specify what `claude plugin update` compares against — the refreshed manifest's `ref`, the
default branch, or the `version` field. What is observable is that Claude Code records both
`version` and `gitCommitSha` per install in `~/.claude/plugins/installed_plugins.json`, and
caches the plugin per version (`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`).

Two consequences worth acting on:

- **An unbumped plugin edit reaches nobody**, including you — the cache is keyed by version.
- **Verify after updating** rather than assuming: `/wellforge:doctor` reports the installed
  version, where it came from, and whether a newer `plugin-v*` tag exists.

## Why the CLI is its own series

Because it was not, and the consequence was measurable. The Formula pinned
`refs/tags/v0.9.0.tar.gz`, so the CLI shipped only when the **template** shipped — and the
rule two sections down says a template release must carry a template change. A CLI-only fix
therefore had nowhere to go. By the time this was noticed, `scripts/wellforge` had moved
**179 insertions and 64 deletions** past `v0.9.0` with no release to ride on, and
`wellforge doctor` cheerfully reported the checkout as current while every brew user ran
the old CLI.

The CLI and the template have nothing in common as products: one is a single file installed
by Homebrew, the other is a file tree rendered by copier into someone's repository. Tying
them together meant the faster-moving one could not move.

### What a CLI release touches

| File | Field |
|---|---|
| `scripts/wellforge` | `WELLFORGE_CLI_VERSION="X.Y.Z"` — the single source |
| `Formula/wellforge.rb` | `url` (the `cli-vX.Y.Z` tarball), `version`, `sha256` |
| git | the tag `cli-vX.Y.Z` |

`WELLFORGE_CLI_VERSION` is what `wellforge version` prints and what the Formula's `test`
block asserts. The Cellar path is kept **only as a cross-check**: when the constant and the
directory brew installed into disagree, `wellforge version` says so, because that means the
installed tree is not what its own path claims.

### Cut one with the script, not by hand

```bash
scripts/release-cli.sh patch            # plan only — prints every step, changes nothing
scripts/release-cli.sh patch --execute  # bump, commit, tag, push, sha256, formula, push
```

**The full checklist is [`RELEASING-CLI.md`](RELEASING-CLI.md)** — the steps live there and
only there, and `release-cli.sh` prints them as it runs, so the three cannot drift far.
The one rule worth repeating here because it constrains the *shape* of a release: it takes
**two commits**, because the Formula pins the sha256 of GitHub's generated tarball, which
does not exist until the tag is pushed and is not reproducible locally. Tag first, sha
second, always.

### The rules, same as the other three

- **Bumped only when `scripts/wellforge` or `Formula/wellforge.rb` changes.** A template or
  plugin change alone does not move it, and a CLI change *must* move it — an unbumped CLI
  fix reaches nobody, exactly as before.
- **Never on the same commit as another series' tag.** `release-cli.sh` refuses when HEAD
  already carries one (`git tag --points-at HEAD`), for the `git describe` reason below.
- **Semver by user-visible CLI behaviour**: patch = a fix or clearer output, minor = a new
  subcommand, flag or check, major = a removed subcommand, a renamed flag, or a changed
  exit-status contract (scripts depend on those).
- **`cli-v*` is invisible to copier** for the same reason as `gates-v*` and `plugin-v*`:
  not PEP440-parseable, so it never gets offered as a template version.
- **Monotonic across the switch.** The first CLI release is `1.0.0`, not `0.1.0`, because
  the Formula already resolved `0.9.0` from the template tag: anything lower would make
  `brew upgrade` a silent no-op for everyone who had already installed it.

## What is a given project on?

```bash
jq -r '.version'                    .forge/manifest.json       # template version
grep -E '^(_commit|gates_ref):'     .copier-answers.yml        # both, as recorded
grep -o '@gates-v[0-9]*'            .github/workflows/*.yml    # what CI actually calls
```

Across a fleet: [`scripts/fleet-status.sh`](../scripts/fleet-status.sh) tables every
project's template version against the newest tag, and the **template-drift heartbeat**
(`.github/workflows/template-drift.yml`) files one deduplicated issue per project that falls
behind.

## Release rules

**Never tag two series on the same commit.** Copier ignores `gates-v*` and `plugin-v*` when
*resolving* versions, but `git describe` can still report one, which would record the wrong
`_commit` in a scaffold and mislabel its template version. With four series the rule is the
same and the opportunities to break it have gone up: when a change spans layers, split it
into one commit per layer and tag them one apart:

```
main ──●───────────────●──────────────●──────────────●────────▶
       │               │              │              │
   gate workflows   template      plugin          CLI
   + gate configs   wiring        (+ marketplace)  (+ Formula)
       │               │              │              │
    gates-v11        v0.9.0     plugin-v2.42.0   cli-v1.0.0
```

- **Template**, semver: patch = cosmetic, minor = additive, major = needs `_migrations`.
  Bump the `template_version` default in the release commit; the manifest reads it.
- **Gates**: increment by one whenever the workflows or their configs change in a way
  consumers should adopt. Consumers pin, so an unbumped change reaches nobody.
- **Plugin**, semver: patch = fix/wording, minor = new command, agent, skill, hook or
  config, major = a change that breaks a project set up by an older plugin. Bump
  `plugin.json`, `marketplace.json` (`version` **and** `source.ref`) and CLAUDE.md in the
  same commit, then tag it `plugin-vX.Y.Z`. It is cached by version at runtime, so an
  unbumped edit will not take effect in a running session — and an untagged bump is
  installable by nobody, because the manifest's `ref` would name a tag that does not exist.
  Every minor also gets an entry in [`PLUGIN-MIGRATIONS.md`](PLUGIN-MIGRATIONS.md), even if
  it is "no project-side action" — `/wellforge:upgrade` reads that file, and silence there
  is ambiguous between "nothing to do" and "nobody checked".
- **CLI**, semver by user-visible behaviour: see *Why the CLI is its own series* above.
  `scripts/release-cli.sh` owns it end to end; do not bump the constant or the Formula by
  hand, because the two must agree and the sha can only come from the pushed tag.
- **The Homebrew formula is checked by hand, before the tag.** `Formula/wellforge.rb` is
  what a teammate installs, and it is the one file in this repo with no CI gate — for a
  measured reason rather than an oversight:

  ```bash
  brew style Formula/wellforge.rb                       # works on a path; ~1.5s warm
  brew audit --strict matteocodogno/wellforge/wellforge # needs the formula TAPPED, not a path
  ```

  `brew audit` refuses a **path** outright (*"Calling `brew audit [path ...]` is disabled"*)
  — it only accepts a formula *name*, which means the repo has to be tapped. Once it is,
  the audit runs locally in ~1.4s against the tap's checkout; it does not need the release
  to be published, only the tap to exist. That is still not something CI can do cheaply: a
  `macos-latest` runner is billed at 10× and would have to tap the repo first, for a file
  that changes once per release.

  Both have earned their place. `brew style` caught `FormulaAudit/Desc` (a description
  starting with the formula name); `brew audit --strict` caught
  `license "UNLICENSED"` as a non-standard SPDX identifier — now `:cannot_represent`.

  Run `brew style` before tagging. Run `brew audit --strict` before tagging too if the repo
  is tapped locally (`brew tap matteocodogno/wellforge <url>` once), otherwise right after
  the tap catches up. `release-cli.sh` runs `brew style` for you and refuses to push a
  formula it rejects.

- Pushing a `vX.Y.Z` tag triggers [`release.yml`](../.github/workflows/release.yml): it
  publishes the GitHub Release with notes from the Conventional Commits. **It no longer
  touches the Homebrew formula.**

  It used to, and this paragraph used to say the formula "follows the **template** series,
  since that tag names the tarball users install" — which contradicted this same document
  two sections above, where the CLI has its own `cli-vX.Y.Z` series precisely because
  riding the template's tags meant a CLI fix could not ship without a template release.
  One file with two owners, and the one that ran on every template tag was the wrong one:
  the formula sat on `v0.9.0` while the CLI shipped four releases of its own.

  The formula belongs to the CLI release path, end to end:

  ```sh
  scripts/release-cli.sh <patch|minor|major|X.Y.Z> --execute
  scripts/release-cli.sh X.Y.Z --formula-only --execute   # the formula alone
  ```

  `check-docs.py` asserts the formula's `version` against `WELLFORGE_CLI_VERSION` and the
  newest `cli-v*` tag, so a formula left behind by a hand edit fails CI rather than
  reaching a brew user.
