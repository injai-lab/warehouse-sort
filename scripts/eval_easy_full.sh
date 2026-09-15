#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
exec scripts/run_v100.sh eval.py difficulty=easy obs_mode=state num_envs=4 seed=20260915 \
  render_backend=none capture_video=false \
  policy=warehouse_sort.il_policy:load_dp \
  checkpoint=il/baselines/diffusion_policy/runs/warehouse_state_dp_easy_full_30k/checkpoints/best_eval_sort_accuracy.pt \
  eval_config=conf/eval/easy_unseen_20.yaml hydra.run.dir=runs/easy-full-final-eval
