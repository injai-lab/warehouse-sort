# WarehouseSort environment inspection

Inspected: 2026-09-15 UTC
Host: pepe-student; account: student (uid 1000)
Competition: https://www.kaggle.com/competitions/marso-hack-berlin-2026-robot-parcel-sorting-challenge
The competition page did not expose its instructions to the browser; dependencies are not yet verified.

## Existing environment (unchanged)
- OS: Ubuntu 24.04.1 LTS; kernel: 6.1.0-35-amd64
- GPUs: 4 x Tesla V100-DGXS-32GB, 32768 MiB each
- GPU memory used: 4 MiB each; free reported by NVML: 32486–32489 MiB each
- GPU utilization: 0%; no running GPU processes reported
- NVIDIA driver: 570.133.20; driver CUDA compatibility: 12.8
- Current Python: /opt/conda/bin/python3, 3.13.12
- Current PyTorch: 2.11.0+cu128, CUDA runtime 12.8; CUDA available=True
- CUDA compiler nvcc: unavailable in PATH and /usr/local/cuda/bin; a cuda-12.8 directory exists, but a full development toolkit is not verified
- Filesystem: ZFS zpool0/legacy; df reports 1.8 TiB total, 1002 GiB used, 773 GiB available
- Account storage quota: unverified; quota and zfs tools and /dev/zfs are unavailable. Filesystem free space is not an account quota.

## Project environment
- Root: /home/student/projects/Robot Parcel Sorting Challenge
- Virtual environment: .venv (Python 3.10.21, existing interpreter reused offline)
- Isolation verified: sys.prefix differs from sys.base_prefix; user site disabled; system packages not inherited
- PyTorch and competition dependencies not installed yet; Python selection is provisional until official requirements are verified
- Folders: data/, checkpoints/, runs/, scripts/
- First training target: state observations, easy demonstrations, baseline Diffusion Policy, saved-checkpoint evaluation in simulator
- No data downloaded and no training/evaluation started during this inspection.

Activation:
```bash
cd '/home/student/projects/Robot Parcel Sorting Challenge'
source .venv/bin/activate
```
