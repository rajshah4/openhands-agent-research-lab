#!/usr/bin/env bash
set -euo pipefail

: "${OPENHANDS_HOST:?Set OPENHANDS_HOST to the Replicated app URL}"
: "${OPENHANDS_API_KEY:?Set OPENHANDS_API_KEY without storing it in the repository}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
archive="${script_dir}/in-platform-controller.tar.gz"
"${script_dir}/package.sh" "${archive}" >/dev/null

upload_response="$(
  curl -fsS -X POST \
    "${OPENHANDS_HOST%/}/api/automation/v1/uploads?name=research-controller-poller&description=Checkpointed%20multi-agent%20campaign%20controller" \
    -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
    -H "Content-Type: application/gzip" \
    --data-binary "@${archive}"
)"
tarball_path="$(jq -er '.tarball_path' <<<"${upload_response}")"

payload="$(
  jq -n \
    --arg tarball_path "${tarball_path}" \
    '{
      name: "Research Lab - Replicated Polling Controller",
      trigger: {
        type: "cron",
        schedule: "0 0 1 1 *",
        timezone: "America/Chicago"
      },
      tarball_path: $tarball_path,
      entrypoint: "python3 main.py",
      timeout: 1800,
      keep_alive: false
    }'
)"

curl -fsS -X POST \
  "${OPENHANDS_HOST%/}/api/automation/v1" \
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
