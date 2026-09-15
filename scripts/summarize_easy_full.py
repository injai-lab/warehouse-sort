"""Export non-sensitive configuration, metrics, checkpoint hashes and a training figure."""
import hashlib
import json
from pathlib import Path
import torch
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
run = root/'il/baselines/diffusion_policy/runs/warehouse_state_dp_easy_full_30k'
training = json.loads((run/'train_summary.json').read_text())
assert training['completed_updates'] == 30000
config = json.loads((run/'effective_config.json').read_text())
assert config['num_demos'] == 200 and config['total_iters'] == 30000
history = [json.loads(line) for line in (run/'eval_history.jsonl').read_text().splitlines()]
final = json.loads((root/'runs/easy-full-final-eval/metrics.json').read_text())
plan = json.loads((root/'experiments/easy-full-run-plan.json').read_text())
assert final['metrics']['n_episodes'] == 20
assert set(final['eval_config']['eval']['seeds']).isdisjoint(plan['demo_seeds'])
models = {}
for tag in ['best_eval_sort_accuracy', 'last']:
    path = run/'checkpoints'/f'{tag}.pt'
    ckpt = torch.load(path, map_location='cpu', weights_only=True)
    assert all(torch.isfinite(v).all() for group in ('agent','ema_agent') for v in ckpt[group].values())
    models[tag] = dict(path=str(path.relative_to(root)), bytes=path.stat().st_size,
                      sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      completed_updates=ckpt['completed_updates'])
assert models['last']['completed_updates'] == 30000
assert final['checkpoint_sha256'] == models['best_eval_sort_accuracy']['sha256']
events = EventAccumulator(str(run)).Reload()
losses = [{'log_iteration': e.step, 'loss': e.value} for e in events.Scalars('losses/total_loss')]
report = dict(training=training, effective_config=config, periodic_evaluations=history,
              checkpoints=models, final_evaluation=final, losses=losses)
(root/'experiments/easy-full-results.json').write_text(json.dumps(report,indent=2)+'\n')
fig, axes = plt.subplots(1,2,figsize=(11,4), constrained_layout=True)
axes[0].plot([r['completed_updates'] for r in history],
             [100*r['metrics']['sort_accuracy'] for r in history], marker='o')
axes[0].set(xlabel='Completed optimizer updates', ylabel='Sort accuracy (%)', ylim=(-3,103),
            title='Internal evaluation: 16 episodes / action chunks')
axes[0].grid(alpha=.25)
axes[1].plot([r['log_iteration'] for r in losses], [r['loss'] for r in losses])
axes[1].set(xlabel='Logged iteration', ylabel='Batch diffusion loss', title='Training loss (sampled batches)')
axes[1].grid(alpha=.25)
fig.suptitle('WarehouseSort easy/state — 200 demonstrations, V100, 30,000 updates')
folder=root/'experiments/figures';folder.mkdir(exist_ok=True)
fig.savefig(folder/'easy-full-training.png',dpi=160)
plt.close(fig)
print(json.dumps({'training':training,'checkpoints':models,'final_metrics':final['metrics']},indent=2))
