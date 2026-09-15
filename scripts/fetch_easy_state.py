"""List competition files; optionally download only the easy/state HDF5+JSON pair."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

COMPETITION = 'marso-hack-berlin-2026-robot-parcel-sorting-challenge'
BASE = 'trajectory.state.pd_ee_delta_pos.physx_cuda'
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--download', action='store_true')
args = p.parse_args()
# Kaggle import performs its own authentication; no secrets are printed or saved here.
from kaggle import api
files = []
token = None
while True:
    response = api.competition_list_files(COMPETITION, page_token=token, page_size=100)
    for f in response.files:
        files.append({'name': f.name, 'bytes': f.total_bytes})
    token = response.next_page_token
    if not token:
        break
selected = [f for f in files if 'easy' in PurePosixPath(f['name']).parts
            and PurePosixPath(f['name']).name in (BASE+'.h5', BASE+'.json')]
manifest = {'competition': COMPETITION, 'files': files, 'selected': selected,
            'selected_bytes': sum(f['bytes'] for f in selected)}
report = ROOT/'runs/data-manifest.json'
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(manifest, indent=2), flush=True)
if not args.download:
    raise SystemExit(0)
if len(selected) != 2 or {PurePosixPath(f['name']).suffix for f in selected} != {'.h5','.json'}:
    raise SystemExit('Expected exactly one easy/state HDF5+JSON pair. Inspect manifest; no download attempted.')
dest = ROOT/'il/demos/easy'
dest.mkdir(parents=True, exist_ok=True)
for f in selected:
    name = PurePosixPath(f['name']).name
    target = dest/name
    if not target.exists() or target.stat().st_size != f['bytes']:
        staging = ROOT/'data/kaggle-downloads'/name
        staging.mkdir(parents=True, exist_ok=True)
        api.competition_download_file(COMPETITION, f['name'], path=str(staging), quiet=False)
        direct = list(staging.rglob(name))
        if len(direct) == 1:
            shutil.copy2(direct[0], target)
        else:
            archives = list(staging.glob('*.zip'))
            if len(archives) != 1:
                raise RuntimeError(f'Unexpected download layout in {staging}')
            with zipfile.ZipFile(archives[0]) as z:
                members = [m for m in z.infolist() if PurePosixPath(m.filename).name == name]
                if len(members) != 1:
                    raise RuntimeError('Expected one matching archive member')
                # Stream only the selected member; never extract arbitrary archive paths.
                with z.open(members[0]) as src, target.open('wb') as out:
                    shutil.copyfileobj(src, out)
    assert target.stat().st_size == f['bytes'], f'Size mismatch: {target}'
    digest = hashlib.sha256()
    with target.open('rb') as src:
        for chunk in iter(lambda: src.read(1024*1024), b''):
            digest.update(chunk)
    f.update(local_path=str(target.relative_to(ROOT)), sha256=digest.hexdigest())
manifest['downloaded'] = True
report.write_text(json.dumps(manifest, indent=2)+'\n')
print('Downloaded and size-checked the easy/state pair only.')
