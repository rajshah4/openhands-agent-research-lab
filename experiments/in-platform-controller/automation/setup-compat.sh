#!/usr/bin/env bash
set -euo pipefail

# Replicated 0.24.0 currently reports automation SDK 1.33.0 while its agent
# server emits the 1.36 event contract, including Event.extended_content.
# Keep this pin beside the experiment rather than modifying platform state.
sdk_version="${OPENHANDS_AUTOMATION_SDK_VERSION:-1.36.0}"

echo "[setup] Creating isolated virtual environment"
uv venv .venv --python '>=3.12' --quiet

echo "[setup] Installing OpenHands SDK compatibility version ${sdk_version}"
uv pip install --quiet \
  "openhands-sdk==${sdk_version}" \
  "openhands-tools==${sdk_version}" \
  "openhands-workspace==${sdk_version}"

echo "[setup] Done"
