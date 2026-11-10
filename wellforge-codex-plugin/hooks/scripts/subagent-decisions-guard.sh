#!/bin/bash
# SubagentStop hook — a dev or devops agent may not hand back work without its DECISIONS block.
#
# Why: the decision ledger records what the USER decided. What an implementing agent decided
# on the user's behalf — a default it picked, something it left out, a requirement it read
# one way when two readings were possible, an assumption it never checked — lived only in the
# code, where a reviewer finds it by accident or not at all. That is how delegation turns into
# surrender: the work is accepted without anyone knowing which choices were in it. The
# agents' prompts ask for the block (spec-driven skill, "decisions.md"); a prompt is a
# request, so this hook makes it a rule: no block, the agent is sent back once to write it.
#
# Exit 2 on SubagentStop makes the subagent continue with stderr as the reason. Once only:
# with `stop_hook_active` set the agent has already been sent back, and a second refusal
# would loop. Fails OPEN everywhere else — no jq, not a WellForge project, an agent this rule
# is not about, or a harness that exposes no final message: a guard that cannot read the
# report must not block a session on a guess.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

{ [ -d "$PROJECT_DIR/specs" ] || [ -d "$PROJECT_DIR/.forge" ]; } || exit 0
command -v jq >/dev/null 2>&1 || exit 0
[ "$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)" = "true" ] && exit 0

# The implementing agents only: their choices land in code. The architect's land in plan.md,
# which a human approves line by line; QE, evaluator and reviewers judge, they do not build.
# Claude Code names plugin agents `wellforge:backend-dev`, Codex `wf-backend-dev`.
ATYPE=$(printf '%s' "$INPUT" | jq -r '(.agent_type // .subagent.agent_type // .subagent_type // empty)' 2>/dev/null)
case "$ATYPE" in
  *backend-dev|*frontend-dev|*devops) ;;
  *) exit 0 ;;
esac

# The final message: inline on recent harnesses, else the last assistant text in the
# subagent's own transcript.
MSG=$(printf '%s' "$INPUT" | jq -r '(.last_assistant_message // empty)' 2>/dev/null)
if [ -z "$MSG" ]; then
  TP=$(printf '%s' "$INPUT" | jq -r '(.agent_transcript_path // .transcript_path // empty)' 2>/dev/null)
  if [ -n "$TP" ] && [ -f "$TP" ]; then
    MSG=$(jq -rs '[ .[] | select(.type == "assistant")
                    | [ (.message.content // [])[]? | select(.type == "text") | .text ] | join("\n")
                    | select(length > 0) ] | last // empty' "$TP" 2>/dev/null)
  fi
fi
[ -n "$MSG" ] || exit 0

# A line that starts the block, markdown decoration allowed: `DECISIONS:`, `**DECISIONS:**`,
# `## DECISIONS`, `- DECISIONS: none — ...`.
if printf '%s\n' "$MSG" | grep -Eiq '^[[:space:]>*#_-]*DECISIONS[*_]*([[:space:]]*:|[[:space:]]*$)'; then
  exit 0
fi

cat >&2 <<'EOF'
Your report has no DECISIONS block. Before you return, add one — the caller records it in
specs/NNN-slug/decisions.md and the human reads it before closing the feature:

DECISIONS:
- default: <what you picked where the spec/plan/task was silent> — why: <reason> — where: <file or task>
- scope: <what you left out or deferred> — why: … — where: …
- reinterpretation: <requirement you read one way when another reading was possible> — why: … — where: …
- assumption: <what you took as true and did not verify> — why: … — where: …

Only choices the spec, plan and task text did not dictate. If there were none, say so in one
line: `DECISIONS: none — <why nothing was left open>`.
EOF
exit 2
