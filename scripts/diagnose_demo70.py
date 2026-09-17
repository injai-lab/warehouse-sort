"""Validate demo-state restoration with the remaining expert actions, then compare the frozen EMA."""
import hashlib,json,random,time
from types import SimpleNamespace
import numpy as np
import torch
import eval_easy_aligned as aligned
from warehouse_sort.demo_restore import restore_demo70


@torch.inference_mode()
def main():
 root=aligned.ROOT;out=root/'runs/demo70-diagnostic';out.mkdir(exist_ok=False)
 previous=json.loads((root/'experiments/easy-full-aligned-results.json').read_text())
 checkpoint=root/previous['previous']['config']['checkpoint'];before=aligned.sha(checkpoint)
 assert before==previous['checkpoint_sha256']
 ckpt=torch.load(checkpoint,map_location='cuda',weights_only=False);args=SimpleNamespace(**ckpt['args'])
 random.seed(20260915);np.random.seed(20260915);torch.manual_seed(20260915)
 torch.backends.cudnn.deterministic=args.torch_deterministic
 kwargs=previous['protocol']['scene_kwargs'];env=aligned.trainer.make_eval_envs(args.env_id,4,args.sim_backend,kwargs,dict(obs_horizon=2));env.auto_reset=False
 agent=aligned.trainer.Agent(env,args).cuda().eval();agent.load_state_dict(ckpt['ema_agent'],strict=True)
 base=env.unwrapped;reports={};start=time.monotonic();initial=None
 try:
  for mode in ['demo','model']:
   obs,expert,validation=restore_demo70(env)
   signature=hashlib.sha256(obs.cpu().numpy().tobytes()).hexdigest()
   physical=base.get_state_dict();flat=np.concatenate([v.cpu().numpy().flatten() for group in physical.values() for v in group.values()])
   physical_hash=hashlib.sha256(flat.tobytes()).hexdigest()
   if initial is None:initial=(signature,physical_hash)
   else:assert initial==(signature,physical_hash)
   torch.manual_seed(20260915)
   trace=[];first_grasp=[None]*4;first_lift=[None]*4;second_sort=[None]*4
   def capture(step,action=None):
    grasp=torch.stack([base.agent.is_grasping(p) for p in base.parcels],1).cpu().numpy()
    parcels=torch.stack([p.pose.p for p in base.parcels],1).cpu().numpy();correct=base._placed_correct.cpu().numpy().copy()
    for i in range(4):
     if grasp[i,1] and first_grasp[i] is None:first_grasp[i]=step
     if parcels[i,1,2]>.10 and first_lift[i] is None:first_lift[i]=step
     if correct[i,1] and second_sort[i] is None:second_sort[i]=step
    trace.append(dict(step=step,source_step=70+step,tcp=base.agent.tcp_pose.p.cpu().tolist(),parcels=parcels.tolist(),grasped=grasp.tolist(),correct=correct.tolist(),action=None if action is None else action.cpu().tolist()))
   capture(0);seq=None
   horizon=45 if mode=='demo' else 200
   for step in range(horizon):
    if mode=='demo':action=expert[step][None].repeat(4,1)
    else:
     if step%8==0:seq=agent.get_action(obs)
     action=seq[:,step%8]
    obs,_,_,truncated,_=env.step(action);capture(step+1,action)
    if step+1<horizon:assert not truncated.any()
   final=trace[-1]['correct'];reports[mode]=dict(validation=validation,initial_observation_sha256=signature,initial_physical_sha256=physical_hash,
      continuation_steps=horizon,first_second_grasp=first_grasp,first_second_lift=first_lift,first_second_sort=second_sort,
      correct=final,both_correct_episodes=sum(all(c) for c in final),sort_accuracy=sum(sum(c) for c in final)/8)
   (out/f'{mode}-trace.json').write_text(json.dumps(trace)+'\n')
   print(mode,json.dumps(reports[mode]),flush=True)
   if mode=='demo':assert all(all(c) for c in final),'Restoration replay failed; do not interpret model comparison.'
 finally:env.close()
 assert aligned.sha(checkpoint)==before
 report=dict(checkpoint_sha256=before,num_envs=4,torch_seed=20260915,denoising_steps=100,action_chunk=8,
             results=reports,elapsed_seconds=time.monotonic()-start,note='All four environments start from the SAME traj_0 state, not four new scene seeds; model noise differs across batch.')
 (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
