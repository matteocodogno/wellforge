# Codex adapter — hands-on smoke test

The human half of `adapters/smoke-test.py --adapter codex` and
`scripts/tests/codex-hooks.test.py`: a pass in a real Codex session, for the things no
script can see. Same structure as the [OpenCode](../opencode/SMOKE-TEST.md) and
[Copilot](../copilot/SMOKE-TEST.md) equivalents, so the three adapters are checked to one
standard.

## What is mechanical now, and what still needs you

CI runs both on every push. Together they assert that the output is non-empty, its links
resolve, coverage is complete, model ids match `config/model-tiers.yml`, the deterministic
layer is present and runs, the TOML parses, every hook in `hooks.json` runs an existing
script — and that those hooks, fed Codex-shaped payloads, refuse and allow what the plugin's
own matrices say they should, from the root and from a subdirectory.

**A green CI means the files are right, not that Codex reads them the way this adapter
assumes.** The assumptions are listed in each section below; each one is a fact about Codex
(as documented 2026-10) that only a running Codex can confirm.

## 0. Prerequisites
- [ ] Codex CLI installed and signed in (`codex --version`); `jq` and `git` on PATH.
- [ ] A throwaway git repo with WellForge's shape, so the hooks have something to guard:
  ```bash
  mkdir -p /tmp/wf-codex-test/specs/001-x && cd /tmp/wf-codex-test && git init -q
  printf -- '---\nid: 001\ntitle: X\nstatus: in-progress\nrigor: production\n---\n# Spec\n- AC-1: a thing\n' > specs/001-x/spec.md
  printf -- '# Tasks\n- [ ] T1\n' > specs/001-x/tasks.md
  ```

## 1. Generate
- [ ] From the WellForge repo:
  ```bash
  uv run --with pyyaml python adapters/codex/generate.py --out /tmp/wf-codex-test
  cd /tmp/wf-codex-test && git add -A && git commit -qm "chore: base" && codex
  ```
- [ ] Codex asks whether to trust the project — **trust it** (project `.codex/` config,
      agents and hooks load only in a trusted project).

## 2. Hooks — *assumes: project hooks.json loads; `^Bash$` / `^apply_patch$` matchers match*
- [ ] `/hooks` lists the WellForge hooks as untrusted. Review and trust them.
- [ ] Ask: *"run `cat .env`"* → refused with `BLOCKED: touches protected file`.
- [ ] Ask: *"create a file .env with FOO=1"* → the patch is refused with
      `BLOCKED: .env is a protected secret file`. **This is the one that proves the
      apply_patch translation in a live session** — if the file appears, stop: the hook
      did not fire, and every file guard is absent.
- [ ] Ask: *"change rigor in specs/001-x/spec.md to spike"* → refused after the write, with
      the revert instruction (post-spec-guard).
- [ ] Ask: *"add an AC-2 to specs/001-x/spec.md"* and end the turn → the Stop hook reports
      spec drift and Codex **continues the turn** on it (Stop `decision: block` semantics).
- [ ] Start a new session → the first context carries `=== SESSION CONTEXT ===`.

## 3. Command skills — *assumes: `.agents/skills` discovered; openai.yaml policy honoured*
- [ ] `/skills` lists the 23 `wf-*` command skills and the 24 WellForge skills.
- [ ] `$wf-status` runs and prints the feature table (the deterministic layer via `$WF`).
- [ ] `$wf-spec a CSV export of the orders list` → `ARGUMENTS` is understood as that text.
- [ ] **Implicit invocation is off:** say *"let's release this"* without `$` — Codex must
      **not** start `wf-release`. If it does, `allow_implicit_invocation: false` is not being
      honoured and the README's safety claim is wrong.
- [ ] Say *"I'm about to write a spec"* — the `spec-driven` skill (implicit) may load.

## 4. Agents — *assumes: `.codex/agents/*.toml` discovered; `model` honoured*
- [ ] Ask Codex to *"spawn the wf-architect agent to review specs/001-x"* — it runs, and
      reports which model it used (expect `gpt-5.5`; a different one means the id in
      `model-tiers.yml` is stale for your account — fix it there and regenerate).
- [ ] The run appends a line to `.forge/runs/.events.jsonl` (SubagentStop → trace-subagent).
      Record whether its token fields are filled; the README says "best-effort, expect
      empty" until this step says otherwise.
- [ ] Ask for two independent read-only agents at once (owasp-reviewer + evaluator) — they
      run in parallel.

## 5. MCP — *assumes: `[mcp_servers]` in project config.toml loads*
- [ ] `/mcp` lists `sequential-thinking`, `playwright`, `context-hub`, `github`.
- [ ] `codex mcp login github` completes OAuth (no token is written to the repo).

## 6. The native plugin — *assumes: the portable package layout, onboarding skill, PLUGIN_ROOT*
In a **fresh** throwaway repo (no per-project adapter in it — the two modes are not mixed):
- [ ] `codex plugin marketplace add <path-to-wellforge-checkout>` (or
      `matteocodogno/wellforge --ref plugin-vX.Y.Z`), then install WellForge from it.
      Record whether Codex also picked up `.claude-plugin/marketplace.json` (the Claude
      marketplace, same name) and what it made of it.
- [ ] `/skills` lists `wf-setup`, the 23 `wf-*` commands and the 24 skills **under those
      names** — if Codex namespaces plugin skills (e.g. `wellforge:wf-spec`), every
      `$wf-x` reference in the generated text is wrong; record the real form.
- [ ] The onboarding skill runs after install (or run `$wf-setup`): `.codex/agents/` gets
      10 `wf-*.toml`, `.codex/wellforge/VERSION` the plugin's version, `AGENTS.md` a block.
- [ ] `/mcp` lists the four servers from the plugin's `mcp.json`.
- [ ] `/hooks` lists the plugin's hooks — trust them, then repeat the secret-file patch
      from §2: refused. **If `/hooks` does not list them** (CLI install), run
      `$wf-setup --hooks`, trust those, and repeat. Record which applied.
- [ ] Set `.codex/wellforge/VERSION` by hand to `0.0.1`, start a session → the first
      context says the project is behind the plugin.

## 7. Record the result
Update the **Status** section of [`README.md`](README.md): the date, the Codex version, and
every box above that did not hold — with what happened instead. A failed assumption is a
README correction or an adapter fix, never a silent skip.
