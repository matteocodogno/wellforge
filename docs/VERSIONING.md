# Versioning — the three tag series

WellForge ships three things that version independently, so `git tag -l` shows three
interleaved series and the README shows three badges. This page is the authoritative
explanation; the enforcement rules live in
[`templates/_shared/CONTRACT.md`](../templates/_shared/CONTRACT.md).

| Version | What it versions | Who reads it | Format | Where it lives |
|---|---|---|---|---|
| `vX.Y.Z` | the **template** file tree (`copier.yml` + `templates/`) | Copier, when scaffolding and upgrading | semver, PEP440-parseable | git tag |
| `gates-vN` | the **reusable gate workflows** + their configs | generated projects' `quality.yml`, via `uses: …@gates-vN` | plain incrementing integer | git tag |
| `plugin-vX.Y.Z` | the **Claude Code plugin** (commands, agents, skills, hooks) | the plugin marketplace, when a teammate installs or updates | semver | git tag **and** `wellforge-plugin/.claude-plugin/plugin.json` **and** the `ref` in `.claude-plugin/marketplace.json` |

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
`_commit` in a scaffold and mislabel its template version. With three series the rule is the
same and the opportunities to break it have gone up: when a change spans layers, split it
into one commit per layer and tag them one apart:

```
main ──●───────────────●──────────────●──────────────▶
       │               │              │
   gate workflows   template      plugin
   + gate configs   wiring        (+ marketplace.json)
       │               │              │
    gates-v11        v0.9.0     plugin-v2.42.0
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
- Pushing a `vX.Y.Z` tag triggers [`release.yml`](../.github/workflows/release.yml): it
  publishes the GitHub Release with notes from the Conventional Commits, then pushes a
  Homebrew formula bump branch (the formula follows the **template** series, since that tag
  names the tarball users install).
