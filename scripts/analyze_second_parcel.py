"""Summarize numeric rollout traces and demonstration second-parcel phases."""
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/second-parcel-diagnostic'


def first(mask):
    indices = np.flatnonzero(mask)
    return int(indices[0]) if len(indices) else None


def demo_audit():
    records, obs_hashes, act_hashes = [], set(), set()
    sample = []
    total_actions = out_actions = 0
    with h5py.File(ROOT / 'il/demos/easy/trajectory.state.pd_ee_delta_pos.physx_cuda.h5') as f:
        for name in sorted(f, key=lambda n:int(n.split('_')[1])):
            g=f[name]; o=g['obs'][:]; a=g['actions'][:]
            obs_hashes.add(hashlib.sha256(o.tobytes()).hexdigest())
            act_hashes.add(hashlib.sha256(a.tobytes()).hexdigest())
            p=np.stack([g[f'env_states/actors/parcel_{j}_env0'][:,:3] for j in range(2)],axis=1)
            bins=np.stack([g[f'env_states/actors/bin_{c}'][:,:3] for c in ('red','blue')],axis=1)
            # Saved state index mapping independently checked against actor ground truth.
            np.testing.assert_allclose(o[:,26:29],p[:,0],atol=1e-6)
            np.testing.assert_allclose(o[:,33:36],p[:,1],atol=1e-6)
            inside=(abs(p[:,:,0]-bins[:,:,0])<.11)&(abs(p[:,:,1]-bins[:,:,1])<.13)&(p[:,:,2]>0)&(p[:,:,2]<.06)
            # Dataset has only aggregate grasp, so release is conservative, not per-parcel contact proof.
            released=o[:,25]==0
            sorted_at=[first(inside[:,j]&released) for j in range(2)]
            after=sorted_at[0]
            dist=np.linalg.norm(o[:,18:21]-p[:,1],axis=1)
            inds=np.arange(len(o))
            lifted=p[:,1,2]>.10
            near=(dist<.06)&(inds>after)
            rec=dict(trajectory=name, first_correct_estimate=sorted_at[0], second_correct_estimate=sorted_at[1],
                     second_near_tcp_under_6cm=first(near), second_grasp_proxy=first(near&(o[:,25]>0)),
                     second_lift_above_10cm=first(lifted), second_final_xyz=p[-1,1].tolist())
            records.append(rec)
            total_actions+=len(a); out_actions+=int((abs(a[:,:3])>1).any(axis=1).sum())
            if name=='traj_0':
                for t in sorted(set([0,after,60,70,75,80,90,95,100,110,115]+[x for x in sorted_at if x is not None])):
                    sample.append(dict(step=t,tcp_xyz=o[t,18:21].tolist(),parcel_xyz=p[t].tolist(),
                                       grasp_any=float(o[t,25]),finger_qpos=o[t,7:9].tolist(),
                                       action_next=None if t==len(a) else a[t].tolist()))
    return dict(n_demos=len(records), unique_observation_arrays=len(obs_hashes), unique_action_arrays=len(act_hashes),
                actions_outside_normalized_arm_bounds=out_actions,total_actions=total_actions,
                phase_ranges={k:[min(r[k] for r in records if r[k] is not None),max(r[k] for r in records if r[k] is not None)]
                              for k in ('first_correct_estimate','second_correct_estimate','second_near_tcp_under_6cm','second_grasp_proxy','second_lift_above_10cm')},
                note='Demo sort times inferred from bin geometry and aggregate grasp=false; per-parcel contact not saved.',
                representative=sample, episodes=records)


def trace_summary():
    d=np.load(OUT/'trace.npz'); meta=json.loads((OUT/'metadata.json').read_text())
    reports=[]
    for i,seed in enumerate(meta['seeds']):
        c=d['correct'][:,i]; p=d['parcels'][:,i]; tcp=d['tcp'][:,i]; g=d['grasped'][:,i]; a=d['actions'][:,i]
        times=[first(c[:,j]) for j in range(2)]
        jfirst=min((j for j in range(2) if times[j] is not None),key=lambda j:times[j])
        second=1-jfirst; t0=times[jfirst]
        close_local=first(a[t0:,3]<-.5)
        close_step=None if close_local is None else t0+close_local
        nearest=t0+int(np.linalg.norm(tcp[t0:]-p[t0:,second],axis=1).argmin())
        samples=[]
        for t in sorted(set([0,t0,t0+8,80,100,120,160,200,300,400,600,nearest]+([] if close_step is None else [close_step]))):
            samples.append(dict(step=t,tcp_xyz=tcp[t].tolist(),parcel_xyz=p[t].tolist(),correct=c[t].tolist(),
                                grasped=g[t].tolist(),fingers=d['fingers'][t,i].tolist(),
                                action_next=None if t==600 else a[t].tolist()))
        phases={}
        for end in (200,400,600):
            sl=slice(t0,end+1); xyz=tcp[sl]-p[sl,second]; distance=np.linalg.norm(xyz,axis=1)
            phases[str(end)]=dict(correct=c[end].tolist(),both_correct=bool(c[end].all()),
                                 min_tcp_second_distance=float(distance.min()),
                                 nearest_step=t0+int(distance.argmin()),
                                 min_tcp_second_xy_distance=float(np.linalg.norm(xyz[:,:2],axis=1).min()),
                                 second_grasp_steps=int(g[sl,second].sum()),
                                 second_max_z=float(p[sl,second,2].max()),
                                 second_max_displacement=float(np.linalg.norm(p[sl,second]-p[0,second],axis=1).max()),
                                 tcp_xyz_min=tcp[sl].min(axis=0).tolist(),tcp_xyz_max=tcp[sl].max(axis=0).tolist(),
                                 mean_gripper_command=float(a[t0:end,3].mean()),
                                 gripper_command_min=float(a[t0:end,3].min()),gripper_command_max=float(a[t0:end,3].max()))
        reports.append(dict(seed=seed,first_parcel=jfirst,second_parcel=second,first_correct_steps=times,
                            first_close_action_after_sort=close_step,
                            closed_command_fraction_after_200=float((a[200:,3]<-.5).mean()),
                            windows=phases,samples=samples))
    return dict(metadata=meta,episodes=reports)


if __name__=='__main__':
    demo=demo_audit()
    if not (OUT/'trace.npz').exists():
        print(json.dumps({k:v for k,v in demo.items() if k not in ('episodes','representative')},indent=2))
    else:
        result=dict(demonstrations=demo,diagnostic=trace_summary())
        (OUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(demo_ranges=demo['phase_ranges'],episodes=[{k:v for k,v in e.items() if k!='samples'} for e in result['diagnostic']['episodes']]),indent=2))
