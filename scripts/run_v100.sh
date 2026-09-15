#!/usr/bin/env bash
# Process-local settings; no changes to shell startup or system CUDA.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
export CUDA_VISIBLE_DEVICES="${WAREHOUSE_GPU:-0}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-4}"
export MS_ASSET_DIR="$project_root/data/maniskill-assets"
export MS_SKIP_ASSET_DOWNLOAD_PROMPT=1
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$project_root/.cache/runtime/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$project_root/.venv/bin/python" "$@"
