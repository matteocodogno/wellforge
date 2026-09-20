#!/bin/bash
# Notification hook — macOS banner + optional Telegram DM.
# Telegram is optional. Configure with the guided wizard:  wellforge telegram
# (writes ~/.config/wellforge/telegram.env; also sourced from ~/.zshrc)
#
# TWO INJECTION SURFACES, both closed here — the message text is NOT ours. It comes from
# the harness and can contain anything a prompt, a path or an error string contains:
#   * AppleScript: interpolating it into `osascript -e "...\"$BODY\"..."` lets a double
#     quote end the string and the rest run as AppleScript. Passed as argv instead.
#   * Telegram: `parse_mode=Markdown` makes an unpaired _ or * a 400 the user never sees
#     (the call is backgrounded and output discarded), so a message about `snake_case_name`
#     silently sends nothing. Sent as plain text — no parse mode, no escaping to get wrong.
#     And `-d` does not URL-encode: an `&` in the body truncates the field, so every field
#     goes through --data-urlencode.
INPUT=$(cat)
if [ -z "$TELEGRAM_BOT_TOKEN" ] && [ -f "$HOME/.config/wellforge/telegram.env" ]; then
  # shellcheck source=/dev/null
  . "$HOME/.config/wellforge/telegram.env"
fi
PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-$(pwd)}")
NOTIFICATION_TYPE=$(echo "$INPUT" | jq -r '.notification_type // "unknown"')
MESSAGE=$(echo "$INPUT" | jq -r '.message // ""')
case "$NOTIFICATION_TYPE" in
  "permissionprompt") TITLE="Claude needs permission"; EMOJI="🔐" ;;
  "idleprompt")       TITLE="Claude is waiting";       EMOJI="⏳" ;;
  "authsuccess")      TITLE="Claude authenticated";    EMOJI="✅" ;;
  *)                  TITLE="Claude Code";             EMOJI="🤖" ;;
esac
BODY="${PROJECT_NAME}: ${MESSAGE:-Needs your attention}"

if command -v osascript >/dev/null 2>&1; then
  osascript - "$BODY" "$TITLE" <<'OSA' >/dev/null 2>&1
on run argv
  display notification (item 1 of argv) with title (item 2 of argv) sound name "Glass"
end run
OSA
fi

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${EMOJI} ${TITLE}
${BODY}" > /dev/null 2>&1 &
fi
exit 0
