#!/usr/bin/env bash
set -euo pipefail

: "${OPENHANDS_HOST:?Set OPENHANDS_HOST to the Replicated app URL}"
: "${OPENHANDS_API_KEY:?Set OPENHANDS_API_KEY without storing it in the repository}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
prompt="$(<"${script_dir}/prompt.txt")"
model="${OPENHANDS_AUTOMATION_MODEL:-Bedrock-Claude-Haiku-4-5}"

payload="$(
  jq -n \
    --arg prompt "${prompt}" \
    --arg model "${model}" \
    '{
      name: "Research Lab - Replicated Scheduled Controller",
      prompt: $prompt,
      model: $model,
      trigger: {
        type: "cron",
        schedule: "0 0 1 1 *",
        timezone: "America/Chicago"
      },
      timeout: 1800,
      keep_alive: false,
      repos: [{
        url: "rajshah4/openhands-agent-research-lab",
        ref: "main",
        provider: "github"
      }]
    }'
)"

curl -fsS -X POST \
  "${OPENHANDS_HOST%/}/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${payload}" |
  jq '{
    id,
    name,
    trigger,
    timeout,
    keep_alive,
    enabled,
    created_at
  }'
