# Versioning — the two tag series (and the third version number)

WellForge ships three things that version independently, so `git tag -l` shows two
interleaved series and the README shows three badges. This page is the authoritative
explanation; the enforcement rules live in
[`templates/_shared/CONTRACT.md`](../templates/_shared/CONTRACT.md).

| Version | What it versions | Who reads it | Format | Where it lives |
|---|---|---|---|---|
| `vX.Y.Z` | the **template** file tree (`copier.yml` + `templates/`) | Copier, when scaffolding and upgrading | semver, PEP440-parseable | git tag |
| `gates-vN` | the **reusable gate workflows** + their configs | generated projects' `quality.yml`, via `uses: …@gates-vN` | plain incrementing integer | git tag |
| `2.x.y` | the **Claude Code plugin** (commands, agents, skills, hooks) | the plugin marketplace / local install | semver | `wellforge-plugin/.claude-plugin/plugin.json` — **not** a tag |

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

**Never tag a `gates-v*` and a `vX.Y.Z` on the same commit.** Copier ignores `gates-v*` when
*resolving* versions, but `git describe` can still report it, which would record the wrong
`_commit` in a scaffold and mislabel its template version. When a change spans both layers,
split it into a gates-only commit and a template commit, and tag them one apart:

```
main ──●───────────────●──────────────●──────────────▶
       │               │              │
   gate workflows   template      docs / plugin
   + gate configs   wiring
       │               │
    gates-v11        v0.9.0
```

- **Template**, semver: patch = cosmetic, minor = additive, major = needs `_migrations`.
  Bump the `template_version` default in the release commit; the manifest reads it.
- **Gates**: increment by one whenever the workflows or their configs change in a way
  consumers should adopt. Consumers pin, so an unbumped change reaches nobody.
- **Plugin**: bump `plugin.json` in the same commit as the plugin change. It is cached by
  version at runtime, so an unbumped edit will not take effect in a running session.
- Pushing a `vX.Y.Z` tag triggers [`release.yml`](../.github/workflows/release.yml): it
  publishes the GitHub Release with notes from the Conventional Commits, then pushes a
  Homebrew formula bump branch (the formula follows the **template** series, since that tag
  names the tarball users install).
