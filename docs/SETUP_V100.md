# V100 / Python 3.10 setup

## Scope

Use only the project `.venv`, retaining system Python/CUDA and prior Git history.
Official source and license status: [UPSTREAM.md](UPSTREAM.md).

## Dependencies

Upstream `pixi.toml` pins Python 3.12 and NumPy 2.4.6; those exact pins are not a Python 3.10 environment.
The project instead resolves `requirements-v100.in` into `requirements-v100.lock` for Python 3.10.
PyTorch 2.7.1 / torchvision 0.22.1 CUDA 12.6 wheels are selected for V100 (compute capability 7.0).
Runtime verification, not just `torch.cuda.is_available()`, is required below.

Sources:

- https://pytorch.org/get-started/previous-versions/
- https://maniskill.readthedocs.io/en/latest/user_guide/getting_started/installation.html
- PyPI release metadata for Python version requirements.

```bash
cd '/home/student/projects/Robot Parcel Sorting Challenge'
uv pip compile --python .venv/bin/python \
  --torch-backend cu126 requirements-v100.in -o requirements-v100.lock
UV_HTTP_TIMEOUT=300 UV_CONCURRENT_DOWNLOADS=4 uv pip install --python .venv/bin/python \
  --torch-backend cu126 -r requirements-v100.lock -e .
scripts/install_runtime_libs.sh
uv pip check --python .venv/bin/python
```

`--torch-backend cu126` directs PyTorch packages to the official CUDA 12.6 wheel index;
other dependencies use PyPI. All resolved package versions are pinned in the lockfile.
The original broad extra-index configuration repeatedly retried CUDA dependency downloads.
A trial `tool.uv.sources` configuration did not resolve torch from a requirements file and was removed.

## Single GPU checks

Check availability with `nvidia-smi` before running. GPU 0 was idle when selected.
`WAREHOUSE_GPU=0` is the default; `scripts/run_v100.sh` sets process-local CUDA visibility,
limits CPU thread pools, disables the user Python site and stores ManiSkill assets under `data/`.
It does not modify shell startup files or system libraries.

```bash
scripts/run_v100.sh scripts/smoke_runtime.py cuda
scripts/run_v100.sh scripts/smoke_runtime.py state
scripts/run_v100.sh scripts/smoke_runtime.py render
```

State probe uses `render_backend=none`; render probe separately requests the Vulkan renderer
and saves a five-frame MP4 locally. Detailed logs/results belong under `runs/` and are ignored.

## Data access

Kaggle account authentication is separate from GitHub authentication.
The user must personally accept any competition terms at:
https://www.kaggle.com/competitions/marso-hack-berlin-2026-robot-parcel-sorting-challenge

Python 3.10 uses Kaggle CLI 1.7.4.5; latest CLI 2.2.4 requires Python >=3.11.
Put a legacy `kaggle.json` at `~/.kaggle/kaggle.json` with mode 600; never commit its contents.
Only request the easy state pair listed by the authenticated API. Do not use upstream's
bulk downloader, which fetches all levels and image data.

## Short training

`scripts/train_smoke.sh` requests 20 optimization iterations, 4 easy demos, batch 16,
one evaluation environment and no training video. It retains the default network/horizons
so the official `warehouse_sort.il_policy:load_dp` can reload the checkpoint.
This is a plumbing check and cannot establish sorting performance.

Status and errors are recorded in experiments/2026-09-15-setup.md.


Prepared commands (execution status is in the experiment report):

```bash
.venv/bin/python scripts/fetch_easy_state.py              # list every file and its byte size
.venv/bin/python scripts/fetch_easy_state.py --download   # only easy/state HDF5 + JSON
scripts/train_smoke.sh
scripts/eval_smoke.sh
```

The short trainer saves `19.pt` after the 20th update (zero-based iteration numbering).
The learning-rate warmup remains the upstream 500 steps; 20 iterations test execution only.
Explicit checkpoint saving avoids reliance on `best_eval_sort_accuracy.pt`, which upstream
only writes after a strict improvement above zero.

### Headless options added locally

- `render_backend` and `capture_video` in the root Hydra config retain defaults `gpu` / `true`.
- `warehouse_sort/utils.py` forwards the renderer choice into `gym.make`.
- `eval.py capture_video=false` skips the otherwise unconditional video rollout.
- The state trainer accepts `--render-backend none` with `--no-capture-video`.
- Smoke scripts set those options and do not change the observation/action/reward definitions,
  network or checkpoint loader.

### Local runtime libraries and cache locations

OpenCV requires libGL and GLib even for this state-only workflow. Run
`scripts/install_runtime_libs.sh`: it downloads exact Ubuntu package versions, checks
`requirements-runtime.sha256`, and uses `dpkg-deb -x` under `.cache/runtime`.
It does not install system packages. `scripts/run_v100.sh` supplies the local library path.

SAPIEN automatically downloads its PhysX GPU library to
`~/.sapien/physx/105.1-physx-5.3.1.patch0/` on first GPU use. This is its built-in
user cache; the package exposes no cache-path environment override in this version.
ManiSkill assets use the project `data/maniskill-assets` directory.

The environment additionally avoids allocating visual materials when `scene.can_render()`
is false. Collisions, RNG draws, observations and scoring definitions are retained.
The GPU-rendered equivalence path could not be exercised on this container.

Credential setup (performed by the user):

```bash
mkdir -p ~/.kaggle
chmod 700 ~/.kaggle
# Place the downloaded legacy kaggle.json in ~/.kaggle without sharing its content in chat.
chmod 600 ~/.kaggle/kaggle.json
KAGGLE_CONFIG_DIR="$HOME/.kaggle" .venv/bin/python scripts/fetch_easy_state.py
```

The Kaggle account must have accepted the competition terms. Authenticated access and
remote file sizes have now been verified (see docs/DATA_MANIFEST.json). The authenticated
download is blocked by missing competition-rule acceptance. No demo data or model has been downloaded/trained.
