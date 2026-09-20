"""Loopback-only live PhysX state viewer. Rendering happens in the browser, never in the policy."""
import argparse
import gzip
from collections import defaultdict, deque
from functools import lru_cache
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import signal
import socket
from pathlib import Path
import random
import secrets
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs
import xml.etree.ElementTree as ET

import numpy as np
import torch
import eval_easy_aligned as aligned
from warehouse_sort.demo_restore import restore_demo70
from warehouse_sort.ready_intervention import ReadyIntervention

START_MODE="demo70"

ROOT=aligned.ROOT
TOKEN=secrets.token_urlsafe(32)
lock=threading.Lock()
state={'status':'loading','step':0,'playing':False}
commands=[]
stopping=threading.Event()
meshes={}
measurements=defaultdict(lambda:deque(maxlen=4096))

def measure(name,started):
    with lock:measurements[name].append((time.perf_counter()-started)*1000)

def profile():
    with lock:
        result={k:dict(count=len(v),mean_ms=float(np.mean(v)),p95_ms=float(np.percentile(v,95)),total_ms=float(sum(v))) for k,v in measurements.items() if v}
        result['state']={k:state.get(k) for k in ('step','mode','action_sha256','obs_sha256','correct')}
    return result



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
        def make_env(mode):
            options=dict(kwargs)
            options['max_episode_steps']=600 if mode=='prepare' else 200
            result=aligned.trainer.make_eval_envs(args.env_id,1 if mode=='prepare' else 4,args.sim_backend,options,dict(obs_horizon=2))
            result.auto_reset=False
            return result
        env=make_env(START_MODE)
        env.auto_reset=False
        agent=aligned.trainer.Agent(env,args).cuda().eval()
        agent.load_state_dict(ckpt['ema_agent'],strict=True)
        assert len(agent.noise_scheduler.timesteps)==100 and args.act_horizon==8
        base=env.unwrapped
        seeds=[100000,100001,100002,100003]
        mode=START_MODE;limit=600 if mode=='prepare' else 45
        expert=None;restoration=None;intervention=None
        if mode=='prepare':
            obs,_=env.reset(seed=[seeds[0]])
            intervention=ReadyIntervention(base,ROOT/'runs/ready-intervention')
        else:obs,expert,restoration=restore_demo70(env)
        control_source='학습 모델 제어' if mode=='prepare' else '시범 행동 재생'
        torch.manual_seed(20260915)
        action_hash=hashlib.sha256();obs_hash=hashlib.sha256()
        step=0;sequence=None;cursor=0;playing=False;action=torch.zeros((base.num_envs,4),device='cuda')
        publish(visuals=visuals,seeds=seeds,checkpoint_sha256=digest,status='ready',protocol='state · EMA · DDPM 100 · action chunk 8 · history 2')

        def snapshot():
            capture_started=time.perf_counter()
            publish(frame_id=state.get("frame_id",0)+1,step=step,playing=playing,timestamp=time.time(),mode=mode,limit=limit,seeds=seeds[:base.num_envs] if mode in ('full','prepare') else [1000]*4,source_step=None if mode in ('full','prepare') else 70+step,
                control_source=control_source,intervention=intervention.info() if intervention else None,
                restoration=None if mode in ('full','prepare') else restoration,
                links={link.name:link.pose.raw_pose.cpu().tolist() for link in base.agent.robot.get_links()},
                parcels=[p.pose.raw_pose.cpu().tolist() for p in base.parcels],
                bins=[p.pose.raw_pose.cpu().tolist() for p in base.bins],
                correct=base._placed_correct.cpu().tolist(),
                grasped=torch.stack([base.agent.is_grasping(p) for p in base.parcels],1).cpu().tolist(),
                tcp=base.agent.tcp_pose.p.cpu().tolist(),action=action.cpu().tolist())
            measure('state_extract',capture_started)
        snapshot()
        while not stopping.is_set():
            with lock:
                pending=list(commands);commands.clear()
            for command in pending:
                if command=='play' and step<limit and not (intervention and (intervention.failure or intervention.phase=='done')): playing=True
                elif command=='pause': playing=False
                elif command=='reset' or command.startswith('mode-'):
                    if command.startswith('mode-'):mode=command[5:]
                    playing=False
                    wanted=1 if mode=='prepare' else 4
                    if base.num_envs!=wanted:
                        env.close();env=make_env(mode);base=env.unwrapped
                        action=torch.zeros((wanted,4),device='cuda')
                    intervention=None
                    if mode in ('full','prepare'):
                        obs,_=env.reset(seed=seeds[:wanted]);limit=600 if mode=='prepare' else 200
                        if mode=='prepare':
                            torch.manual_seed(20260915)
                            intervention=ReadyIntervention(base,ROOT/'runs/ready-intervention')
                    else:
                        obs,expert,restoration=restore_demo70(env)
                        torch.manual_seed(20260915)
                        limit=45 if mode=='demo70' else 200
                    control_source='시범 행동 재생' if mode=='demo70' else '학습 모델 제어'
                    step=0;sequence=None;cursor=0
                    action_hash=hashlib.sha256();obs_hash=hashlib.sha256()
                    with lock:measurements.clear()
                    action.zero_();publish(status='ready')
            if not playing:
                if pending:snapshot()
                stopping.wait(.1);continue
            started=time.perf_counter()
            script_step=bool(intervention and intervention.scripting)
            if script_step:
                control_source='스크립트 제어'
                action=intervention.action(base)
            elif mode=='demo70':
                control_source='시범 행동 재생'
                action=expert[step][None].repeat(4,1)
            else:
                control_source='학습 모델 제어'
                if sequence is None or cursor==8:
                    publish(status='inferring',playing=True,control_source=control_source)
                    torch.cuda.synchronize();inference_started=time.perf_counter()
                    if intervention:intervention.log('policy_input',step=step,observation_history=obs[0].cpu().tolist())
                    sequence=agent.get_action(obs);cursor=0
                    torch.cuda.synchronize();measure('inference_100',inference_started)
                action=sequence[:,cursor];cursor+=1
            if stopping.is_set():break
            torch.cuda.synchronize();physics_started=time.perf_counter()
            obs,_,_,truncated,_=env.step(action);step+=1
            torch.cuda.synchronize();measure('physics_step',physics_started)
            action_hash.update(action.cpu().numpy().tobytes());obs_hash.update(obs.cpu().numpy().tobytes())
            publish(action_sha256=action_hash.hexdigest(),obs_sha256=obs_hash.hexdigest())
            if intervention:
                if script_step:
                    intervention.after_script_step(base,step)
                    if not intervention.scripting:
                        sequence=None;cursor=0
                elif intervention.trigger(base,step,0 if sequence is None else 8-cursor):
                    sequence=None;cursor=0
                intervention.record_step(base,obs,action,step,control_source)
                if intervention.failure or intervention.phase=='done':playing=False
            if step==limit:
                if limit in (200,600):assert truncated.all()
                if intervention:intervention.log('episode_limit',step=step,correct=base._placed_correct.cpu().tolist())
                playing=False
            publish(status='aborted' if intervention and intervention.failure else 'finished' if step==limit or (intervention and intervention.phase=='done') else 'running')
            snapshot()
            measure('iteration_work',started)
            wait_started=time.perf_counter()
            stopping.wait(max(0,.05-(time.perf_counter()-started)))
            measure('pacing_wait',wait_started)
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
        if use_gzip:
            compress_started=time.perf_counter();body=compressed(body)
            if urlsplit(self.path).path=='/state':measure('gzip',compress_started)
        self.send_response(status)
        if use_gzip:self.send_header('Content-Encoding','gzip')
        self.send_header('Vary','Accept-Encoding')
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','private, max-age=86400' if mime=='model/gltf-binary' else 'no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        try:
            write_started=time.perf_counter();self.wfile.write(body);self.wfile.flush()
            if urlsplit(self.path).path=='/state':measure('socket_write',write_started)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/stream':return self.stream()
        if path=='/profile':return self.send(200,json.dumps(profile()).encode(),'application/json')
        if path=='/state':
            serialize_started=time.perf_counter()
            with lock:copy=dict(state)
            copy['sent_at']=time.time()
            body=json.dumps(copy).encode()
            measure('json_serialize',serialize_started)
            return self.send(200,body,'application/json')
        if path in ('/','/index.html'):
            return self.send(200,(ROOT/'web/live-viewer/index.html').read_bytes().replace(b'__CONTROL_TOKEN__',TOKEN.encode()).replace(b'__VIEWER_BUNDLE__',(ROOT/'.cache/live-viewer/bundle.js').read_bytes().replace(b'</script',b'<\\/script')),'text/html; charset=utf-8')
        if path=='/viewer.js':return self.send(200,(ROOT/'web/live-viewer/viewer.js').read_bytes(),'text/javascript')
        assets={f'/vendor/{name}':ROOT/'.cache/live-viewer'/name for name in ('three.module.js','OrbitControls.js','GLTFLoader.js','BufferGeometryUtils.js','LICENSE')}
        if path in assets and assets[path].is_file():return self.send(200,assets[path].read_bytes(),'text/javascript' if path.endswith('.js') else 'text/plain')
        if path in meshes:return self.send(200,meshes[path].read_bytes(),'model/gltf-binary')
        self.send(404,b'Not found','text/plain')
    def stream(self):
        query=parse_qs(urlsplit(self.path).query)
        try:
            index=max(0,min(3,int(query.get('env',['0'])[0])))
            hz=max(1,min(20,int(query.get('hz',['15'])[0])))
            digits=max(3,min(5,int(query.get('precision',['4'])[0])))
        except ValueError:return self.send(400,b'Invalid stream settings','text/plain')
        self.send_response(200)
        self.send_header('Content-Type','text/event-stream')
        self.send_header('Cache-Control','no-cache, no-transform')
        self.send_header('X-Accel-Buffering','no')
        self.send_header('Transfer-Encoding','chunked')
        self.end_headers()
        self.connection.settimeout(2)
        self.connection.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096)
        last=None;last_send=0
        def compact(v):
            if isinstance(v,float):return round(v,digits)
            if isinstance(v,list):return [compact(x) for x in v]
            if isinstance(v,dict):return {k:compact(x) for k,x in v.items()}
            return v
        try:
            while not stopping.is_set():
                with lock:copy=dict(state)
                signature=(copy.get('frame_id'),copy.get('status'),copy.get('playing'))
                if signature!=last or time.monotonic()-last_send>2:
                    started=time.perf_counter()
                    for key in ('visuals','restoration','protocol','checkpoint_sha256','action_sha256','obs_sha256'):copy.pop(key,None)
                    if copy.get('links'):
                        index=min(index,len(copy['correct'])-1)
                        copy['links']={name:[poses[index]] for name,poses in copy['links'].items()}
                        for key in ('parcels','bins'):copy[key]=[[poses[index]] for poses in copy[key]]
                        for key in ('correct','grasped','tcp','action'):copy[key]=[copy[key][index]]
                        copy['render_index']=0
                    timestamp=copy.pop('timestamp',None)
                    copy=compact(copy)
                    copy.update(timestamp=timestamp,sent_at=time.time(),selected_env=index,transport='sse')
                    payload=('data: '+json.dumps(copy,separators=(',',':'))+'\n\n').encode()
                    measure('stream_serialize',started)
                    started=time.perf_counter()
                    self.wfile.write(f'{len(payload):x}\r\n'.encode()+payload+b'\r\n');self.wfile.flush()
                    measure('stream_socket_write',started)
                    last=signature;last_send=time.monotonic()
                stopping.wait(1/hz)
        except (OSError,ConnectionError):pass
        finally:
            self.close_connection=True

    def do_POST(self):
        if urlsplit(self.path).path!='/control' or not secrets.compare_digest(self.headers.get('X-Control-Key',''),TOKEN):
            return self.send(403,b'Forbidden','text/plain')
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<256:raise ValueError()
            command=json.loads(self.rfile.read(size))['command']
            if command not in ('play','pause','reset','mode-full','mode-demo70','mode-model70','mode-prepare'):raise ValueError()
        except (ValueError,KeyError):return self.send(400,b'Bad request','text/plain')
        with lock:
            if len(commands)<16:commands.append(command)
        self.send(200,b'{}','application/json')


def main():
    global START_MODE
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--mode',choices=['demo70','prepare'],default='demo70')
    args=parser.parse_args();START_MODE=args.mode
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
