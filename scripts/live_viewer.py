"""Loopback-only live PhysX state viewer. Rendering happens in the browser, never in the policy."""
import argparse
import gzip
from functools import lru_cache
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import signal
from pathlib import Path
import random
import secrets
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

import numpy as np
import torch
import eval_easy_aligned as aligned
from warehouse_sort.demo_restore import restore_demo70

ROOT=aligned.ROOT
TOKEN=secrets.token_urlsafe(32)
lock=threading.Lock()
state={'status':'loading','step':0,'playing':False}
commands=[]
stopping=threading.Event()
meshes={}


def publish(**values):
    with lock: state.update(values)


@torch.inference_mode()
def simulation():
    env=None
    try:
        from mani_skill.agents.robots.panda.panda import Panda
        urdf=Path(Panda.urdf_path)
        visuals=[]
        for link in ET.parse(urdf).getroot().findall('link'):
            for visual in link.findall('visual'):
                mesh=visual.find('geometry/mesh')
                if mesh is None: continue
                path=(urdf.parent/mesh.attrib['filename']).resolve()
                key=f'mesh{len(meshes)}.glb'
                assert path.suffix=='.glb' and path.is_file()
                meshes['/meshes/'+key]=path
                origin=visual.find('origin')
                visuals.append(dict(link=link.attrib['name'],url='meshes/'+key,
                    xyz=[float(v) for v in (origin.get('xyz','0 0 0') if origin is not None else '0 0 0').split()],
                    rpy=[float(v) for v in (origin.get('rpy','0 0 0') if origin is not None else '0 0 0').split()],
                    scale=[float(v) for v in mesh.get('scale','1 1 1').split()]))
        previous=json.loads((ROOT/'experiments/easy-full-aligned-results.json').read_text())
        checkpoint=ROOT/previous['previous']['config']['checkpoint']
        digest=aligned.sha(checkpoint)
        assert digest==previous['checkpoint_sha256']
        ckpt=torch.load(checkpoint,map_location='cuda',weights_only=False)
        args=SimpleNamespace(**ckpt['args'])
        random.seed(20260915);np.random.seed(20260915);torch.manual_seed(20260915)
        torch.backends.cudnn.deterministic=args.torch_deterministic
        kwargs=dict(previous['protocol']['scene_kwargs'])
        env=aligned.trainer.make_eval_envs(args.env_id,4,args.sim_backend,kwargs,dict(obs_horizon=2))
        env.auto_reset=False
        agent=aligned.trainer.Agent(env,args).cuda().eval()
        agent.load_state_dict(ckpt['ema_agent'],strict=True)
        assert len(agent.noise_scheduler.timesteps)==100 and args.act_horizon==8
        base=env.unwrapped
        seeds=[100000,100001,100002,100003]
        mode='demo70';limit=45
        obs,expert,restoration=restore_demo70(env)
        torch.manual_seed(20260915)
        step=0;sequence=None;cursor=0;playing=False;action=torch.zeros((4,4),device='cuda')
        publish(visuals=visuals,seeds=seeds,checkpoint_sha256=digest,status='ready',protocol='state · EMA · DDPM 100 · action chunk 8 · history 2')

        def snapshot():
            publish(step=step,playing=playing,timestamp=time.time(),mode=mode,limit=limit,seeds=seeds if mode=='full' else [1000]*4,source_step=None if mode=='full' else 70+step,
                restoration=None if mode=='full' else restoration,
                links={link.name:link.pose.raw_pose.cpu().tolist() for link in base.agent.robot.get_links()},
                parcels=[p.pose.raw_pose.cpu().tolist() for p in base.parcels],
                bins=[p.pose.raw_pose.cpu().tolist() for p in base.bins],
                correct=base._placed_correct.cpu().tolist(),
                grasped=torch.stack([base.agent.is_grasping(p) for p in base.parcels],1).cpu().tolist(),
                tcp=base.agent.tcp_pose.p.cpu().tolist(),action=action.cpu().tolist())
        snapshot()
        while not stopping.is_set():
            with lock:
                pending=list(commands);commands.clear()
            for command in pending:
                if command=='play' and step<limit: playing=True
                elif command=='pause': playing=False
                elif command=='reset' or command.startswith('mode-'):
                    if command.startswith('mode-'):mode=command[5:]
                    playing=False
                    if mode=='full':
                        obs,_=env.reset(seed=seeds);limit=200
                    else:
                        obs,expert,restoration=restore_demo70(env)
                        torch.manual_seed(20260915)
                        limit=45 if mode=='demo70' else 200
                    step=0;sequence=None;cursor=0
                    action.zero_();publish(status='ready')
            if not playing:
                if pending:snapshot()
                stopping.wait(.1);continue
            started=time.monotonic()
            if mode=='demo70':
                action=expert[step][None].repeat(4,1)
            else:
                if sequence is None or cursor==8:
                    publish(status='inferring',playing=True)
                    sequence=agent.get_action(obs);cursor=0
                action=sequence[:,cursor];cursor+=1
            if stopping.is_set():break
            obs,_,_,truncated,_=env.step(action);step+=1
            if step==limit:
                if limit==200:assert truncated.all()
                playing=False
            publish(status='finished' if step==limit else 'running')
            snapshot()
            stopping.wait(max(0,.05-(time.monotonic()-started)))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        publish(status='error',error=str(exc),playing=False)
    finally:
        if env is not None:env.close()


@lru_cache(maxsize=32)
def compressed(body):
    return gzip.compress(body,compresslevel=5)


class ViewerServer(ThreadingHTTPServer):
    request_queue_size=128
    daemon_threads=True


class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,*args):pass
    def send(self,status,body,mime):
        use_gzip='gzip' in self.headers.get('Accept-Encoding','') and len(body)>512
        if use_gzip:body=compressed(body)
        self.send_response(status)
        if use_gzip:self.send_header('Content-Encoding','gzip')
        self.send_header('Vary','Accept-Encoding')
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','private, max-age=86400' if mime=='model/gltf-binary' else 'no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/state':
            with lock:body=json.dumps(state).encode()
            return self.send(200,body,'application/json')
        if path in ('/','/index.html'):
            return self.send(200,(ROOT/'web/live-viewer/index.html').read_bytes().replace(b'__CONTROL_TOKEN__',TOKEN.encode()).replace(b'__VIEWER_BUNDLE__',(ROOT/'.cache/live-viewer/bundle.js').read_bytes().replace(b'</script',b'<\\/script')),'text/html; charset=utf-8')
        if path=='/viewer.js':return self.send(200,(ROOT/'web/live-viewer/viewer.js').read_bytes(),'text/javascript')
        assets={f'/vendor/{name}':ROOT/'.cache/live-viewer'/name for name in ('three.module.js','OrbitControls.js','GLTFLoader.js','BufferGeometryUtils.js','LICENSE')}
        if path in assets and assets[path].is_file():return self.send(200,assets[path].read_bytes(),'text/javascript' if path.endswith('.js') else 'text/plain')
        if path in meshes:return self.send(200,meshes[path].read_bytes(),'model/gltf-binary')
        self.send(404,b'Not found','text/plain')
    def do_POST(self):
        if urlsplit(self.path).path!='/control' or not secrets.compare_digest(self.headers.get('X-Control-Key',''),TOKEN):
            return self.send(403,b'Forbidden','text/plain')
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<256:raise ValueError()
            command=json.loads(self.rfile.read(size))['command']
            if command not in ('play','pause','reset','mode-full','mode-demo70','mode-model70'):raise ValueError()
        except (ValueError,KeyError):return self.send(400,b'Bad request','text/plain')
        with lock:
            if len(commands)<16:commands.append(command)
        self.send(200,b'{}','application/json')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not (ROOT/'.cache/live-viewer/bundle.js').is_file():
        raise SystemExit('First run setup_live_viewer_assets.py, then build_live_viewer.py with .venv/bin/python')
    server=ViewerServer(('127.0.0.1',args.port),Handler)
    pidfile=ROOT/'runs/live-viewer.pid'
    pidfile.write_text(str(os.getpid())+'\n')
    def stop_signal(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop_signal)
    signal.signal(signal.SIGINT,stop_signal)
    worker=threading.Thread(target=simulation,name='physx-viewer')
    worker.start()
    print(f'Viewer: http://127.0.0.1:{args.port} (loopback only; forward privately in VS Code). Starts paused.',flush=True)
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        stopping.set();server.server_close();worker.join()
        if pidfile.exists() and pidfile.read_text().strip()==str(os.getpid()):pidfile.unlink()
        print('Viewer stopped; simulator closed.',flush=True)


if __name__=='__main__':main()
