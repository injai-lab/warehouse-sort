"""Bundle the pinned local browser libraries; no node/npm or system install required."""
import hashlib,io,json,os,subprocess,tarfile,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1];cache=root/'.cache/live-viewer'
url='https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.25.0.tgz'
blob=urllib.request.urlopen(url,timeout=60).read()
assert hashlib.sha256(blob).hexdigest()=='822e9d5ff45b588f5af388f3ae17a4cd4d0d1b93d04220ee92956e941e7b8d9d','esbuild archive hash mismatch'
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as tar:
 binary=tar.extractfile('package/bin/esbuild').read()
(cache/'esbuild').write_bytes(binary);(cache/'esbuild').chmod(0o700)
entry=(root/'web/live-viewer/viewer.js').read_text().replace('./vendor/','./')
(cache/'entry.js').write_text(entry)
subprocess.run([str(cache/'esbuild'),str(cache/'entry.js'),'--bundle','--minify','--format=iife','--global-name=WarehouseViewer','--target=es2020',f'--alias:three={cache}/three.module.js',f'--outfile={cache}/bundle.js','--legal-comments=linked'],check=True)
(cache/'build-manifest.json').write_text(json.dumps(dict(esbuild_version='0.25.0',source=url,archive_sha256=hashlib.sha256(blob).hexdigest(),bundle_sha256=hashlib.sha256((cache/'bundle.js').read_bytes()).hexdigest()),indent=2)+'\n')
