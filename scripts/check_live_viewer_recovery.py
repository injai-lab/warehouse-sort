import json
from playwright.sync_api import sync_playwright
results=[]
with sync_playwright() as p:
 for mode in ['normal','no-webgl','blocked-module']:
  args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']
  if mode=='no-webgl':args+=['--disable-webgl']
  browser=p.chromium.launch(headless=True,args=args)
  page=browser.new_page(viewport={'width':1280,'height':850});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  if mode=='blocked-module':page.route('**/viewer.js?*',lambda route:route.abort())
  page.goto('http://127.0.0.1:8765/')
  page.wait_for_function('window.viewerState?.links && window.viewerMode',timeout=45000)
  if mode!='no-webgl':page.wait_for_function('window.viewerMeshesReady',timeout=45000)
  else:assert page.evaluate('window.viewerMode')=='canvas'
  assert page.locator('#play').is_enabled()
  assert page.locator('#tcp').inner_text()!='—'
  if mode=='no-webgl':
   page.click('#play');page.wait_for_function('window.viewerState.step>=5',timeout=45000)
   page.click('#pause');page.wait_for_timeout(1200)
   page.screenshot(path='runs/live-viewer-compatibility.png')
   page.click('#reset');page.wait_for_function('window.viewerState.step===0',timeout=15000)
  assert not errors,errors
  results.append({'case':mode,'renderer':page.evaluate('window.viewerMode'),'state_and_controls':True,'errors':errors})
  browser.close()
print(json.dumps(results))
