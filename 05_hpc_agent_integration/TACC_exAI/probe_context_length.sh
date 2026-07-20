#!/usr/bin/env bash
set -euo pipefail

: "${EXAI_BASE_URL:?EXAI_BASE_URL is not set}"
: "${EXAI_API_KEY:?EXAI_API_KEY is not set}"

MODEL="Qwen3-32B"

START=5000
STEP=5000
MAX_TRIES=50   # safety cap

echo "Probing context window for model: $MODEL"
echo "Base URL: $EXAI_BASE_URL"

total_tokens=$START

while (( total_tokens > 0 )); do
  prompt_tokens=$(( total_tokens / 2 ))
  max_tokens=$(( total_tokens - prompt_tokens ))

  echo
  echo "=== Trying total tokens: $total_tokens (prompt ~${prompt_tokens}, max_tokens ${max_tokens}) ==="

  prompt=$(printf 'token %.0s' $(seq 1 "$prompt_tokens"))

  # Let curl fail softly so we can inspect the response
  response=$(curl -sS "${EXAI_BASE_URL%/}/v1/chat/completions" \
    -H "Authorization: Bearer $EXAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d @- <<EOF || true
{
  "model": "$MODEL",
  "messages": [
    {"role": "user", "content": "$prompt"}
  ],
  "max_tokens": $max_tokens
}
EOF
  )

  # Try to see if there is an error field; if so, stop
  error_message=$(printf '%s' "$response" | jq -r '.error.message // empty' 2>/dev/null || true)

  if [[ -n "$error_message" ]]; then
    echo "Received error from server:"
    echo "$response"
    echo
    echo "Stopped at total_tokens=$total_tokens"
    exit 0
  else
    echo "Request accepted at total_tokens=$total_tokens"
  fi

  ((MAX_TRIES--))
  if (( MAX_TRIES <= 0 )); then
    echo "Hit MAX_TRIES without triggering an error. Stopping."
    exit 1
  fi

  total_tokens=$(( total_tokens + STEP ))
done
