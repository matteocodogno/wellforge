---
name: template-extraction
description: >
  WellForge template extraction — turn an existing project into (1) a structured stack
  profile checked against the shipped presets (the gap check), and (2) an opt-in, org-internal
  reusable Copier template so a team can scaffold its next service from its own real stack.
  Use during /wellforge:adopt (Stage 0 always runs the profile+gap; extraction is an opt-in
  layer) and for the standalone /wellforge:extract-template command. Authoritative reference
  for the .forge/stack-profile.json schema, the preset gap-check heuristic, the mandatory
  IP/secret scrub gate (skeleton-only, no domain code, no secrets), and CONTRACT-compliant
  template generation with copier --defaults verification. This produces an ORG-INTERNAL
  template the team owns — it never opens a PR to the WellForge repo or ships code upstream.
---

# Template extraction — from a real project to a reusable template

Two capabilities, in order. The first is cheap and always worth running; the second is an
opt-in, higher-effort payoff that depends on the first.

1. **Stack profile + gap check** — fingerprint the project's stack and classify it against the
   shipped WellForge presets. Cheap, read-only, informative on its own.
2. **Org-internal template extraction** — reverse the project into a Copier template the team
   owns, so its *next* service starts from its *own* proven stack instead of a blank page.

**Scope boundary (non-negotiable).** Extraction produces a template the **org owns**, written
to a destination the user picks — a standalone Copier template repo. It does **NOT** open a PR
to the WellForge repository and does **NOT** ship the project's code anywhere upstream.
Contributing a stack back to WellForge's shipped catalog is a separate, human-curated decision
that is deliberately out of scope here.

---

## Part 1 — Stack profile + gap check

### The profile — `.forge/stack-profile.json`

Fingerprint the project from its build files, lockfiles, source tree, and config — never from
assumptions. Write this schema (omit keys you genuinely can't determine; don't guess):

```json
{
  "generated": "<YYYY-MM-DD>",
  "plugin": "<plugin version>",
  "monorepo": true,
  "layout": "single | monorepo-services | monorepo-packages",
  "services": [
    {
      "path": "backend",
      "role": "backend | frontend | worker | lib",
      "language": "kotlin",
      "language_version": "2.0",
      "framework": "spring-boot",
      "framework_version": "3.4",
      "build_tool": "maven",
      "package_manager": "maven",
      "test_runner": "junit5",
      "lint": "ktlint",
      "db_layer": "jooq+liquibase",
      "ui_library": null,
      "styling": null,
      "notable_deps": ["spring-modulith", "kotlin-logging"]
    }
  ],
  "database": "postgres | mysql | none",
  "ci": "github | gitlab | none",
  "container": "docker-compose | dockerfile | none",
  "gap": {
    "verdict": "covered | partial | novel",
    "closest_preset": "spring-kotlin-react | hono-react | null",
    "matched": ["frontend: react-ts-vite"],
    "unmatched": ["backend: fastapi (no preset)"],
    "recommendation": "<one line>"
  }
}
```

For projects with a frontend, always record `ui_library` and `styling` explicitly (MUI /
Chakra / Ant / shadcn / Mantine / Tailwind-only) — the designer and frontend-dev read it.

### The gap-check heuristic

Compare each service against the two shipped presets (source of truth for what they contain):

- **`spring-kotlin-react`** — backend: Spring Boot + Kotlin + jOOQ + Liquibase + Maven +
  Spring Modulith; frontend: React + TypeScript + Vite + Mantine + Tailwind + TanStack.
- **`hono-react`** — backend: Hono + TypeScript + Drizzle + pnpm; frontend: same React TS Vite.

Classify the whole project by how its **backend** and **frontend** halves land (DB choice and
minor deps don't change the verdict):

| Verdict | Condition | Recommendation |
|---|---|---|
| **covered** | both halves match one preset | Prefer `/wellforge:new` with that preset for the next service; extraction would just duplicate a shipped template (low value — say so). |
| **partial** | one half matches a preset, the other doesn't (e.g. React frontend + FastAPI backend, or Hono backend + Vue frontend) | Extraction is valuable for the **uncovered half**; the covered half can mirror the preset's conventions. |
| **novel** | neither half matches (e.g. Django+HTMX, Rails, .NET, Go+templ) | Extraction is **most** valuable — a genuinely new stack the catalog doesn't cover. |

Report the verdict, the closest preset, matched/unmatched dimensions, and a one-line
recommendation. Persist it in the profile's `gap` block. **The gap check only informs — it
never blocks.** A `covered` verdict is a nudge, not a refusal.

---

## Part 2 — Org-internal template extraction (opt-in)

Only after the user opts in. This is higher-effort and has a hard safety gate. Never start it
on a `covered` verdict without telling the user it will largely duplicate a shipped preset.

### The safety gate — run BEFORE writing anything

Extraction reads real, possibly proprietary, code. These are prerequisites, not steps:

1. **Skeleton-only.** The template captures **structure, build config, framework wiring, and
   ONE genericized representative example** per layer (a sample module/endpoint/entity, a
   sample component/page/route) — never the project's domain/business logic. Delete feature
   code; keep the scaffolding that shows *how* the stack is wired.
2. **Secret scrub.** Scan every candidate file for secrets (run `gitleaks detect` if
   available; otherwise pattern-scan for keys/tokens/passwords/connection strings). If any are
   found in files you'd include, **stop and report** — do not write the template. Replace all
   env values with placeholders; never carry a real `.env`.
3. **IP / license check.** Exclude vendored third-party code, anything under a non-permissive
   or unclear license, and generated artifacts. When unsure whether something is safe to
   extract, exclude it and note the exclusion. The user owns the source; the template must not
   quietly re-publish someone else's code.
4. **Human review gate.** The output is a **draft the user must review** before reusing or
   sharing it. Say so explicitly on hand-off. Extraction never makes the template
   authoritative on its own.

### Destination

Ask the user for a destination path. **Refuse** to write:
- inside the source project (it would pollute the repo being templated), or
- inside the WellForge repo itself (that's the out-of-scope upstream path).

Default suggestion: a sibling directory, `../<project_slug>-wellforge-template/`. The output is
a **self-contained Copier template repo** the org owns and can `copier copy` / `copier update`
from — it mirrors WellForge's own monorepo-template shape so it's familiar and upgradeable.

### What to generate (mirrors `templates/_shared/CONTRACT.md`)

At the destination, produce:

```
<dest>/
├── copier.yml                     # root: preset question + common + stack-specific questions
├── templates/
│   ├── _shared/CONTRACT.md        # copy of the WellForge contract (the rules still apply)
│   └── <preset-slug>/template/    # the scrubbed, parameterized skeleton
└── README.md                      # "extracted by WellForge; org-owned; review before use"
```

**`copier.yml`** — root monorepo pattern, exactly as the contract requires:
- `_subdirectory: "templates/{{ preset }}/template"`, `_min_copier_version: "9.0.0"`.
- The common questions verbatim from the contract (`project_name`, `project_slug`,
  `description`, `ci`, `rigor`, `gates_repo`, `gates_ref`) with the same defaults.
- A hidden `template_version` (`when: false`, start `0.1.0`).
- **Stack-specific questions derived from what you parameterized** (see below), each with a
  sensible default so `--defaults` always renders.
- No copy-time-injected answers (no dates) — the contract's `when: false` rule.

**`templates/<preset-slug>/template/`** — the project tree, transformed:
- Only files needing substitution get the `.jinja` suffix; leave the rest literal.
- Parameterize identifiers into copier vars: project name/slug → `{{ project_name }}` /
  `{{ project_slug }}`; a Java/Kotlin base package → a `base_package` question + a hidden
  `package_path` (`{{ base_package.replace('.', '/') }}`) for templated directory names (a dir
  name can't contain a literal `/`); DB name, service names, ports as needed.
- Conditional files use copier's `{% if %}` filename syntax (e.g. the `.github/` dir guarded on
  `ci == 'github'`) — a `ci: none` answer must not leave an empty `.github/`.
- Include the **required generated files**, genericized from the project's real ones:
  `.forge/manifest.json` (`{ "template": "<preset-slug>", "version": "{{ template_version }}",
  "answers": {…} }`), `.copier-answers.yml` (`{{ _copier_answers|to_nice_yaml }}`), `AGENTS.md`,
  `CLAUDE.md` (`@AGENTS.md`), `.claude/settings.json`, `specs/README.md`, `mise.toml`,
  `.gitignore`, `README.md`. Reuse the project's own AGENTS.md/mise.toml/settings.json as the
  basis — they already describe this stack — with names parameterized.
- `.github/workflows/quality.yml`: if the project already had WellForge gates wired (adoption),
  carry that, pinned to the same `gates_repo`/`gates_ref`. If not, generate a minimal one that
  **calls** the reusable gates (never inline gate logic) and note the org must confirm the
  gate workflow supports this stack — a novel stack may have no matching `quality-<stack>.yml`
  yet (report it as a gates gap, don't fabricate one).
- `.release-it.json`: mirror the project's release setup if present; otherwise the contract's
  default (conventional-changelog + bumper for the stack's version files, `npm.publish:false`).

### Verify before hand-off (required)

The contract's rule holds: **`--defaults` must always generate a working project.** Render into
a throwaway dir and confirm copier succeeds:

```bash
uvx copier copy --trust --defaults <dest> /tmp/wf-extract-verify
```

If render fails, fix the template (usually a Jinja/`when` error or a missing default) and
re-run — do not hand off a template that can't render. Where feasible, go further and run the
stack's install/build in the rendered dir to prove it's not just render-valid but buildable;
if you can't, say the verification stopped at render.

### Hand off

- `git init` the destination and make one commit: `chore: extract WellForge template from
  <project> (skeleton, scrubbed)`.
- Report: destination path, preset slug, the gap verdict that motivated it, what was
  parameterized, **what was scrubbed/excluded** (domain code, secrets, licensed code — be
  explicit), the verification result (render-only vs built), and the gates gap if the stack has
  no matching reusable workflow.
- State plainly that this is an **org-owned draft to review**, and how to use it:
  `uvx copier copy --trust <dest> <new-service-dir>`.

## Relationship to adopt

`/wellforge:adopt` runs **Part 1 in Stage 0** (always — cheap) and offers **Part 2 as an opt-in
layer**; when chosen it records `template-extraction` in `.forge/adoption.json`'s `layers`. The
standalone `/wellforge:extract-template` command runs either part on any project without a full
adoption. See [[spec-driven]] for the workflow context and the adopt command for the layer model.
