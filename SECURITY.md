# Security

## Reporting a vulnerability

**Do not open a public issue.** Use either:

- **GitHub private security advisory** — [Security → Report a vulnerability](https://github.com/matteocodogno/wellforge/security/advisories/new)
  on this repo. Preferred: it keeps the report, the fix and the disclosure in one place.
- **Email** — matteo.codogno@welld.ch, subject `wellforge security`. Say "wellforge" in the
  first line so it is not read as ordinary mail.

Include what you did, what happened, and what you expected. A proof of concept helps; a
working exploit is not required and you do not need to weaponise anything to be taken
seriously.

**Response:** acknowledgement within **3 working days**, an assessment (accepted / not a
vulnerability / needs more information) within **10 working days**. This is a small project
maintained alongside other work — that is the honest commitment, not a same-day SLA.

**Which versions get fixes:** the **newest tag of each of the four series** only
([docs/VERSIONING.md](docs/VERSIONING.md)) — template `vX.Y.Z`, `gates-vN`,
`plugin-vX.Y.Z`, `cli-vX.Y.Z`. There are no long-term support branches and nothing is
backported. A fix ships as a new tag in whichever series owns the code; generated projects
pick up gate fixes by bumping their `gates_ref`, which is a raise-only step in
`/wellforge:upgrade`.

Please give us a reasonable window to ship a fix before disclosing publicly. We will credit
you unless you ask us not to.

---

## Threat model — the plugin on a developer's machine

This is what the plugin actually does when installed, so you can decide whether you want it.
It is written to be uncomfortable where the truth is uncomfortable.

### The hooks run shell on your machine, on every tool call

`wellforge-plugin/hooks/hooks.json` registers seven hooks. Two of them are guards that run
**before** a tool call: `pre-bash-guard.sh` on every `Bash`, and `pre-file-guard.sh` on every
`Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit` and `Grep`. The rest run on
`SessionStart`, `PostToolUse` (`Write|Edit|MultiEdit|NotebookEdit`), `Notification`, `Stop`,
`SubagentStop` and `PreCompact`.

If you enable the plugin at **user scope**, that is every session in every repository on the
machine, not only WellForge projects. The hooks are ordinary bash scripts in the plugin
directory; you can read all of them in a few minutes, and you should.

**What they read:** the tool-input JSON that Claude Code pipes to them on stdin — for a Bash
call, the command *text*; for a file call, the *path*. **What they do not read:** the
contents of your files. `pre-bash-guard.sh` matches on the command string and never opens
what the command would open, which is why its own header calls every rule "an approximation"
and keeps it tight in both directions.

**They fail OPEN without `jq`, not closed.** Every guard's first act is
`jq -r '.tool_input.command // empty'`; with no `jq` on `PATH` that yields empty, and the
next line is `[ -z "$COMMAND" ] && exit 0` — *allow*. Measured, not assumed: with `jq`
removed from `PATH`, a command the guard blocks outright is waved through with exit 0. So on
a machine without `jq` the guards are decoration, silently. `/wellforge:doctor` reports this
("every hook — they exit 0 without it, silently doing nothing") and `jq` is a documented
prerequisite, but nothing stops a session running without it. If you rely on these guards,
check `jq --version` first.

### MCP servers are fetched from npm and run as you

`.mcp.json` starts three stdio servers through `npx`, which means npm downloads and executes
code on your machine, with your user's permissions and network access:

| Server | Package | Network |
|---|---|---|
| `sequential-thinking` | `@modelcontextprotocol/server-sequential-thinking@2026.8.31` | none |
| `playwright` | `@playwright/mcp@0.0.82` | drives a real browser — whatever you point it at |
| `context-hub` | `@aisuite/chub@0.1.4` | the Context Hub service |

plus `github`, which is HTTP to `api.githubcopilot.com` and holds an OAuth token you grant
on first use.

**Every one of them names an exact version.** `playwright` and `sequential-thinking` used to
resolve `@latest`, which is a dependency chosen at launch by whatever the registry served
that minute — a supply-chain surface with no review step and no record of what anyone
actually ran. Pinning does not make a package trustworthy; it makes the version a reviewable
fact, and an upgrade an ordinary plugin patch release with a diff. `check-docs.py` fails CI
if any npx server carries a moving tag or no version.

You are still trusting those publishers. If that is not acceptable, remove the server from
`.mcp.json` — the plugin degrades rather than breaks.

### Prompt injection from the content the agents read

The agents read repository content: specs, `AGENTS.md`, code comments, existing files, PR
descriptions, issue text you paste in. **Any of that can contain instructions, and an agent
asked to implement a file will follow instructions it finds inside that file.** There is no
content sanitisation anywhere in this plugin, and there is no boundary marker that separates
"data the agent is reading" from "instructions the agent was given". Treat a repository you
did not write as untrusted input to an agent that can write code and run commands.

What exists today is defence in depth, not a solution:

- **Two human gates** in the spec-driven flow — a spec is approved by a person before a plan
  exists, and a plan before tasks. Injected work has to survive a human reading the artifact.
- **The evaluator's adversarial rubric** scores trajectory and spec fidelity, so work that
  does not correspond to the approved spec loses points.
- **The security floor** runs at every rigor tier, including `spike`, so scanning is not
  something a tier can turn off.
- **The guards** refuse the loudest exfiltration shapes, within the limits above.

What does not exist: sanitisation, provenance tracking on file content, or any check that
the instructions an agent followed came from the spec rather than from a file it opened. If
you are running this against untrusted repositories, that is the gap to know about.

### Secrets

`.mise.local.toml` is the sanctioned store — gitignored, per-checkout, never templated. The
guards refuse commands and file operations that name `.env`, `.pem`, `.key` and
`secrets.yml`, and refuse writes to `.mise.local.toml` except through the sanctioned forms.

The limits are documented in `pre-bash-guard.sh`'s own header and are real: the rules match
**command text**, so they approximate "touches a secret" and can be both too tight and too
loose. `.env.ci` and `.env.local` still block even when harmless; `production.env` no longer
blocks; metadata-only queries like `git check-ignore` are deliberately carved out, and that
carve-out applies only to a single simple command with no separator or substitution. Real
secret *content* is backstopped elsewhere — a gitleaks pre-commit hook and the security-floor
CI gate — because a text matcher on a command line was never going to be the last line.

### Generated projects

A scaffold is not a copy of the gates; it **pins** them (`gates-vN`) and calls them as
reusable workflows, so a gate fix reaches every project by bumping one ref rather than by
re-templating. The security floor is called at every rigor tier.

Two escape hatches exist and both are **recorded, not silent**: `--skip-checks` on a CLI
release prints a banner and writes the skip into the commit body *and* the annotated tag,
and `rigor: spike` is written into the manifest and the spec frontmatter where
`/wellforge:status` and the done gate both read it. Lower rigor is tracked debt that
`/wellforge:promote` pays off — it is never a quiet default.
