---
name: springboot-scaffold
description: >
  How a Spring Boot / Kotlin service comes into existence in a WellForge project — the JVM
  backend path. Use when the user wants a new Spring Boot / Kotlin / JVM service, or a second
  service in an existing JVM monorepo. Trigger phrases: "new Spring Boot service", "new
  Kotlin/JVM microservice", "scaffold a JVM/Spring backend", "new spring boot app". FIRST
  confirm the target stack — for a TypeScript / Hono service use `hono-ts-backend`; this
  skill is JVM-only and must NOT put Spring into a TypeScript codebase. It routes to the
  right generator and owns the module conventions; it does not hand-generate a project.
---

# Spring Boot / Kotlin — how a service gets created here

**This skill generates nothing.** It used to: it shipped a 741-line `scaffold.sh` that
hand-built a whole project. That was deleted, because it broke the contract everything else
depends on — WellForge generates projects **only** through the root `copier.yml`
([`template-contract`](../template-contract/SKILL.md)). A hand-rolled project has no `.forge/manifest.json`, so it has no
recorded template version, no `copier update` path, and no wiring to the shared quality
gates. It looks like a scaffold and is actually a dead end: pillar 5 and pillar 6 both
bypassed, silently, at the moment a project is born.

(It was also broken in two ways nobody had hit, because no command or agent ever called it:
it `cp`'d its output to a `/mnt/user-data/outputs/` sandbox path under `set -euo pipefail`,
so it exited non-zero on any real machine after generating, and it told the model to deliver
the result with `present_files`, which is not a Claude Code tool.)

## Route by what is actually being asked

**A new project, JVM backend + React frontend** → `/wellforge:new`, which picks the
`spring-kotlin-react` preset. That is the supported path and the only one that produces a
manifest, CI wired to the pinned gates, and an upgrade path.

```
/wellforge:new  "order service with a React admin UI"
```

**A second service inside an existing WellForge JVM monorepo** → there is no generator for
this, and `/wellforge:new` is the wrong tool (it makes a whole project, one per invocation).
Do it by hand, deliberately, following the conventions below and the existing service as the
reference — it is the closest thing in the repo to a template, and it is already correct for
this project's versions.

1. Copy the existing backend module's structure (not its domain code): `pom.xml`,
   `src/main/kotlin/<base-package>/`, `src/main/resources/`, `src/test/`.
2. Register it in the parent `pom.xml` `<modules>`, and inherit every version from the
   parent — **never re-pin a version a parent already manages**.
3. Add its tasks to the service's own `mise.toml`, and a root pointer task per [`mise`](../mise/SKILL.md)
   (a root task cannot depend on a subdirectory task by name).
4. Wire it into CI by calling the shared gate with the new `working-directory`
   ([`quality-gates`](../quality-gates/SKILL.md)).
5. Follow [`kotlin-springboot`](../kotlin-springboot/SKILL.md) for the code itself — Result/DomainError, Modulith module
   boundaries, jOOQ repositories, Liquibase changelogs.

**An existing non-WellForge Spring project** → `/wellforge:adopt`, not a scaffold.

## Versions come from the project, never from a skill

The shipped preset (`templates/spring-kotlin-react/template/backend/pom.xml`) is the source
of truth for Spring Boot, Modulith, jOOQ and Liquibase versions, and a generated project's
own parent `pom.xml` is the source of truth for that project. A version written into a skill
is a version that goes stale silently — this skill and [`kotlin-springboot`](../kotlin-springboot/SKILL.md)'s Maven
reference had drifted a whole major apart (Boot 4.0/Modulith 2.0 here, 3.4.x/1.3.x there)
without either being wrong enough to notice.

Read the pin; don't recall it.

## What this skill is for now

- Deciding **which** path applies (above).
- The module conventions for adding a service by hand.
- Keeping the JVM/TS fork honest: `hono-ts-backend` and `pulumi-gcp-ts` point here for
  anything JVM, and this skill points back at them for anything that is not.
