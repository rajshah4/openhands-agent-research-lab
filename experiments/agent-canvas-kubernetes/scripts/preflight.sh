#!/usr/bin/env bash
set -euo pipefail

if command -v gcloud >/dev/null 2>&1; then
  sdk_root="$(gcloud info --format='value(installation.sdk_root)' 2>/dev/null || true)"
  if [[ -x "$sdk_root/bin/gke-gcloud-auth-plugin" ]]; then
    export PATH="$sdk_root/bin:$PATH"
  fi
fi

NAMESPACE="${AGENT_CANVAS_NAMESPACE:-agent-canvas-research}"
CHART="${AGENT_CANVAS_CHART:-$HOME/Code/agent-canvas/helm/agent-canvas}"

command -v kubectl >/dev/null
command -v helm >/dev/null
test -f "$CHART/Chart.yaml"

context="$(kubectl config current-context)"
test -n "$context"
kubectl version --request-timeout=20s >/dev/null

if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  echo "namespace=$NAMESPACE exists"
else
  echo "namespace=$NAMESPACE absent"
fi

echo "context=$context"
echo "chart=$CHART"
echo "can_create_namespace=$(kubectl auth can-i create namespaces)"
echo "storage_class=standard-rwo"
