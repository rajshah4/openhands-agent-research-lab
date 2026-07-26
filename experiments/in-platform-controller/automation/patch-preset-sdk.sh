#!/usr/bin/env bash
set -euo pipefail

: "${OPENHANDS_HOST:?Set OPENHANDS_HOST to the Replicated app URL}"
: "${OPENHANDS_API_KEY:?Set OPENHANDS_API_KEY without storing it in the repository}"

automation_id="${1:?Usage: patch-preset-sdk.sh AUTOMATION_ID}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

curl -fsS \
  "${OPENHANDS_HOST%/}/api/automation/v1/${automation_id}/tarball" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -o "${work_dir}/preset.tar.gz"
mkdir -p "${work_dir}/preset"
tar -xzf "${work_dir}/preset.tar.gz" -C "${work_dir}/preset"
cp "${script_dir}/setup-compat.sh" "${work_dir}/preset/setup.sh"
chmod 755 "${work_dir}/preset/setup.sh"
tar -czf "${work_dir}/patched.tar.gz" -C "${work_dir}/preset" .

upload_response="$(
  curl -fsS -X POST \
    "${OPENHANDS_HOST%/}/api/automation/v1/uploads?name=research-controller-compatible-preset&description=Preset%20with%20agent-server-compatible%20SDK" \
    -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
    -H "Content-Type: application/gzip" \
    --data-binary "@${work_dir}/patched.tar.gz"
)"
tarball_path="$(jq -er '.tarball_path' <<<"${upload_response}")"

jq -n --arg tarball_path "${tarball_path}" '{tarball_path: $tarball_path}' |
  curl -fsS -X PATCH \
    "${OPENHANDS_HOST%/}/api/automation/v1/${automation_id}" \
    -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
    -H "Content-Type: application/json" \
    -d @- |
  jq '{id,name,tarball_path,setup_script_path,entrypoint,keep_alive,enabled}'
