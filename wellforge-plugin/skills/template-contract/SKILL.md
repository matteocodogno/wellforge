---
name: template-contract
description: >
  The binding contract every WellForge Copier template must satisfy — the single root
  copier.yml, the shared question set, required generated files, the manifest, and the
  versioning rules that make `copier update` work. Use when adding or editing a preset,
  when writing an org-internal template with /wellforge:extract-template, when a scaffold or
  an upgrade behaves unexpectedly, or when deciding which version series a change belongs
  to. Authoritative reference for the monorepo template pattern, the no-hidden-answers rule,
  the two independent version series, and what a template may never do.
---

# Template contract

Every WellForge Copier template must satisfy this. `/wellforge:new` and
`/wellforge:upgrade` depend on it, and the lifecycle breaks quietly when a template drifts
from it — usually at `copier update`, months later, in someone else's project.

The canonical copy lives at `templates/_shared/CONTRACT.md` in the wellforge repo; this
skill is what an agent carries into a project that has no access to that file.

## One copier.yml at the repo root

ONE `copier.yml` at the **repo root** serves every preset: a `preset` question selects the
stack, and `_subdirectory: "templates/{{ preset }}/template"` picks the file tree. Presets
do **not** have their own `copier.yml`; preset-specific questions live in the root file,
guarded with `when: "{{ preset == '<name>' }}"`.

This is not organisational taste. `copier update` requires the template source to be the git
repo root, versioned by repo-wide tags — split the config per preset and the upgrade path
goes with it.

```bash
uvx copier copy --trust <repo or URL> <dest> --data preset=<name>
```

Note for anyone testing a template change: copier renders from the **latest tag**, not your
working tree. To exercise an uncommitted edit, copy the repo without `.git` and render from
there, or pass an explicit `--vcs-ref`.

## The shared question set

Every preset asks these, with these names — `/wellforge:new` fills them and
`/wellforge:upgrade` re-uses the recorded answers:

`project_name`, `project_slug`, `description`, `ci`, `rigor`, `gates_repo`, `gates_ref`,
`heartbeat`, `heartbeat_cron`. Stack-specific questions are free per preset but **must have
defaults**, so `copier copy --defaults` always produces a valid project — that is what CI
smoke-tests every preset with.

**No hidden copy-time answers.** A question with `when: false` is not persisted to
`.copier-answers.yml`, so an injected value (a generation date is the classic) diverges from
the re-rendered base and conflicts on every future update. Learned the hard way; generation
date lives in git history, where it already was.

## Required generated files

- `.forge/manifest.json` — template, version, answers. **The upgrade contract.** Never
  hand-edit it, and never hand-edit `.copier-answers.yml`; between them they are the only
  record of where a project came from.
- `AGENTS.md` (with `CLAUDE.md` importing it) — the project's own conventions, so an agent
  arriving later reads the project rather than guessing.
- `mise.toml` — pinned toolchain plus `install`/`build`/`test`/`lint` tasks. In a monorepo,
  a root task **cannot** depend on a subdirectory task by name; see [`mise`](../mise/SKILL.md) for the
  addressing rule and the pointer-task pattern.
- CI that **calls** the shared gate workflows pinned to a `gates-v*` tag, passing
  `gates-repo` and `gates-ref` explicitly ([`quality-gates`](../quality-gates/SKILL.md)).
- A `specs/` directory, so the spec-driven flow has somewhere to land ([`spec-driven`](../spec-driven/SKILL.md)).

## Two version series, deliberately independent

| Series | What it versions | Where it lives |
|---|---|---|
| `vX.Y.Z` | the **templates** — what `copier update` resolves | repo-wide git tags, presets in lockstep |
| `gates-v*` | the **gate workflows and configs** | separate tags, invisible to copier |
| `2.x.y` | the **plugin** | `plugin.json`, not a tag |

They move at different rates for different reasons, so a template release does not drag a
gates bump into existing projects, and a plugin fix reaches everyone without a scaffold
change. Semver for templates: patch = cosmetic, minor = additive, major = needs
`_migrations`. Bump the `template_version` default in the release commit, and never tag two
series on one commit.

## What a template may never do

- Ship a secret, or a placeholder that looks like one.
- Depend on a tool it does not pin in `mise.toml`.
- Reference a file it does not generate (the shipped presets once called `./mvnw` with no
  wrapper in the tree — every backend task failed at the first run).
- Carry domain code from the project it was extracted from ([`template-extraction`](../template-extraction/SKILL.md) has the
  mandatory scrub).
