# WellForge — Rigor tiers (velocity vs. assurance)

Status legend: ☐ todo · ◐ in progress · ☑ done

A plan to let WellForge match its ceremony to the stakes. Today every feature runs the
full pipeline (7 agents, 2 approval gates, frontier models, 80% coverage, LM-judge eval) —
right for production, wasteful for a feasibility spike that may be thrown away.

**Principle: don't lower the bar — defer it, explicitly and reversibly.** Lower rigor is a
*declared, recorded, promotable* lifecycle stage (extends Pillar 6), never a silent
corner-cut. The failure mode we design against is a spike silently becoming production.

## Decisions (locked)

- **Three tiers:** `spike` / `mvp` / `production`.
- **`spike` runs on the main loop** — no subagents at all (fastest; loses the team by design).
- Fast tier is named **`spike`**; the express command is `/wellforge:spike`.

## Tiers

| Tier | Intent | Throwaway-ok? |
|---|---|---|
| `spike` | Feasibility / business-model experiment | Yes — expected |
| `mvp` | First real release to validate with users | No, but debt is acknowledged |
| `production` | Current full rigor (unchanged) | No |

One vocabulary (`rigor:`) flows through copier answer → manifest → spec frontmatter →
command flag. **Not** new templates, **not** forked agents (both are death risks — template
sprawl, prompt duplication). `rigor` is a *selector* the existing pipeline reads.

## What each tier tunes

| Lever | `spike` | `mvp` | `production` (today) |
|---|---|---|---|
| Pipeline depth | **main loop** builds from a brief; no subagents | combined planner + dev + light QE | full 7-agent team |
| Human gates | 0 (autonomous; human reviews result) | 1 (combined brief) | 2 |
| Spec ceremony | one `brief.md` | spec + tasks (plan folded in) | spec + plan + design + tasks |
| Models | inherits session model (no per-agent routing) | mid; frontier only where it pays | current routing |
| Quality gates | lint + typecheck + build, **advisory** | + smoke tests + SAST-high **blocking**; coverage advisory | full 80% + SAST + eval |
| Eval (LM-judge) | off | off | on (gate into `done`) |
| CI | build-only (or none) | reduced gate | full |

Reuse, not new machinery:
- **Models** — an `mvp` profile is a routing profile over the existing `frontier/mid/cheap`
  tiers (`config/model-routing.yml`). `spike` is moot here: the main loop uses the session model.
- **Gates** — "advisory not blocking, report gap-to-target" is exactly the brownfield
  **ratchet baseline** mechanism. Reuse it.

**Non-negotiable security floor (all tiers, incl. `spike`):** gitleaks secret scan, no
hardcoded creds, dependency audit on *critical* CVEs. Fast must never mean "leaks credentials."
No tier can disable this floor.

## Where rigor lives

Declared + recorded, precedence **invocation > feature > project default**:

- **Project default** — `/wellforge:new` interview asks "throwaway spike / MVP to validate /
  production product?" → `rigor` copier answer → `.forge/manifest.json`. A spike scaffold
  gets build-only CI, not an 80%-coverage gate it can never meet.
- **Per-feature** — `rigor:` in spec/brief frontmatter (a production project can still spike
  one risky feature).
- **Per-invocation** — `--mode spike|mvp|production` on `orchestrate`/`implement`.

## Command surface

- `/wellforge:spike <goal>` — express lane: main-loop, brief → code, advisory gates, no
  approval. Sugar for `orchestrate --mode spike`. A named command signals intent.
- `--mode` flag on `orchestrate` / `implement` / `new`.
- `/wellforge:status` shows each feature's tier; generated README carries a **SPIKE** badge
  and CI prints "rigor: spike — gates advisory". Visibility is the guardrail.

## Graduation — `/wellforge:promote`

`/wellforge:promote <feature> --to mvp|production` raises the tier and **pays the deferred
debt**: architect writes the plan retroactively, QE backfills tests to the coverage floor,
gates flip advisory → blocking, eval runs. The skipped rigor was a tracked debt (the
frontmatter tier), paid when the experiment proves real. This is Pillar 6 extended from
"template version" to "rigor stage."

## Guardrails against silent promotion

- Visible labeling everywhere (manifest, README badge, CI notice) — nobody mistakes a spike
  for production-grade.
- Production rigor only ever via `/wellforge:promote` (which pays the debt) — never implicit.
- Optional staleness nag — `status` flags "this spike is N days old: promote or archive."
- Single source of truth — one `rigor` vocabulary; parametrized pipeline, not parallel agents.

## Phasing

### Phase A — Workflow parametrization (biggest speed win, zero template change) ☑
- ☑ Add `rigor` vocabulary (`spike`/`mvp`/`production`) to `spec-driven` skill + frontmatter.
  New canonical **`rigor-tiers` skill** is the SSOT (tiers, levers, floor, precedence).
- ☑ `/wellforge:spike <goal>` command — main-loop builder: `brief.md` → implementation,
  advisory lint/typecheck/build, no agents, no approval gate.
- ☑ Teach `/wellforge:orchestrate` + `/wellforge:implement` a `--mode` flag; `mvp` collapses
  the pipeline (PO → 1 gate → inline tasks → mid devs → light QE, no architect/designer/eval).
- ☑ `mvp` model story documented in `config/model-routing.yml` — tiers save cost by
  *composition* (mvp never spawns frontier agents), not by re-tiering fixed frontmatter.
- ☑ Wire the security floor as the non-negotiable minimum across all tiers.
- ☑ Reuse the ratchet-baseline advisory mode for `spike`/`mvp` gate reporting.

### Phase B — Scaffold dimension ☑
- ☑ `rigor` question in root `copier.yml` → `.forge/manifest.json` (both presets). Template v0.4.0.
- ☑ Conditional CI in templates: spike = security-floor + build sanity, mvp = coverage advisory,
  production = full — same templates (copier `{% if %}`), no new presets. Gates made tier-aware
  (`rigor` input on quality-node/jvm) + new `security-floor.yml`; cut **gates-v5**.
- ☑ README **not-production-ready** badge for spike/mvp + AGENTS.md states the project tier.
- ☑ `/wellforge:new` interview sets the project default from the scale/lifetime answer.

### Phase C — Graduation
- ☐ `/wellforge:promote <feature> --to <tier>` — retro plan, backfill tests to floor, flip
  gates to blocking, run eval; one revertable commit (mirror `/wellforge:upgrade`'s shape).
- ☐ `/wellforge:status` surfaces tier per feature + optional staleness nag.

## Open / to validate during the pilot

- **Measure first:** attribute the current ~20-min run via `run-report.py` over `.forge/runs/`
  before tuning — confirm the dominant cost (agent cold-starts vs. opus latency vs. full gates)
  so Phase A cuts the right thing.
- `mvp` tier calibration: how light is too light before it causes rework loops (the OpEx trap)?
- Whether `mvp` truly needs a separate "combined planner" agent or can reuse `architect` with
  a lighter prompt budget.
