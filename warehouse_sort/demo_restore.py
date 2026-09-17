"""Restore an open-gripper demonstration state and its true two-frame observation history."""
from pathlib import Path
import re
import h5py
import numpy as np
import torch
from mani_skill.utils.wrappers import FrameStack

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'il/demos/easy/trajectory.state.pd_ee_delta_pos.physx_cuda.h5'


def restore_demo70(env):
    base=env.unwrapped
    env.reset(seed=[1000]*base.num_envs)
    with h5py.File(DATA) as f:
        g=f['traj_0'];observations=g['obs'][:71];actions=g['actions'][70:]
        source={kind:{name:ds[70] for name,ds in group.items()} for kind,group in g['env_states'].items()}
    assert observations[70,25]==0, 'Restoration is only validated for this ungrasped state.'
    current=base.get_state_dict();restored={};mapping={}
    for kind in ('actors','articulations'):
        restored[kind]={}
        for name,value in current.get(kind,{}).items():
            candidates=[name,re.sub(r'_env\d+$','_env0',name),name+'_env0']
            key=next((n for n in candidates if n in source[kind]),None)
            if key is None:raise KeyError(f'No source state for {kind}/{name}')
            tensor=torch.as_tensor(source[kind][key],device=base.device,dtype=value.dtype)
            restored[kind][name]=tensor[None].repeat(value.shape[0],1)
            mapping[kind+'/'+name]=key
    base.scene._reset_mask[:]=True
    base.set_state_dict(restored)
    # Do not agent.reset(): that would zero the saved joint velocities.
    base.agent.controller.reset()
    for controller in base.agent.controller.controllers.values():
        assert not getattr(controller.config,'use_target',False)
        if hasattr(controller,'set_drive_targets'):
            controller.set_drive_targets(controller.qpos.clone())
    base._elapsed_steps.zero_()  # continuation budget starts here; physical source step remains 70
    # Reconstruct cumulative task flags absent from the saved physical state.
    p=np.stack([observations[:,26:29],observations[:,33:36]],1)
    bins=observations[:,44:50].reshape(-1,2,3)
    released=observations[:,25]==0
    correct=(abs(p[:,:,0]-bins[:,:,0])<.11)&(abs(p[:,:,1]-bins[:,:,1])<.13)&(p[:,:,2]>0)&(p[:,:,2]<.06)&released[:,None]
    flags=np.logical_or.accumulate(correct,axis=0)[70]
    assert flags.tolist()==[True,False]
    base._placed_correct[:]=torch.as_tensor(flags,device=base.device)
    base._placed_other.zero_();base._prev_sorted[:]=1
    base._steps_to_complete[:]=base.max_episode_steps
    measured=base.get_obs()
    expected=torch.as_tensor(observations[70],device=base.device)[None].repeat(base.num_envs,1)
    error=float((measured-expected).abs().max())
    torch.testing.assert_close(measured,expected,rtol=0,atol=2e-5)
    wrapper=env
    while not isinstance(wrapper,FrameStack):
        wrapper=getattr(wrapper,'env',getattr(wrapper,'_env',None))
        if wrapper is None:raise RuntimeError('FrameStack not found')
    history=torch.as_tensor(observations[69:71],device=base.device)[None].repeat(base.num_envs,1,1)
    wrapper.frames.clear()
    for t in range(2):wrapper.frames.append(history[:,t].clone())
    obs=wrapper.observation(None)
    torch.testing.assert_close(obs,history,rtol=0,atol=0)
    return obs,torch.as_tensor(actions,device=base.device),dict(trajectory='traj_0',source_step=70,
        observation_steps=[69,70],remaining_demo_actions=len(actions),observation_max_abs_error=error,
        cumulative_correct=flags.tolist(),mapping=mapping,
        controller='reset targets to restored qpos; preserved saved qvel; use_target=False',
        limitation='Saved state has no solver contact cache; replay continuation validates restoration functionally.')
