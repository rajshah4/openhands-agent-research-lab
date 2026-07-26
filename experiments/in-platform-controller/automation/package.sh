#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output_path="${1:-${script_dir}/in-platform-controller.tar.gz}"

python3 -m py_compile "${script_dir}/main.py"
tar -czf "${output_path}" -C "${script_dir}" main.py
printf '%s\n' "${output_path}"
