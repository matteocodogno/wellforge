#!/bin/bash
# Telegram is optional. Configure with the guided wizard:  wellforge telegram
# (writes ~/.config/wellforge/telegram.env; also sourced from ~/.zshrc)
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
command -v osascript &>/dev/null && \
  osascript -e "display notification \"$BODY\" with title \"$TITLE\" sound name \"Glass\"" 2>/dev/null
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=${EMOJI} *${TITLE}*%0A${BODY}" \
    -d "parse_mode=Markdown" > /dev/null 2>&1 &
fi
exit 0
