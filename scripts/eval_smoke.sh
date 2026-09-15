#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
exec scripts/run_v100.sh eval.py difficulty=easy obs_mode=state num_envs=1 \
  render_backend=none capture_video=false \
  policy=warehouse_sort.il_policy:load_dp \
  checkpoint=il/baselines/diffusion_policy/runs/warehouse_state_dp_smoke/checkpoints/19.pt \
  eval_config=conf/eval/smoke.yaml hydra.run.dir=runs/eval-smoke "$@"
