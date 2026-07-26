#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 --live <concurrency: 1-6>" >&2
}

if [[ "${1:-}" != "--live" || ! "${2:-}" =~ ^[1-6]$ ]]; then
  usage
  exit 2
fi

concurrency="$2"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
namespace="${AGENT_CANVAS_NAMESPACE:-agent-canvas-research}"
release="${AGENT_CANVAS_RELEASE:-agent-canvas-research}"
phase_id="c${concurrency}-$(date -u +%Y%m%dT%H%M%SZ)"
phase_dir="$root/.lab-canvas-kubernetes/load/$phase_id"
workers_dir="$phase_dir/workers"
mkdir -p "$workers_dir"

if command -v gcloud >/dev/null 2>&1; then
  sdk_root="$(gcloud info --format='value(installation.sdk_root)' 2>/dev/null || true)"
  if [[ -x "$sdk_root/bin/gke-gcloud-auth-plugin" ]]; then
    export PATH="$sdk_root/bin:$PATH"
  fi
fi

pod="$(
  kubectl -n "$namespace" get pods \
    -l "app.kubernetes.io/instance=$release" \
    -o jsonpath='{.items[0].metadata.name}'
)"
test -n "$pod"
kubectl -n "$namespace" wait --for=condition=Ready "pod/$pod" --timeout=120s

key_path="/home/openhands/.openhands/agent-canvas/api-key.txt"
CANVAS_API_KEY="$(
  kubectl -n "$namespace" exec "$pod" -- cat "$key_path"
)"
export CANVAS_API_KEY
export PYTHONPATH="$root/src"

python3 -m research_lab.cli preflight \
  --campaign "$root/examples/graph-coloring-campaign.json" \
  --worker canvas \
  --base-url http://127.0.0.1:8000 \
  --canvas-remote-workspace \
  --canvas-workspace-root /home/openhands/workspace/neurogolf-research-lab \
  --canvas-launch-lock-at "$concurrency" \
  > "$phase_dir/preflight.json"

printf 'timestamp,cpu,memory,active_conversations,pod_restarts\n' \
  > "$phase_dir/resources.csv"
stop_file="$phase_dir/.sampling-complete"

sample_resources() {
  while [[ ! -f "$stop_file" ]]; do
    timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    metrics="$(kubectl top pod "$pod" -n "$namespace" --no-headers 2>/dev/null || true)"
    cpu="$(awk '{print $2}' <<<"$metrics")"
    memory="$(awk '{print $3}' <<<"$metrics")"
    restarts="$(
      kubectl -n "$namespace" get pod "$pod" \
        -o jsonpath='{.status.containerStatuses[0].restartCount}' \
        2>/dev/null || true
    )"
    active="$(
      curl -sS http://127.0.0.1:8000/api/conversations/search?limit=100 \
        -H "X-Session-API-Key: $CANVAS_API_KEY" \
        2>/dev/null \
        | jq '[.items[]? | select(.execution_status == "running")] | length' \
        2>/dev/null || true
    )"
    printf '%s,%s,%s,%s,%s\n' \
      "$timestamp" "${cpu:-unavailable}" "${memory:-unavailable}" \
      "${active:-unavailable}" "${restarts:-unavailable}" \
      >> "$phase_dir/resources.csv"
    sleep 1
  done
}

sample_resources &
sampler_pid="$!"

phase_started_epoch="$(date +%s)"
pids=()
for worker_number in $(seq 1 "$concurrency"); do
  worker_id="$(printf '%02d' "$worker_number")"
  worker_dir="$workers_dir/worker-$worker_id"
  workspace_root="/home/openhands/workspace/neurogolf-research-lab/load/$phase_id/worker-$worker_id"
  python3 -m research_lab.cli run \
    --campaign "$root/examples/graph-coloring-campaign.json" \
    --store "$worker_dir" \
    --worker canvas \
    --base-url http://127.0.0.1:8000 \
    --canvas-remote-workspace \
    --canvas-workspace-root "$workspace_root" \
    --canvas-launch-lock-at "$concurrency" \
    --attempts 1 \
    --max-iterations 12 \
    --execution-timeout 600 \
    --poll-seconds 2 \
    --live \
    > "$worker_dir.log" 2>&1 &
  pids+=("$!")
done

phase_status=0
for pid in "${pids[@]}"; do
  wait "$pid" || phase_status=1
done
phase_finished_epoch="$(date +%s)"
touch "$stop_file"
wait "$sampler_pid" || true
rm "$stop_file"

find "$workers_dir" -path '*/attempts/*.json' -type f -print0 \
  | xargs -0 jq -c '{
      id,
      run_id,
      task_id,
      started_at,
      finished_at,
      outcome,
      worker_kind,
      conversation_id: .conversation.conversation_id,
      valid: .validation.valid,
      score: .validation.score,
      candidate_hash,
      cost: (
        .metadata.conversation_snapshot.stats.usage_to_metrics.default.accumulated_cost
        // 0
      ),
      prompt_tokens: (
        .metadata.conversation_snapshot.stats.usage_to_metrics.default
        .accumulated_token_usage.prompt_tokens // 0
      ),
      completion_tokens: (
        .metadata.conversation_snapshot.stats.usage_to_metrics.default
        .accumulated_token_usage.completion_tokens // 0
      )
    }' \
  > "$phase_dir/attempts.jsonl"

jq -s \
  --arg phase_id "$phase_id" \
  --argjson concurrency "$concurrency" \
  --argjson wall_seconds "$((phase_finished_epoch - phase_started_epoch))" \
  '{
    phase_id: $phase_id,
    concurrency: $concurrency,
    wall_seconds: $wall_seconds,
    attempts: length,
    completed: ([.[] | select(.outcome == "completed")] | length),
    valid: ([.[] | select(.valid == true)] | length),
    failed: ([.[] | select(.outcome != "completed")] | length),
    unique_candidates: ([.[].candidate_hash | select(. != null)] | unique | length),
    duplicate_candidates: (
      ([.[].candidate_hash | select(. != null)] | length)
      - ([.[].candidate_hash | select(. != null)] | unique | length)
    ),
    total_cost: ([.[].cost] | add // 0),
    total_prompt_tokens: ([.[].prompt_tokens] | add // 0),
    total_completion_tokens: ([.[].completion_tokens] | add // 0),
    conversations: [.[].conversation_id]
  }' "$phase_dir/attempts.jsonl" \
  > "$phase_dir/summary.json"

cat "$phase_dir/summary.json"
echo "Artifacts: $phase_dir"
exit "$phase_status"
