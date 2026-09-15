"""Evaluate the existing best EMA with the trainer's exact Agent and environment stack.

No optimizer or training loop is executed. Explicit reset seeds replace the trainer's
implicit stream so this run uses the previous independent evaluation's 20 seeds.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time
from types import SimpleNamespace

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'il/baselines/diffusion_policy'
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location('warehouse_baseline_state', BASE / 'train.py')
trainer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = trainer
spec.loader.exec_module(trainer)  # __main__ guard prevents all training


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(info, seeds, steps):
    return [dict(seed=seed, steps=steps,
                 sorted=int(info['success_count'][i].item()),
                 all_placed=bool(info['all_placed'][i].item()),
                 mis_sorted=int(info['mis_sort_count'][i].item()))
            for i, seed in enumerate(seeds)]


def aggregate(episodes):
    return dict(n_episodes=len(episodes), correct_parcels=sum(r['sorted'] for r in episodes),
                total_parcels=2 * len(episodes),
                sort_accuracy=sum(r['sorted'] for r in episodes) / (2 * len(episodes)),
                both_correct_episodes=sum(r['sorted'] == 2 for r in episodes),
                all_placed_episodes=sum(r['all_placed'] for r in episodes),
                all_placed_rate=sum(r['all_placed'] for r in episodes) / len(episodes))


@torch.inference_mode()
def main():
    out = ROOT / 'runs/easy-full-aligned-eval'
    out.mkdir(exist_ok=False)  # never overwrite an evaluation
    previous_path = ROOT / 'runs/easy-full-final-eval/metrics.json'
    previous_hash = sha(previous_path)
    previous = json.loads(previous_path.read_text())
    checkpoint = ROOT / previous['config']['checkpoint']
    checkpoint_hash = sha(checkpoint)
    assert checkpoint_hash == previous['checkpoint_sha256']
    seeds = previous['eval_config']['eval']['seeds']
    assert len(seeds) == 20 and len(set(seeds)) == 20
    ckpt = torch.load(checkpoint, map_location='cuda', weights_only=False)
    args = SimpleNamespace(**ckpt['args'])
    assert (args.obs_horizon, args.act_horizon, args.pred_horizon) == (2, 8, 16)
    seed = previous['config']['seed']
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.backends.cudnn.deterministic = args.torch_deterministic
    demo = json.loads((ROOT / 'il/demos/easy/trajectory.state.pd_ee_delta_pos.physx_cuda.json').read_text())
    demo_seeds = {ep['episode_seed'] for ep in demo['episodes']}
    assert not set(seeds) & demo_seeds
    scene = demo['env_info']['env_kwargs']
    kwargs = dict(control_mode=args.control_mode, reward_mode='sparse', obs_mode='state',
                  render_mode=None, render_backend='none', max_episode_steps=200,
                  human_render_camera_configs=dict(shader_pack='default'))
    kwargs.update({k: scene[k] for k in ('num_parcels', 'fixed_poses', 'randomization') if k in scene})
    start = time.monotonic()
    env = trainer.make_eval_envs(args.env_id, 4, args.sim_backend, kwargs,
                                 dict(obs_horizon=args.obs_horizon))
    agent = trainer.Agent(env, args).cuda().eval()
    agent.load_state_dict(ckpt['ema_agent'], strict=True)
    assert len(agent.noise_scheduler.timesteps) == 100
    assert agent.noise_scheduler.timesteps.tolist() == list(range(99, -1, -1))
    episodes199, episodes200 = [], []
    try:
        for offset in range(0, 20, 4):
            batch = seeds[offset:offset + 4]
            obs, _ = env.reset(seed=batch)
            assert obs.shape == (4, 2, 54)
            torch.testing.assert_close(obs[:, 0], obs[:, 1], rtol=0, atol=0)
            steps = calls = 0
            while steps < 200:
                action_seq = agent.get_action(obs)
                calls += 1
                assert action_seq.shape == (4, 8, 4)
                assert torch.isfinite(action_seq).all()
                for action in action_seq.unbind(dim=1):
                    last_obs = obs[:, -1].clone()
                    obs, _, _, truncated, info = env.step(action)
                    steps += 1
                    if not truncated.any():
                        # FrameStack advances every physical step, even within a chunk.
                        torch.testing.assert_close(obs[:, 0], last_obs, rtol=0, atol=0)
                    if steps == 199:
                        episodes199.extend(rows(env.unwrapped.evaluate(), batch, steps))
                    if truncated.any():
                        assert truncated.all() and steps == 200
                        final_info = info['final_info']  # capture BEFORE auto-reset
                        episodes200.extend(rows(final_info, batch, steps))
                        # ManiSkill auto-reset fills both frames with the new initial state.
                        torch.testing.assert_close(obs[:, 0], obs[:, 1], rtol=0, atol=0)
                        break
            assert calls == 25
            print(json.dumps(dict(batch_seeds=batch, denoising_calls=calls,
                                  cumulative=aggregate(episodes200))), flush=True)
    finally:
        env.close()
    assert sha(previous_path) == previous_hash and sha(checkpoint) == checkpoint_hash
    report = dict(checkpoint_sha256=checkpoint_hash, checkpoint_updates=ckpt['completed_updates'],
                  previous_metrics_sha256=previous_hash, previous=previous,
                  protocol=dict(denoising_steps=100, action_chunk=8, obs_horizon=2,
                                pred_horizon=16, num_envs=4, seed=seed, seeds=seeds,
                                reset='Explicit batch seeds; trainer FrameStack reset padding; auto-reset at truncation; discard old chunk',
                                scene_kwargs=kwargs, cudnn_deterministic=args.torch_deterministic),
                  metrics_199=aggregate(episodes199), metrics_200=aggregate(episodes200),
                  episodes_199=episodes199, episodes_200=episodes200,
                  elapsed_seconds=time.monotonic() - start,
                  validations=['strict EMA load', '100 scheduler timesteps', '8-action chunks',
                               'reset duplicates initial observation', 'history advances each step',
                               '200-step truncation and final_info', 'auto-reset clears history',
                               '25 policy calls per episode', 'demo/eval seed disjointness',
                               'previous report and checkpoint hashes unchanged'])
    (out / 'metrics.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('metrics_199', 'metrics_200', 'elapsed_seconds')}, indent=2))


if __name__ == '__main__':
    main()
