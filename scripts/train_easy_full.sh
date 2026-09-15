#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
run_name=warehouse_state_dp_easy_full_30k
if [[ -e "il/baselines/diffusion_policy/runs/$run_name" ]]; then
  echo "Run directory already exists; choose a new run name to preserve artifacts." >&2
  exit 1
fi
exec scripts/run_v100.sh il/train.py method=dp demo_dir=easy \
  flags.total_iters=30000 flags.batch_size=256 +flags.num_demos=200 \
  flags.obs_horizon=2 flags.act_horizon=8 flags.pred_horizon=16 \
  flags.num_eval_envs=8 flags.num_eval_episodes=16 \
  flags.eval_freq=5000 flags.save_freq=10000 flags.log_freq=1000 \
  flags.capture_video=false +flags.render_backend=none \
  flags.exp_name="$run_name"
