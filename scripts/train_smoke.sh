#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
exec scripts/run_v100.sh il/train.py method=dp demo_dir=easy \
  flags.total_iters=20 flags.batch_size=16 +flags.num_demos=4 \
  flags.num_eval_envs=1 flags.num_eval_episodes=1 \
  flags.eval_freq=20 flags.save_freq=19 flags.log_freq=1 \
  flags.capture_video=false +flags.render_backend=none flags.exp_name=warehouse_state_dp_smoke "$@"
