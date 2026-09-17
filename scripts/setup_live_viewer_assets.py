"""Download a pinned MIT-licensed Three.js bundle into the ignored project cache."""
import hashlib, io, json, tarfile, urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'.cache/live-viewer'
out.mkdir(parents=True,exist_ok=True)
url='https://registry.npmjs.org/three/-/three-0.170.0.tgz'
blob=urllib.request.urlopen(url,timeout=60).read()
assert hashlib.sha256(blob).hexdigest() == '4a608a355dcaba72e0e5383cdc814303f5b6060b43c238cdf6932dceb699238d', 'Three.js archive hash mismatch'
files={'three.module.js':'build/three.module.js','OrbitControls.js':'examples/jsm/controls/OrbitControls.js','GLTFLoader.js':'examples/jsm/loaders/GLTFLoader.js','BufferGeometryUtils.js':'examples/jsm/utils/BufferGeometryUtils.js','LICENSE':'LICENSE'}
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as tar:
 for dst,src in files.items():
  content=tar.extractfile('package/'+src).read()
  if dst=='GLTFLoader.js': content=content.replace(b'../utils/BufferGeometryUtils.js',b'./BufferGeometryUtils.js')
  (out/dst).write_bytes(content)
manifest=dict(version='0.170.0',license='MIT',source=url,archive_sha256=hashlib.sha256(blob).hexdigest(),files={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in files})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
