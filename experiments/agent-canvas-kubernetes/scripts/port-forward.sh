#!/usr/bin/env bash
set -euo pipefail

if command -v gcloud >/dev/null 2>&1; then
  sdk_root="$(gcloud info --format='value(installation.sdk_root)' 2>/dev/null || true)"
  if [[ -x "$sdk_root/bin/gke-gcloud-auth-plugin" ]]; then
    export PATH="$sdk_root/bin:$PATH"
  fi
fi

NAMESPACE="${AGENT_CANVAS_NAMESPACE:-agent-canvas-research}"
RELEASE="${AGENT_CANVAS_RELEASE:-agent-canvas-research}"

exec kubectl -n "$NAMESPACE" port-forward "service/$RELEASE" 8000:8000
