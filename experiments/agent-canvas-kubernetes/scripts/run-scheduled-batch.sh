#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--live" || ! "${2:-}" =~ ^(naive|managed)$ ]]; then
  echo "usage: $0 --live naive|managed" >&2
  exit 2
fi

mode="$2"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
namespace="${AGENT_CANVAS_NAMESPACE:-agent-canvas-research}"
release="${AGENT_CANVAS_RELEASE:-agent-canvas-research}"
campaign="$root/examples/hard-transfer-live.json"
batch_id="scheduled-${mode}-$(date -u +%Y%m%dT%H%M%SZ)"
batch_dir="$root/.lab-canvas-kubernetes/scheduled/$batch_id"
workers_dir="$batch_dir/workers"
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

CANVAS_API_KEY="$(
  kubectl -n "$namespace" exec "$pod" -- \
    cat /home/openhands/.openhands/agent-canvas/api-key.txt
)"
export CANVAS_API_KEY
export PYTHONPATH="$root/src"

task_ids=()
while IFS= read -r task_path; do
  task_ids+=("$(jq -r '.id' "$root/examples/$task_path")")
done < <(jq -r '.task_paths[]' "$campaign")
concurrency="${#task_ids[@]}"
if [[ "$concurrency" -ne 6 ]]; then
  echo "expected exactly 6 campaign tasks, found $concurrency" >&2
  exit 1
fi

printf 'timestamp,cpu,memory,active_conversations,pod_restarts\n' \
  > "$batch_dir/resources.csv"
stop_file="$batch_dir/.sampling-complete"

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
      >> "$batch_dir/resources.csv"
    sleep 1
  done
}

sample_resources &
sampler_pid="$!"

batch_started_epoch="$(date +%s)"
pids=()
for worker_number in $(seq 1 "$concurrency"); do
  worker_id="$(printf '%02d' "$worker_number")"
  worker_dir="$workers_dir/worker-$worker_id"
  workspace_root="/home/openhands/workspace/neurogolf-research-lab/scheduled/$batch_id/worker-$worker_id"
  policy="naive"
  run_command=(python3 -m research_lab.cli run \
    --campaign "$campaign" \
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
    --live)
  if [[ "$mode" == "managed" ]]; then
    policy="managed"
    run_command+=(--task-id "${task_ids[$((worker_number - 1))]}")
    run_command+=(--policy "$policy")
  else
    run_command+=(--policy "$policy")
  fi
  "${run_command[@]}" > "$worker_dir.log" 2>&1 &
  pids+=("$!")
done

batch_status=0
for pid in "${pids[@]}"; do
  wait "$pid" || batch_status=1
done
batch_finished_epoch="$(date +%s)"
touch "$stop_file"
wait "$sampler_pid" || true
rm "$stop_file"

find "$workers_dir" -path '*/attempts/*.json' -type f -print0 \
  | xargs -0 jq -c '{
      id,
      task_id,
      outcome,
      valid: .validation.valid,
      score: .validation.score,
      candidate_hash,
      conversation_id: .conversation.conversation_id,
      cost: (
        .metadata.conversation_snapshot.stats.usage_to_metrics.default.accumulated_cost
        // 0
      )
    }' \
  > "$batch_dir/attempts.jsonl"

jq -s \
  --arg batch_id "$batch_id" \
  --arg mode "$mode" \
  --argjson wall_seconds "$((batch_finished_epoch - batch_started_epoch))" \
  '{
    batch_id: $batch_id,
    mode: $mode,
    agents: length,
    wall_seconds: $wall_seconds,
    completed: ([.[] | select(.outcome == "completed")] | length),
    valid: ([.[] | select(.valid == true)] | length),
    task_coverage: ([.[].task_id] | unique | length),
    duplicate_task_assignments: (length - ([.[].task_id] | unique | length)),
    unique_candidates: ([.[].candidate_hash | select(. != null)] | unique | length),
    total_cost: ([.[].cost] | add // 0),
    task_ids: [.[].task_id],
    conversations: [.[].conversation_id]
  }' "$batch_dir/attempts.jsonl" \
  > "$batch_dir/summary.json"

cat "$batch_dir/summary.json"
echo "Artifacts: $batch_dir"
exit "$batch_status"
