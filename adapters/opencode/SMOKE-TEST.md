# OpenCode adapter — hands-on smoke test

The human half of `adapters/smoke-test.py`: a pass in a real OpenCode session, for the
things no script can see. Structured like the [Copilot equivalent](../copilot/SMOKE-TEST.md)
so the two adapters are checked to the same standard.

## What is mechanical now, and what still needs you

`adapters/smoke-test.py` runs in CI on every push (`adapter-smoke` in
`.github/workflows/ci.yml`) and asserts four things about freshly generated output:

```bash
uv run --with pyyaml python adapters/smoke-test.py --adapter opencode
uv run --with pyyaml python adapters/smoke-test.py --adapter opencode --keep /tmp/wf-opencode-test
```

| Assertion | Why it is mechanical |
|---|---|
| a. no generated file is empty | both generators once emitted 44 zero-byte skill files and still reported "44 skill files" — a count is not content |
| b. every relative link resolves | the plugin's links are correct in the *plugin* tree; the adapter writes a different tree |
| c. every command/agent/skill has a counterpart, or is declared absent in the README | a generator that silently stops emitting one artifact kind looks identical in its summary |
| d. model names match `config/model-tiers.yml` | a stale generated `model:` sends work to the wrong tier and nothing complains |

**A green script means the artifacts are well-formed, not that OpenCode accepts them.**
Everything below is the part that needs a human and a running tool. Run the script with
`--keep` first, then open that folder.

## 0. Prerequisites
- [ ] [OpenCode](https://opencode.ai) installed and authenticated for the provider you
      generated with (`--provider anthropic` by default).
- [ ] A throwaway git repo so `.opencode/` doesn't collide with anything:
  ```bash
  mkdir /tmp/wf-opencode-test && cd /tmp/wf-opencode-test && git init
  ```

## 1. Generate
- [ ] From the WellForge repo:
  ```bash
  uv run --with pyyaml python adapters/smoke-test.py --adapter opencode --keep /tmp/wf-opencode-test
  ```
- [ ] All four assertions pass. If any fail, **stop** — that is an adapter bug, and the
      session pass below would only be testing broken files.
- [ ] `cd /tmp/wf-opencode-test && opencode` — start it with the generated folder as the
      project root (OpenCode resolves `.opencode/` from there).

## 2. Commands (`/wf-*`)
- [ ] Type `/` — confirm the `wf-` commands appear (20).
- [ ] Run `/wf-spec` with a one-line feature description — confirm `$ARGUMENTS` is
      substituted, not printed literally.
- [ ] Confirm the body refers to `/wf-plan`, never `/wellforge:plan` — ref translation landed.
- [ ] Confirm one of *your* own commands (if you have a `/spec`) is untouched: the `wf-`
      prefix exists precisely because OpenCode commands are unnamespaced.

## 3. Agents (`wf-*`)
- [ ] Confirm the subagents are listed (10) and that `wf-architect` resolves to a real model
      for your provider — a wrong-but-valid model name passes assertion (d) and fails here.
- [ ] Dispatch one (`@wf-architect` or the task tool) on a trivial question — confirm it
      answers **in role** rather than as the default assistant.
- [ ] Confirm the `permission` block is honoured: `wf-designer` should not be able to edit
      production code.

## 4. Skills
- [ ] `.opencode/skills/` contains all 21 skills with their `references/`.
- [ ] Ask a backend-shaped question in a Kotlin file's context — confirm the
      `kotlin-springboot` conventions are actually pulled in. OpenCode has no `applyTo`
      glob scoping, so skills are loaded on demand rather than automatically: if nothing
      loads, that is the known difference, not a bug.

## 5. MCP servers
- [ ] `opencode.json` lists all 4 (`sequential-thinking`, `playwright`, `github`,
      `context-hub`) under `mcp`, in OpenCode's local/remote schema.
- [ ] At least one reaches a running state and its tools appear in a session.

## 6. Enforcement plugin
- [ ] `.opencode/plugins/wellforge.js` loads without an ESM error at startup.
- [ ] **bash guard** (`tool.execute.before`): ask it to run `cat .env` → must be **denied**.
      Confirm `cat .env.example` is **allowed** — the guard's false-positive direction is
      what makes people route around it.
- [ ] **post-lint** (`file.edited`): edit a `.ts` file → prettier/eslint runs (best-effort;
      a missing toolchain is environmental, not an adapter bug).
- [ ] **spec-drift** (`session.idle`): with `specs/001-x/` where `spec.md` is newer than
      `tasks.md`, let the session go idle → confirm it **warns**. It cannot block on idle;
      a warning is the pass.

## 7. Known gaps — confirm, don't fail
- [ ] No token/run-trace observability: `.forge/runs/` is not populated (no OpenCode
      subagent-usage event). Expected — CI gates cover enforcement.
- [ ] `session-start` / `pre-compact` hooks are not ported. Expected.
- [ ] `visual-companion` is present in the library but Claude-Code-specific — not exercised.

## 8. Sign-off
- [ ] Record pass/fail per section. A failure in **2, 3, 5 or 6** is a real adapter bug:
      capture the OpenCode version, the exact file and the error, and fix `generate.py` —
      then add the case to `adapters/smoke-test.py` if a script could have caught it.
      Sections 4 and 7 failing on scoping or missing events is the documented support tier,
      not a regression.
