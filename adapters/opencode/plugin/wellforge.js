// WellForge enforcement plugin for OpenCode — drop-in at .opencode/plugins/wellforge.js
// Ports the high-value Claude Code hooks. TS types (optional, for editing) via
// `import type { Plugin } from "@opencode-ai/plugin"`. Plain JS so it needs no install.
//
// Parity note (until the shared core is extracted): the guard patterns here mirror
// wellforge-plugin/hooks/scripts/pre-bash-guard.sh — change both together.
// Not ported: token-trace observability (OpenCode exposes no subagent-usage event) and
// pre-compact backup. Enforcement that can't run here is covered by the CI quality gates.

export const WellForge = async ({ $, client }) => {
  const deny = (msg) => { throw new Error(`WellForge: ${msg}`) }

  return {
    // ── pre-bash guard — block dangerous commands (throw denies the call) ──
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "bash") return
      const cmd = (output && output.args && output.args.command) || ""
      if (/rm\s+-[a-zA-Z]+\s+(\/|\/\*|~|~\/\*?|\*)(\s|[;"')]|$)/.test(cmd))
        deny("blocked recursive deletion from root/home")
      if (/DROP\s+DATABASE|DROP\s+TABLE\s+\w+\s*;|TRUNCATE\s+TABLE/i.test(cmd))
        deny("destructive SQL requires manual execution")
      if (/(curl|wget)[^|]+\|\s*(ba|z)?sh(\s|;|$)/.test(cmd))
        deny("piping remote scripts into a shell is not allowed")
      const scrubbed = cmd.replace(/\.env\.example/g, "").replace(/\.env\.jinja/g, "")
      if (/\.(env|pem|key)([^A-Za-z0-9_]|$)|secrets\.ya?ml/.test(scrubbed))
        deny("touches a protected file (.env / .pem / .key / secrets.yml)")
    },

    // ── post-lint — format the file just edited (best-effort; never fails the session) ──
    "file.edited": async (event) => {
      const f = (event && event.file) || ""
      try {
        if (/\.(ts|tsx)$/.test(f)) {
          await $`pnpm exec prettier --write ${f}`.quiet().nothrow()
          await $`pnpm exec eslint --fix ${f}`.quiet().nothrow()
        } else if (/\.(kt|kts)$/.test(f)) {
          await $`./mvnw com.github.gantsign.maven:ktlint-maven-plugin:format -q --no-transfer-progress`.quiet().nothrow()
        } else if (/\.(json|ya?ml)$/.test(f)) {
          await $`pnpm exec prettier --write ${f}`.quiet().nothrow()
        }
      } catch { /* tooling absent — leave it to CI */ }
    },

    // ── spec-drift check — surfaced when the session goes idle (can't block here) ──
    "session.idle": async () => {
      try {
        const changed = (await $`git diff --name-only`.quiet().nothrow().text()).split("\n")
        const specChanged = changed.filter((l) => /specs\/[^/]+\/(spec|plan)\.md$/.test(l))
        const tasksChanged = changed.some((l) => /specs\/[^/]+\/tasks\.md$/.test(l))
        if (specChanged.length && !tasksChanged) {
          await client.app.log({ body: {
            service: "wellforge", level: "warn",
            message: `spec/plan changed without re-syncing tasks.md (${specChanged.join(", ")}) — run /tasks to sync (drift rule)`,
          }})
        }
      } catch { /* not a git repo / no specs — nothing to check */ }
    },
  }
}
