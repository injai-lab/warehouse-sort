"""One-shot Cartesian preparation using normal pd_ee_delta_pos actions only."""
import json
import time
from pathlib import Path
import h5py
import numpy as np
import torch
from warehouse_sort.demo_restore import DATA


class ReadyIntervention:
    MAX_STEPS = 180  # Simulation-time budget; pauses do not count.
    TOLERANCE = .008
    MAX_DELTA = .012  # metres per command; normalized by the controller's 0.1m scale.

    def __init__(self, base, directory):
        assert base.num_envs == 1
        cfg = base.agent.controller.controllers['arm'].config
        assert cfg.frame == 'root_translation' and cfg.use_delta and not cfg.use_target
        assert cfg.normalize_action and cfg.pos_lower == -.1 and cfg.pos_upper == .1
        assert torch.allclose(base.agent.robot.pose.q, torch.tensor([[1.,0,0,0]],device=base.device))
        with h5py.File(DATA) as f:
            self.target = f['traj_0/obs'][70,18:21].astype(float)
            self.reference_qpos = f['traj_0/obs'][70,:9].astype(float)
        self.control_freq = base.control_freq
        self.phase = 'model_first'
        self.used = False
        self.count = 0
        self.stable = 0
        self.failure = None
        self.first_box = None
        self.previous_latest = None
        self.safe_z = .32
        self.path = Path(directory)/f'ready-{time.time_ns()}.jsonl'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.log('config', target=self.target.tolist(), reference_qpos=self.reference_qpos.tolist(),
                 max_steps=self.MAX_STEPS, tolerance=self.TOLERANCE, max_delta=self.MAX_DELTA)

    def log(self, event, **values):
        with self.path.open('a') as f:
            f.write(json.dumps(dict(event=event,time=time.time(),phase=self.phase,**values))+'\n')

    @property
    def scripting(self):
        return self.phase in ('open','raise','translate','lower')

    def trigger(self, base, step, remaining):
        flags=base._placed_correct[0].cpu().tolist()
        if self.used or not any(flags) or all(flags):
            return False
        self.used=True;self.first_box=flags.index(True)
        self.origin=base.agent.tcp_pose.p[0].cpu().numpy().copy()
        tops=[float(p.pose.p[0,2])+.08 for p in base.parcels]
        self.safe_z=max(.32,float(self.origin[2]),float(self.target[2])+.10,*tops)
        self.phase='open'
        self.log('trigger',step=step,first_box=self.first_box,discarded_actions=remaining,
                 safe_z=self.safe_z,tcp=self.origin.tolist())
        return True

    def action(self, base):
        p=base.agent.tcp_pose.p[0].cpu().numpy()
        target=self.origin.copy()
        if self.phase=='raise':target[2]=self.safe_z
        if self.phase=='translate':target=np.array([*self.target[:2],self.safe_z])
        if self.phase=='lower':target=self.target.copy()
        delta=target-p
        delta*=min(1.,self.MAX_DELTA/max(float(np.linalg.norm(delta)),1e-9))
        result=torch.zeros((1,4),device=base.device)
        result[0,:3]=torch.as_tensor(delta/.1,device=base.device)
        result[0,3]=1.  # normalized gripper upper limit: open to 0.04m.
        self.waypoint=target
        return result

    def after_script_step(self, base, step):
        self.count+=1
        p=base.agent.tcp_pose.p[0].cpu().numpy()
        opened=bool((base.agent.robot.get_qpos()[0,-2:]>.035).all())
        close=float(np.linalg.norm(p-self.waypoint))<self.TOLERANCE
        self.stable=self.stable+1 if close and opened else 0
        if self.stable>=3:
            self.phase={'open':'raise','raise':'translate','translate':'lower','lower':'model_second'}[self.phase]
            self.stable=0
            self.log('phase',step=step,tcp=p.tolist(),script_steps=self.count)
        if self.scripting and self.count>=self.MAX_STEPS:
            self.phase='failed';self.failure=f'준비 위치 도달 제한 {self.MAX_STEPS}스텝(시뮬레이션 {self.MAX_STEPS/self.control_freq:g}초) 초과'
            self.log('timeout',step=step,tcp=p.tolist(),target=self.target.tolist())

    def record_step(self, base, obs, action, step, source):
        # Read-only verification: model history's newest frame must be the real current state.
        torch.testing.assert_close(obs[:,-1],base.get_obs(),rtol=0,atol=2e-5)
        if self.previous_latest is not None:
            torch.testing.assert_close(obs[:,0],self.previous_latest,rtol=0,atol=0)
        self.previous_latest=obs[:,-1].clone()
        self.log('step',step=step,source=source,action=action[0].cpu().tolist(),
                 observation_history=obs[0].cpu().tolist(),tcp=base.agent.tcp_pose.p[0].cpu().tolist(),
                 correct=base._placed_correct[0].cpu().tolist(),
                 parcels=[p.pose.raw_pose[0].cpu().tolist() for p in base.parcels],
                 bins=[b.pose.raw_pose[0].cpu().tolist() for b in base.bins])

    def info(self):
        return dict(phase=self.phase,script_steps=self.count,max_steps=self.MAX_STEPS,target=self.target.tolist(),
                    first_box=self.first_box,failure=self.failure,log=str(self.path))
