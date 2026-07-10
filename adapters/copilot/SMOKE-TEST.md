# Copilot adapter — VS Code smoke test

Step 8 of `docs/PLAN-copilot-adapter.md`: a hands-on pass in a real VS Code + Copilot session.
Ordered so each artifact type is verified independently, with explicit pass criteria and the
two known gaps called out so they aren't flagged as bugs.

## 0. Prerequisites
- [ ] VS Code (latest) with the **GitHub Copilot** + **GitHub Copilot Chat** extensions,
      signed in on a plan that exposes the model picker.
- [ ] A throwaway git repo to generate into (so the `.github/` layer doesn't collide):
  ```bash
  mkdir /tmp/wf-copilot-test && cd /tmp/wf-copilot-test && git init
  ```

## 1. Generate the adapter
- [ ] From the WellForge repo:
  ```bash
  uv run --with pyyaml python adapters/copilot/generate.py --out /tmp/wf-copilot-test
  ```
- [ ] Confirm the summary: `17 prompts · 10 chat modes · 9 instruction files · 3 MCP servers · 1 githook config`.
- [ ] `open -a "Visual Studio Code" /tmp/wf-copilot-test` — open the **generated** folder as the
      workspace root (Copilot resolves `.github/` from the workspace root).

## 2. Enable the relevant settings (Settings JSON)
- [ ] `"chat.promptFiles": true` — enables `.prompt.md` and `.instructions.md`.
- [ ] `"github.copilot.chat.codeGeneration.useInstructionFiles": true` — enables `.github/copilot-instructions.md`.
- [ ] MCP enabled (`"chat.mcp.enabled": true` if present in your version).
- [ ] Reload window after changing these.

## 3. Prompt files (`/wf-*`)
- [ ] Open Copilot Chat, type `/` — confirm `wf-spec`, `wf-plan`, `wf-orchestrate`, … appear (17 total).
- [ ] Run `/wf-spec` — confirm it prompts for input with the **argument-hint placeholder**
      (`<feature description> | <NNN-slug to resume>`), i.e. `${input:args}` resolved.
- [ ] Confirm the body references `/wf-plan` (not `/wellforge:plan`) — ref translation landed.
- [ ] Spot-check one more (`/wf-tasks`) runs without a "malformed prompt file" warning.

## 4. Custom chat modes (`wf-*`)
- [ ] Open the chat **mode dropdown** (where Ask/Edit/Agent live) — confirm the `wf-*` modes
      appear (`wf-architect`, `wf-backend-dev`, … 10 total).
- [ ] Select `wf-architect` — confirm the **model** resolves to a real picker entry
      (`Claude Opus 4.1` by default; if your plan lacks it, note the fallback — expected,
      picker names are plan-dependent).
- [ ] Confirm no "unknown tool" hard error on mode entry (unknown tool names are
      warned-and-ignored by Copilot — acceptable).
- [ ] Switch to `wf-designer` — sanity check it behaves as a persona (it keeps `editFiles`;
      the "never edit production code" rule is prompt-enforced, per the known limitation).

## 5. Instructions — glob-scoped + repo-wide
- [ ] Create `src/Foo.kt` and open it. Ask something backend-y. Confirm the **Kotlin/Spring
      conventions** are in play (references block / Result-DomainError guidance) — proves
      `wf-kotlin-springboot.instructions.md`'s `applyTo: **/*.kt` fired.
- [ ] Open a `.tsx` file → confirm the React instructions apply instead. Open a plain `.md`
      outside `specs/` → confirm **neither** stack instruction loads (scoping works, no bloat).
- [ ] Create `specs/001-x/spec.md` and open it → confirm `wf-spec-driven.instructions.md`
      (`applyTo: specs/**`) applies.
- [ ] Verify the **references panel** in a chat response lists `.github/copilot-instructions.md`
      (repo-wide guide is being pulled).

## 6. Skill library
- [ ] Confirm `.github/wf-skills/kotlin-springboot/references/` has its 5 deep-dive files
      (agent can `#file`-reference them on demand).
- [ ] Grep the library for leftover refs (should be none):
  ```bash
  grep -rl '/wellforge:' /tmp/wf-copilot-test/.github/wf-skills && echo "LEAK" || echo "clean"
  ```

## 7. MCP servers
- [ ] Open the MCP servers view (Command Palette → "MCP: List Servers", or the Chat tools
      picker). Confirm `sequential-thinking`, `playwright`, `github` are listed from `.vscode/mcp.json`.
- [ ] Start `sequential-thinking` (stdio/npx) — confirm it reaches **Running** (needs network for `npx -y`).
- [ ] In an agent-mode chat, confirm its tool(s) show up in the tool list. (The `github` HTTP
      server pointing at Copilot's own MCP endpoint may be redundant inside Copilot — fine to
      leave disabled.)

## 8. Git-hook fallback (lefthook)
- [ ] `cd /tmp/wf-copilot-test && lefthook install` (install lefthook if needed).
- [ ] **secret-scan:** `touch .env && git add .env && git commit -m x` → must be **BLOCKED**
      ("staged secret/protected file: .env"). Confirm `.env.example` is **not** blocked.
- [ ] **spec-drift:** with a `specs/001-x/tasks.md` present, stage only `spec.md` and commit →
      blocked with the `/wf-tasks` drift message.
- [ ] (Optional, needs toolchains) **lint/compile:** stage a `.ts`/`.kt` file → prettier/ktlint
      run on commit; `tsc`/`mvnw compile` run on push.

## 9. Known gaps — confirm, don't fail
- [ ] `/wf-orchestrate` runs as a **single sequential session** (no parallel subagents) — expected.
- [ ] No token/run-trace observability (`.forge/runs/` not populated by Copilot) — expected;
      CI gates cover enforcement.
- [ ] `visual-companion` skill is present in the library but is Claude-Code-specific — not exercised here.

## 10. Sign-off
- [ ] Record pass/fail per section. Any failure in **3, 4, 5, or 7** is a real adapter bug →
      capture the VS Code version, the exact file, and the error, and fix `generate.py`.
      Sections 8–9 failing on missing toolchains/network is environmental, not an adapter bug.
</content>
