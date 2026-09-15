"""Read-only best-policy diagnostic: four representative seeds, 600 steps, no rendering/training."""
import json
import random
import time
from types import SimpleNamespace

import numpy as np
import torch
import eval_easy_aligned as aligned


@torch.inference_mode()
def main():
    root = aligned.ROOT
    out = root / 'runs/second-parcel-diagnostic'
    out.mkdir(exist_ok=False)
    old = root / 'runs/easy-full-aligned-eval/metrics.json'
    previous_hash = aligned.sha(old)
    previous = json.loads(old.read_text())
    checkpoint = root / previous['previous']['config']['checkpoint']
    assert aligned.sha(checkpoint) == previous['checkpoint_sha256']
    ckpt = torch.load(checkpoint, map_location='cuda', weights_only=False)
    args = SimpleNamespace(**ckpt['args'])
    seeds = previous['protocol']['seeds'][:4]
    seed = previous['protocol']['seed']
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.backends.cudnn.deterministic = args.torch_deterministic
    kwargs = dict(previous['protocol']['scene_kwargs'])
    kwargs['max_episode_steps'] = 600
    env = aligned.trainer.make_eval_envs(args.env_id, 4, args.sim_backend, kwargs,
                                         dict(obs_horizon=args.obs_horizon))
    # Retain the terminal physical state for diagnostics; no continuation across resets.
    env.auto_reset = False
    agent = aligned.trainer.Agent(env, args).cuda().eval()
    agent.load_state_dict(ckpt['ema_agent'], strict=True)
    assert len(agent.noise_scheduler.timesteps) == 100
    base = env.unwrapped
    observations, actions, parcel_positions, tcp_positions = [], [], [], []
    grasped, correct, fingers = [], [], []

    def capture(obs):
        observations.append(obs[:, -1].cpu().numpy().copy())
        parcel_positions.append(torch.stack([p.pose.p for p in base.parcels], dim=1).cpu().numpy())
        tcp_positions.append(base.agent.tcp_pose.p.cpu().numpy().copy())
        grasped.append(torch.stack([base.agent.is_grasping(p) for p in base.parcels], dim=1).cpu().numpy())
        correct.append(base._placed_correct.cpu().numpy().copy())
        fingers.append(base.agent.robot.get_qpos()[:, -2:].cpu().numpy().copy())

    started = time.monotonic()
    try:
        obs, _ = env.reset(seed=seeds)
        bins = base._bin_positions().cpu().numpy().copy()
        tags = base.parcel_tags.cpu().numpy().copy()
        capture(obs)
        step = 0
        while step < 600:
            seq = agent.get_action(obs)
            assert seq.shape == (4, 8, 4)
            for action in seq.unbind(1):
                actions.append(action.cpu().numpy().copy())
                obs, _, _, truncated, _ = env.step(action)
                step += 1
                capture(obs)
                if step in (200, 400, 600):
                    print(json.dumps(dict(step=step, correct=correct[-1].tolist())), flush=True)
                assert bool(truncated.any()) == (step == 600)
        assert np.asarray(correct)[200].sum(axis=1).tolist() == [1, 1, 1, 1]
    finally:
        env.close()
    arrays = dict(obs=np.asarray(observations), actions=np.asarray(actions),
                  parcels=np.asarray(parcel_positions), tcp=np.asarray(tcp_positions),
                  grasped=np.asarray(grasped), correct=np.asarray(correct),
                  fingers=np.asarray(fingers), bins=bins, tags=tags)
    np.savez_compressed(out / 'trace.npz', **arrays)
    with (out / 'trace.jsonl').open('w') as f:
        for t in range(601):
            for i, s in enumerate(seeds):
                record = dict(seed=s, step=t, parcel_xyz=arrays['parcels'][t,i].tolist(),
                              parcel_correct=arrays['correct'][t,i].tolist(),
                              grasped=arrays['grasped'][t,i].tolist(),
                              tcp_xyz=arrays['tcp'][t,i].tolist(),
                              finger_qpos=arrays['fingers'][t,i].tolist(),
                              action_leading_to_state=None if t==0 else arrays['actions'][t-1,i].tolist())
                f.write(json.dumps(record)+'\n')
    assert aligned.sha(old) == previous_hash
    assert aligned.sha(checkpoint) == previous['checkpoint_sha256']
    meta = dict(seeds=seeds, random_seed=seed, checkpoint_sha256=previous['checkpoint_sha256'],
                base_evaluation_sha256=previous_hash, horizon=600, base_horizon=200,
                denoising_steps=100, action_chunk=8, obs_horizon=2, num_envs=4,
                auto_reset=False, note='Single uninterrupted episode; snapshots at 200,400,600. Not the official 20-episode score.',
                bins=bins.tolist(), tags=tags.tolist(), elapsed_seconds=time.monotonic()-started)
    (out / 'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')


if __name__ == '__main__':
    main()
