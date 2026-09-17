"""Validate both live continuation modes against recorded diagnostic outcomes."""
import json,time,urllib.request
from playwright.sync_api import sync_playwright
for _ in range(60):
 try:
  if json.load(urllib.request.urlopen('http://127.0.0.1:8765/state',timeout=1)).get('mode')=='demo70':break
 except OSError:pass
 time.sleep(.5)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1280,'height':850});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8765/')
 page.wait_for_function('window.viewerMeshesReady && window.viewerState.mode==="demo70"',timeout=60000)
 initial=page.evaluate('JSON.stringify({tcp:window.viewerState.tcp,parcels:window.viewerState.parcels})')
 results={}
 for mode,limit in [('demo70',45),('model70',200)]:
  page.select_option('#mode',mode)
  page.wait_for_function(f'window.viewerState.mode==="{mode}" && window.viewerState.step===0',timeout=30000)
  assert page.evaluate('JSON.stringify({tcp:window.viewerState.tcp,parcels:window.viewerState.parcels})')==initial
  page.click('#play')
  page.wait_for_function(f'window.viewerState.step==={limit} && !window.viewerState.playing',timeout=120000)
  correct=page.evaluate('window.viewerState.correct');assert correct==[[True,True]]*4,correct
  results[mode]={'final_step':limit,'correct':correct,'counter':page.locator('#step').inner_text()}
  page.screenshot(path=f'runs/demo70-{mode}-viewer.png')
 page.select_option('#mode','demo70');page.wait_for_function('window.viewerState.mode==="demo70" && window.viewerState.step===0',timeout=30000)
 assert not errors,errors
 print(json.dumps({'results':results,'errors':errors,'left_paused_at':'demo70'}))
 browser.close()
