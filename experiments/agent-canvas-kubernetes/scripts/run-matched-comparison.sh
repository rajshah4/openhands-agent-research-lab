#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--live" ]]; then
  echo "Refusing model calls without --live" >&2
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
namespace="${AGENT_CANVAS_NAMESPACE:-agent-canvas-research}"
release="${AGENT_CANVAS_RELEASE:-agent-canvas-research}"
campaign="${CANVAS_COMPARISON_CAMPAIGN:-$root/examples/multi-family-live-pilot.json}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
store="${CANVAS_COMPARISON_STORE:-$root/.lab-canvas-kubernetes/matched-$timestamp}"

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

python3 -m research_lab.cli preflight \
  --campaign "$campaign" \
  --worker canvas \
  --base-url http://127.0.0.1:8000 \
  --canvas-remote-workspace \
  --canvas-workspace-root /home/openhands/workspace/neurogolf-research-lab \
  --canvas-launch-lock-at 2

python3 -m research_lab.cli compare \
  --campaign "$campaign" \
  --store "$store" \
  --worker canvas \
  --base-url http://127.0.0.1:8000 \
  --canvas-remote-workspace \
  --canvas-workspace-root /home/openhands/workspace/neurogolf-research-lab \
  --canvas-launch-lock-at 2 \
  --max-iterations 12 \
  --execution-timeout 600 \
  --poll-seconds 2 \
  --live
