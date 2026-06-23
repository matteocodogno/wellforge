---
name: react-ts-vite
description: >
  Expert React + TypeScript + Vite frontend development skill. Use this skill whenever the user asks
  to build, scaffold, extend, or refactor a React application using TypeScript. Triggers include:
  "create a React component", "build a page with React", "add a feature to my React app",
  "scaffold a new Vite project", "write a custom hook", "set up React Context", "add TanStack Query/Router",
  "style with Tailwind", "refactor this component", "use Effect TS in React", or any time the user
  describes frontend work in a React/TypeScript codebase. Always use this skill proactively whenever
  frontend React/TypeScript code is being produced — even if the user just says "create a form" or
  "add a new page". Prefer this skill over generic coding responses for any React work.
---

# React + TypeScript + Vite Skill

Production-grade React development with a clear, opinionated architecture. Every output must follow the conventions in this skill precisely.

## Quick Reference

| Concern | Choice |
|---|---|
| Bundler | Vite |
| Language | TypeScript (strict) |
| UI | React 18+ |
| Component Library | Mantine UI |
| Routing | TanStack Router |
| Data Fetching | TanStack Query |
| Forms | React Hook Form + Effect Schema |
| Styling | Tailwind CSS v3 (layout/spacing) + Mantine (components) |
| FP / Effects | Effect TS |
| State | React Context (no Redux/Zustand/Jotai) |
| Types vs Interfaces | **Always `type`** |
| Functions | **Always arrow/lambda** |
| Logic placement | **Hooks, never components** |
| Error Boundaries | `react-error-boundary` |
| Linting | ESLint + typescript-eslint + eslint-plugin-react-hooks |
| Formatting | Prettier + lint-staged + husky |

---

## Architecture

Read `references/architecture.md` for the full folder structure and feature-splitting conventions.  
Read `references/conventions.md` for all coding rules with examples.  
Read `references/effect-ts.md` for Effect TS patterns used in this stack.  
Read `references/setup.md` for tooling, env vars, ESLint, Prettier, and husky config.  
Read `references/ui-forms.md` for Mantine UI usage, React Hook Form patterns, and error boundaries.  
Read `references/performance.md` for code splitting, `useMemo`/`useCallback`, and `React.memo` rules.

> **When to read which file:**
> - Scaffolding a new project or setting up tooling → `architecture.md` + `setup.md`
> - Writing any component, hook, context, or utility → `conventions.md`
> - Writing data-fetching, validation, error handling, or business logic → `effect-ts.md`
> - Building forms or UI components → `ui-forms.md`
> - Optimising bundles or preventing re-renders → `performance.md`

---

## Core Principles (memorise these)

1. **Types, not interfaces** — use `type Foo = { ... }` everywhere.
2. **Lambdas, not functions** — `const foo = () => ...`, never `function foo()`.
3. **Logic in hooks** — components are pure render trees; all logic lives in custom hooks.
4. **Context for state** — no external state managers; use `React.createContext` + custom provider hooks.
5. **One component per file** — each file exports exactly one React component as default. Never put two components in the same file.
6. **One hook per file** — each custom hook lives in its own `.ts` file named after the hook (e.g. `useGameSocket.ts`).
7. **Hooks in a `hooks/` folder** — all hooks for a feature live in `features/<feature>/hooks/`. Shared hooks live in `src/shared/hooks/`. Never put a hook file directly in the feature root or inside a component file.
8. **Feature-first structure** — code is split by feature; shared code lives in top-level `components/`, `hooks/`, `contexts/`, `utils/`.
7. **Functional purity** — no mutations; prefer `map/filter/reduce`, spread, and immutable patterns.
8. **Effect TS for effects** — side-effects, async, validation, and error handling use Effect TS primitives.
10. **Mantine for UI** — use Mantine components first; Tailwind only for layout, spacing, and custom composition.
10. **React Hook Form for forms** — all form state via `useForm`; validation via Effect Schema resolver.
11. **Error boundaries everywhere** — every route and every async feature boundary is wrapped with `react-error-boundary`.
13. **Lazy-load every route** — all page components are `React.lazy`; wrap in `<Suspense>` at the router level.

---

## Checklist before emitting any code

- [ ] Every type is `type`, not `interface`
- [ ] Every function is an arrow function
- [ ] No business logic inside JSX return or component body (beyond trivial ternaries)
- [ ] State is managed via Context + hooks, not useState scattered across components
- [ ] Each file contains exactly one exported component
- [ ] Imports follow the canonical order (see conventions.md)
- [ ] Mantine components used for UI; Tailwind for layout/spacing only
- [ ] Forms use React Hook Form + Effect Schema resolver
- [ ] TanStack Query used for all server state; TanStack Router for all routing
- [ ] Effect TS used for async operations and error handling
- [ ] Route-level page components are `React.lazy` + wrapped in `<Suspense>`
- [ ] Every route-level and async feature boundary has an `<ErrorBoundary>`
- [ ] `useMemo`/`useCallback`/`React.memo` only added when there is a measured reason (see performance.md)
- [ ] Env vars use `VITE_` prefix and are typed in `vite-env.d.ts` (see setup.md)
