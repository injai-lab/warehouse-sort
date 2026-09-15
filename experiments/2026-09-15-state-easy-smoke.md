# 2026-09-15 — state/easy end-to-end smoke: PASS

## Outcome

Completed selective official-data download → 20 optimizer updates → checkpoint save →
fresh-process reload using the official loader → GPU simulator evaluation.
No long training was started. This supersedes the authentication/data blockers in the
[setup report](2026-09-15-setup.md) and [data-access report](2026-09-15-data-access.md).

| Stage | Result |
|---|---|
| Kaggle easy/state download | PASS: only HDF5 + JSON, 15,312,447 bytes total |
| File integrity | PASS: byte sizes checked against authenticated inventory; SHA256 recorded |
| Dataset | 200 trajectories, state dimension 54, action dimension 4 |
| Training subset | First 4 trajectories; 460 transitions, 456 observation sequences |
| Training | PASS: 20 optimizer updates, batch 16, seed 1 |
| Checkpoint save | PASS: `0.pt` and `19.pt` saved locally |
| Checkpoint integrity | PASS: agent and EMA weights finite; all 148 tensors in each changed since iteration 0 |
| Reload | PASS: separate process, `warehouse_sort.il_policy:load_dp`, EMA weights |
| Simulator evaluation | PASS: easy/state, 1 GPU environment, 2 episodes |
| Sorting performance | 0.0% sort accuracy, 0.00/2 parcels sorted per episode |
| All-placed / mis-sort rates | 0.000 / 0.000 |
| Video | Disabled for this run; prior Vulkan renderer failure remains unresolved |

The first batch loss was **1.1440119743**, the last **1.0388448238**. These are different
mini-batches, not a validation-loss measurement or evidence of convergence.
The upstream 500-step LR warmup is retained, so this 20-step run remains within warmup.
TensorBoard records steps 0–19 and repeats the final loss at step 20; this is **20**, not 21,
optimizer updates.

## Reproduction

Working directory: `/home/student/projects/Robot Parcel Sorting Challenge`.
Training/evaluation code base: project commit `08b7cf7`, imported from official commit
`6048f33217f26ae39009a812f53c81171517f393`; local headless changes are documented in the setup guide.
The new checkpoint-inspection script only reads saved weights and logs.

All commands below completed with exit code 0:

```bash
.venv/bin/python scripts/fetch_easy_state.py --download
WAREHOUSE_GPU=0 scripts/train_smoke.sh
WAREHOUSE_GPU=0 scripts/run_v100.sh scripts/inspect_smoke_checkpoint.py
WAREHOUSE_GPU=0 scripts/eval_smoke.sh
```

`scripts/train_smoke.sh` keeps the default 4.48M-parameter state DP network,
obs_horizon=2, act_horizon=8 and pred_horizon=16. It disables rendering, uses one evaluation
environment, and explicitly saves iteration 19 after the twentieth update.
Its internal evaluations at iteration 0 and after training each completed 200 steps with
sort_accuracy=0 and success_at_end=0.

`scripts/eval_smoke.sh` starts a fresh process with `eval.py`, the official `load_dp`
entrypoint and `conf/eval/smoke.yaml` (environment seeds 5000 and 5001).
The horizon setting is 200; upstream `rollout_metrics` executes `max_steps - 1`, i.e.
199 control steps per episode. The loader uses 16 denoising steps and re-plans every step;
training-time evaluation uses the baseline's action chunks. Those upstream behaviors were
not changed for this test. `deterministic=True` does not remove the loader's random diffusion
sampling, and the upstream evaluation does not seed its PyTorch RNG. Treat this as a smoke
result, not a deterministic benchmark or a performance comparison.

## Local artifacts

- Data: `il/demos/easy/trajectory.state.pd_ee_delta_pos.physx_cuda.{h5,json}`.
- Checkpoint: `il/baselines/diffusion_policy/runs/warehouse_state_dp_smoke/checkpoints/19.pt`.
- Checkpoint size: **35,921,033 bytes**.
- Checkpoint SHA256: `5ffca2c673d65356e46e6c80eb9325c3c1e262021478a21ddfea91871e78d102`.
- Training stdout: `runs/runtime-smoke/train-smoke.log`.
- Reload inspection: `runs/runtime-smoke/checkpoint-inspection.{json,log}`.
- Standalone evaluation stdout: `runs/runtime-smoke/eval-smoke.log`.
- TensorBoard events: `il/baselines/diffusion_policy/runs/warehouse_state_dp_smoke/`.

Only summaries and scripts are tracked. The model, data, detailed logs and credentials are
excluded by `.gitignore`.

Machine-readable summaries: [checkpoint](2026-09-15-checkpoint-summary.json),
[data inventory and checksums](../docs/DATA_MANIFEST.json).

## Environment and remaining limit

- Server: `pepe-student`; only physical GPU 0 was exposed to the child processes.
- GPU: Tesla V100-DGXS-32GB; sampled memory use was 2,766 MiB in training and 1,578 MiB
  in standalone evaluation (samples, not measured peaks). Other GPUs remained at 4 MiB.
- Python 3.10.21; torch 2.7.1+cu126; torchvision 0.22.1+cu126.
- ManiSkill 3.0.1; SAPIEN 3.0.3; diffusers 0.38.0; NumPy 2.2.6.
- Complete pins: `requirements-v100.lock`; local GL/GLib package hashes:
  `requirements-runtime.sha256`; no system driver or Python environment replacement.
- Earlier HTTP 403 was resolved by the user accepting competition rules. Authenticated
  download then succeeded without generating substitute or synthetic demonstrations.
- Video rendering remains unavailable: `vk::createInstanceUnique: ErrorIncompatibleDriver`.
  It does not block this verified headless state training/evaluation workflow.

The next learning experiment should be planned separately; no longer run was launched.
