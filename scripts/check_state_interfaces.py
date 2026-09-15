"""Validate headless environment wrappers used by the official trainer and evaluator."""
import sys
from pathlib import Path
import torch
from warehouse_sort.utils import compose_cfg, make_env

assert torch.cuda.device_count() == 1
cfg = compose_cfg(['difficulty=easy', 'num_envs=1', 'obs_mode=state',
                   'render_backend=none', 'capture_video=false'])
env, is_rgb = make_env(cfg, 'state', cfg.randomization)
try:
    obs, _ = env.reset(seed=0)
    assert not is_rgb and tuple(obs.shape) == (1, 54)
    obs, *_ = env.step(torch.zeros((1, 4), device='cuda'))
    assert obs.is_cuda and torch.isfinite(obs).all()
    print('Official evaluation environment wrapper: passed')
finally:
    env.close()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'il/baselines/diffusion_policy'))
from diffusion_policy.make_env import make_eval_envs

env = make_eval_envs('WarehouseSort-v1', 1, 'gpu',
                    dict(obs_mode='state', control_mode='pd_ee_delta_pos',
                         reward_mode='sparse', render_backend='none', render_mode=None,
                         max_episode_steps=200), dict(obs_horizon=2))
try:
    obs, _ = env.reset(seed=0)
    assert tuple(obs.shape) == (1, 2, 54), obs.shape
    obs, *_ = env.step(torch.zeros((1, 4), device='cuda'))
    assert obs.is_cuda and torch.isfinite(obs).all()
    print('Official training environment + FrameStack: passed')
finally:
    env.close()
