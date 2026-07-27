#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
supervisor_root="/tmp/research-lab-endurance-controller"
pid_file="${supervisor_root}/controller.pid"
exit_file="${supervisor_root}/controller.exit"
log_file="${supervisor_root}/controller.log"

mkdir -p "${supervisor_root}"

status() {
  if [[ -f "${exit_file}" ]]; then
    exit_code="$(<"${exit_file}")"
    jq -n \
      --arg status "completed" \
      --argjson exit_code "${exit_code}" \
      --arg log_file "${log_file}" \
      '{status: $status, exit_code: $exit_code, log_file: $log_file}'
    return
  fi
  if [[ -f "${pid_file}" ]]; then
    pid="$(<"${pid_file}")"
    if kill -0 "${pid}" 2>/dev/null; then
      jq -n \
        --arg status "running" \
        --argjson pid "${pid}" \
        --arg log_file "${log_file}" \
        '{status: $status, pid: $pid, log_file: $log_file}'
      return
    fi
  fi
  jq -n --arg status "not-started" '{status: $status}'
}

case "${1:-status}" in
  start)
    current="$(status)"
    if [[ "$(jq -r '.status' <<<"${current}")" != "not-started" ]]; then
      printf '%s\n' "${current}"
      exit 0
    fi
    : "${OPENHANDS_API_KEY:?OPENHANDS_API_KEY was not injected}"
    rm -f "${exit_file}" "${log_file}"
    (
      set +e
      cd "${project_root}" || exit 90
      RESEARCH_STATE_BRANCH="experiment/endurance-controller-state" \
      RESEARCH_CAMPAIGN="examples/endurance-live.json" \
      RESEARCH_STATE_ROOT=".campaign-state/endurance-controller" \
      OPENHANDS_API_KEY="${OPENHANDS_API_KEY}" \
        python3 experiments/in-platform-controller/automation/preset_tick.py
      exit_code="$?"
      printf '%s\n' "${exit_code}" >"${exit_file}.tmp"
      mv "${exit_file}.tmp" "${exit_file}"
    ) </dev/null >"${log_file}" 2>&1 &
    printf '%s\n' "$!" >"${pid_file}"
    status
    ;;
  status)
    status
    ;;
  result)
    current="$(status)"
    printf '%s\n' "${current}"
    if [[ "$(jq -r '.status' <<<"${current}")" == "completed" ]]; then
      tail -n 40 "${log_file}"
    fi
    ;;
  *)
    echo "usage: $0 [start|status|result]" >&2
    exit 2
    ;;
esac
