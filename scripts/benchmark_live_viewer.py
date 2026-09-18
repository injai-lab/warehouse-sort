"""Controlled browser benchmark; software-rendered test browser, not the user's PC."""
import argparse,json,time,urllib.request
from pathlib import Path
import numpy as np
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('label');args=p.parse_args()
for _ in range(90):
 try:
  if json.load(urllib.request.urlopen('http://127.0.0.1:8765/state',timeout=1)).get('links'):break
 except OSError:pass
 time.sleep(.5)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1280,'height':850},device_scale_factor=1.5)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 cdp=page.context.new_cdp_session(page);cdp.send('Network.enable')
 cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':100,'downloadThroughput':256000,'uploadThroughput':128000})
 page.goto('http://127.0.0.1:8765/',wait_until='domcontentloaded',timeout=60000)
 page.wait_for_function('window.viewerMeshesReady',timeout=120000)
 page.select_option('#mode','model70');page.wait_for_function('window.viewerState.mode==="model70" && window.viewerState.step===0',timeout=30000)
 page.evaluate('window.viewerPerf.frames=[];window.viewerPerf.render=[];window.viewerPerf.visibleAge=[];window.networkPerf=[]')
 started=time.monotonic();page.click('#play')
 page.wait_for_function('window.viewerState.step===200 && !window.viewerState.playing',timeout=180000)
 elapsed=time.monotonic()-started
 data=page.evaluate('({render:window.viewerPerf,network:window.networkPerf,state:window.viewerState,transport:window.transportPerf})')
 profile=page.request.get('http://127.0.0.1:8765/profile').json()
 def stat(v):return dict(mean=float(np.mean(v)),p50=float(np.percentile(v,50)),p95=float(np.percentile(v,95)),count=len(v)) if v else {}
 fresh=[];seen=set()
 for r in data['network']:
  if r['step']>0 and r['step'] not in seen:fresh.append(r);seen.add(r['step'])
 unique=len(fresh)
 report=dict(label=args.label,environment='Chromium headless SwiftShader, viewport1280x850 DPR1.5; CDP latency100ms down256000B/s up128000B/s',
   elapsed_seconds=elapsed,render_fps=1000/np.mean(data['render']['frames']),render_submit_ms=stat(data['render']['render']),
   fresh_state_fps=unique/elapsed,fresh_states=unique,
   transport=data.get('transport',{}).get('transport','poll'),
   rtt_ms=stat((data.get('transport') or {}).get('rtt') or [r['rtt_ms'] for r in data['network'] if r.get('rtt_ms') is not None]),
   received_state_age_est_ms=stat([r['age_ms'] for r in data['network'] if r.get('age_ms') is not None]),
   fresh_state_latency_ms=stat([r['actual_age_ms'] for r in fresh]),
   visible_state_age_ms=stat(data['render'].get('visibleAge',[])),
   browser_network_samples=data['network'],server=profile,errors=errors)
 Path(f'runs/viewer-performance/{args.label}.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True)
 page.click('#reset');page.wait_for_function('window.viewerState.step===0',timeout=30000)
 assert not errors,errors
 browser.close()
