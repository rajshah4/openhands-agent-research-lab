#!/usr/bin/env bash
set -euo pipefail

: "${OPENHANDS_HOST:?Set OPENHANDS_HOST to the Replicated app URL}"
: "${OPENHANDS_API_KEY:?Set OPENHANDS_API_KEY without storing it in the repository}"
: "${AUTOMATION_ID:?Set AUTOMATION_ID to the validated polling automation}"

curl -fsS -X PATCH \
  "${OPENHANDS_HOST%/}/api/automation/v1/${AUTOMATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger": {
      "type": "cron",
      "schedule": "0 * * * *",
      "timezone": "America/Chicago"
    },
    "enabled": true
  }' |
  jq '{id,name,trigger,timeout,keep_alive,enabled}'
