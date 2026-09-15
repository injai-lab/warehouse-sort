"""Small independent CUDA/state/render probes; run from the repository root."""
import argparse
import json
from pathlib import Path
import torch

p = argparse.ArgumentParser()
p.add_argument('mode', choices=['cuda', 'state', 'render'])
p.add_argument('--render-backend', default=None)
args = p.parse_args()
result = {'mode': args.mode, 'torch': torch.__version__, 'cuda_runtime': torch.version.cuda}
assert torch.cuda.is_available()
assert torch.cuda.device_count() == 1, 'Select exactly one GPU with CUDA_VISIBLE_DEVICES'
result['gpu'] = torch.cuda.get_device_name(0)
if args.mode == 'cuda':
    torch.manual_seed(0)
    a = torch.randn(256, 256, device='cuda', requires_grad=True)
    b = torch.randn(256, 256, device='cuda')
    c = a @ b
    torch.testing.assert_close(c.cpu(), a.detach().cpu() @ b.cpu(), rtol=1e-4, atol=1e-4)
    c.square().mean().backward()
    torch.cuda.synchronize()
    assert torch.isfinite(a.grad).all()
    result.update(status='passed', capability=torch.cuda.get_device_capability(0), arch_list=torch.cuda.get_arch_list())
else:
    import gymnasium as gym
    import warehouse_sort
    env = gym.make('WarehouseSort-v1', num_envs=1, obs_mode='state',
                   difficulty='easy', num_parcels=2, fixed_poses=True,
                   control_mode='pd_ee_delta_pos', sim_backend='gpu',
                   render_backend=args.render_backend or ('sapien_cuda' if args.mode == 'render' else 'none'),
                   render_mode='rgb_array' if args.mode == 'render' else None,
                   reward_mode='sparse', max_episode_steps=200)
    try:
        obs, _ = env.reset(seed=0)
        assert tuple(obs.shape) == (1, 54), obs.shape
        assert obs.is_cuda and torch.isfinite(obs).all()
        frames = []
        for _ in range(5):
            obs, reward, terminated, truncated, info = env.step(torch.zeros((1,4), device='cuda'))
            assert torch.isfinite(obs).all()
            if args.mode == 'render':
                frame = env.render()[0].cpu().numpy()
                frames.append(frame)
        result.update(status='passed', observation_shape=list(obs.shape), steps=5,
                      sim_device=str(env.unwrapped.device), reward=reward.cpu().tolist())
        if frames:
            import imageio.v2 as iio
            dest = Path('runs/runtime-smoke/render.mp4')
            dest.parent.mkdir(parents=True, exist_ok=True)
            iio.mimsave(dest, frames, fps=10)
            assert dest.stat().st_size > 0
            result.update(video=str(dest), video_bytes=dest.stat().st_size, frame_shape=list(frames[0].shape))
    finally:
        env.close()
output = Path('runs/runtime-smoke')
output.mkdir(parents=True, exist_ok=True)
(output / f'{args.mode}.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
