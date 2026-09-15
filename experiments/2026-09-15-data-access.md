# 2026-09-15 — authenticated data inventory

**Resolved follow-up:** official easy/state data was downloaded and the 20-update
training/save/reload/evaluation smoke completed. See [the final smoke report](2026-09-15-state-easy-smoke.md).
Earlier results below are retained as history.

## Result

Kaggle credentials supplied by the user were validated locally and configured outside the
repository. Credential contents were not printed or committed. Both the supplied file and
the active credential file have mode 600; the active credential directory has mode 700.

Authenticated competition file listing succeeded. Full filename/size inventory:
[DATA_MANIFEST.json](../docs/DATA_MANIFEST.json).

Only these two files are selected for download:

| File | Bytes |
|---|---:|
| easy/trajectory.state.pd_ee_delta_pos.physx_cuda.h5 | 15,260,186 |
| easy/trajectory.state.pd_ee_delta_pos.physx_cuda.json | 52,261 |
| **Total** | **15,312,447 (14.60 MiB)** |

Command that succeeded:

```bash
.venv/bin/python scripts/fetch_easy_state.py
```

## Download blocker

```bash
.venv/bin/python scripts/fetch_easy_state.py --download
```

The first selected file was rejected with HTTP 403 Forbidden. The server JSON response was:

```json
{"code": 403, "message": "You must accept this competition's rules before you'll be able to download files."}
```

The account owner must personally review and accept the rules at:
https://www.kaggle.com/competitions/marso-hack-berlin-2026-robot-parcel-sorting-challenge/rules

No rule acceptance was performed by the agent. No demo files were downloaded.
Short training, checkpoint save/reload and learned-policy evaluation remain blocked on
that download. No long training was started.

Once the user confirms acceptance, resume with the existing selective downloader,
`scripts/train_smoke.sh` and `scripts/eval_smoke.sh`.
The earlier CUDA/state simulation validation remains recorded in
[the setup report](2026-09-15-setup.md).
