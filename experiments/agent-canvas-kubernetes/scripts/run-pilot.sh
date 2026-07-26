#!/usr/bin/env bash
set -euo pipefail

if command -v gcloud >/dev/null 2>&1; then
  sdk_root="$(gcloud info --format='value(installation.sdk_root)' 2>/dev/null || true)"
  if [[ -x "$sdk_root/bin/gke-gcloud-auth-plugin" ]]; then
    export PATH="$sdk_root/bin:$PATH"
  fi
fi

if [[ "${1:-}" != "--live" ]]; then
  echo "Refusing model calls without --live" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NAMESPACE="${AGENT_CANVAS_NAMESPACE:-agent-canvas-research}"
RELEASE="${AGENT_CANVAS_RELEASE:-agent-canvas-research}"

pod="$(
  kubectl -n "$NAMESPACE" get pods \
    -l "app.kubernetes.io/instance=$RELEASE" \
    -o jsonpath='{.items[0].metadata.name}'
)"
test -n "$pod"

key_path="/home/openhands/.openhands/agent-canvas/api-key.txt"
if ! CANVAS_API_KEY="$(
  kubectl -n "$NAMESPACE" exec "$pod" -- sh -c "test -f '$key_path' && cat '$key_path'"
)"; then
  key_path="/home/openhands/.openhands/agent-canvas/session-api-key.txt"
  CANVAS_API_KEY="$(
    kubectl -n "$NAMESPACE" exec "$pod" -- cat "$key_path"
  )"
fi
export CANVAS_API_KEY

cd "$ROOT"
PYTHONPATH=src python3 -m research_lab.cli preflight \
  --campaign examples/graph-coloring-campaign.json \
  --worker canvas \
  --base-url http://127.0.0.1:8000 \
  --canvas-remote-workspace \
  --canvas-workspace-root /home/openhands/workspace/neurogolf-research-lab \
  --canvas-launch-lock-at 2

PYTHONPATH=src python3 -m research_lab.cli run \
  --campaign examples/graph-coloring-campaign.json \
  --store .lab-canvas-kubernetes \
  --worker canvas \
  --base-url http://127.0.0.1:8000 \
  --canvas-remote-workspace \
  --canvas-workspace-root /home/openhands/workspace/neurogolf-research-lab \
  --canvas-launch-lock-at 2 \
  --attempts 1 \
  --max-iterations 12 \
  --execution-timeout 600 \
  --poll-seconds 5 \
  --live
