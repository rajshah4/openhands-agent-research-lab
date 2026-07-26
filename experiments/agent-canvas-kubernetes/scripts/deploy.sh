#!/usr/bin/env bash
set -euo pipefail

if command -v gcloud >/dev/null 2>&1; then
  sdk_root="$(gcloud info --format='value(installation.sdk_root)' 2>/dev/null || true)"
  if [[ -x "$sdk_root/bin/gke-gcloud-auth-plugin" ]]; then
    export PATH="$sdk_root/bin:$PATH"
  fi
fi

if [[ "${1:-}" != "--live" ]]; then
  echo "Refusing cluster mutation without --live" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NAMESPACE="${AGENT_CANVAS_NAMESPACE:-agent-canvas-research}"
RELEASE="${AGENT_CANVAS_RELEASE:-agent-canvas-research}"
CHART="${AGENT_CANVAS_CHART:-$HOME/Code/agent-canvas/helm/agent-canvas}"
VALUES="$ROOT/experiments/agent-canvas-kubernetes/values.yaml"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml |
  kubectl apply -f -

helm upgrade --install "$RELEASE" "$CHART" \
  --namespace "$NAMESPACE" \
  --values "$VALUES" \
  --wait \
  --timeout 10m

kubectl -n "$NAMESPACE" rollout status "statefulset/$RELEASE" --timeout=10m
kubectl -n "$NAMESPACE" get statefulset,pod,pvc,service
