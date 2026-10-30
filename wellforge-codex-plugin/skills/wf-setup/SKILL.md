---
name: wf-setup
description: "WellForge command — set up (or refresh) WellForge in this project after installing the WellForge Codex plugin: the agent team, the scripts the $wf-* commands run, the eval rubric and the AGENTS.md block. Run once per project and again after every plugin update. Invoke explicitly: $wf-setup [--hooks]"
---
> WellForge Codex plugin — hand-written source in `adapters/codex/plugin/wf-setup/`; the
> plugin's onboarding skill. **ARGUMENTS** below means the text the user wrote after
> `$wf-setup` (empty if nothing).

# WellForge setup

The plugin gave this Codex the WellForge skills, MCP servers and hooks. What a plugin
cannot carry is copied into the project by this skill's installer: the custom agents
(`.codex/agents/wf-*.toml`), the deterministic layer every `$wf-*` command calls as `$WF`
(`.codex/wellforge/`), and a short WellForge block in `AGENTS.md`.

## Steps

1. **Be in the project.** Run `git rev-parse --show-toplevel`. If it fails, stop and tell
   the user to open their project in Codex and run `$wf-setup` there — this skill also runs
   right after the plugin is installed, which may be outside any project.
2. **Run the installer** that sits next to this file, `scripts/install.sh` (resolve it
   against the directory this SKILL.md was loaded from), passing ARGUMENTS through:
   ```bash
   bash "<this skill's directory>/scripts/install.sh" ARGUMENTS
   ```
   It is idempotent, writes only WellForge-owned files and the marked `AGENTS.md` block, and
   prints what it did. Do not copy or edit those files yourself — on a failure, report the
   installer's message and stop.
3. **Hooks.** Ask the user to open `/hooks`:
   - the WellForge hooks are listed → they must **trust** them (Codex skips an untrusted
     hook, and asks again after every plugin update that changes one);
   - they are **not** listed (a Codex that does not run plugin hooks) → re-run with
     `--hooks`, which installs them into `.codex/hooks.json`, then trust them there.
   Without trusted hooks nothing refuses `cat .env`, a lowered `rigor:` or a hand-written
   `status: done` — say so plainly rather than reporting the setup as complete.
4. **Report** the installer's summary, then: commit `.codex/` and `AGENTS.md` so the team
   gets the same setup, and run `$wf-doctor` to check tools and MCP servers, then
   `$wf-status` (or `$wf-spec <feature>` to start).
