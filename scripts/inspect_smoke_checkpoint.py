"""Verify saved smoke weights and export a small JSON report (no model tensors)."""
import hashlib
import json
from pathlib import Path
import torch
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

root = Path(__file__).resolve().parents[1]
run = root/'il/baselines/diffusion_policy/runs/warehouse_state_dp_smoke'
first = torch.load(run/'checkpoints/0.pt', map_location='cpu', weights_only=True)
last_path = run/'checkpoints/19.pt'
last = torch.load(last_path, map_location='cpu', weights_only=True)
assert {'agent', 'ema_agent'}.issubset(last), last.keys()
report = {'checkpoint': str(last_path.relative_to(root)), 'bytes': last_path.stat().st_size,
          'sha256': hashlib.sha256(last_path.read_bytes()).hexdigest(), 'weights': {}}
for group in ('agent', 'ema_agent'):
    assert first[group].keys() == last[group].keys()
    assert all(torch.isfinite(v).all() for v in last[group].values())
    changed = sum(not torch.equal(first[group][k], v) for k,v in last[group].items())
    assert changed > 0, f'{group} weights did not change between saved updates'
    report['weights'][group] = {'tensors': len(last[group]), 'changed_since_iteration_0': changed,
                               'all_finite': True}
events = EventAccumulator(str(run)).Reload()
losses = events.Scalars('losses/total_loss')
report['loss'] = {'first': losses[0].value, 'last': losses[-1].value,
                  'logged_steps': [e.step for e in losses]}
output = root/'runs/runtime-smoke/checkpoint-inspection.json'
output.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
