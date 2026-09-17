"""Exercise inline code, compressed responses, and slow-network control responsiveness."""
import json
from playwright.sync_api import sync_playwright
results=[]
with sync_playwright() as p:
 for mode in ('slow-network','no-webgl'):
  args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']
  if mode=='no-webgl':args+=['--disable-webgl']
  browser=p.chromium.launch(headless=True,args=args)
  page=browser.new_page(viewport={'width':1280,'height':850});errors=[];js_requests=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('request',lambda r:js_requests.append(r.url) if '.js' in r.url else None)
  if mode=='slow-network':
   cdp=page.context.new_cdp_session(page);cdp.send('Network.enable')
   cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':250,'downloadThroughput':128000,'uploadThroughput':64000})
  response=page.goto('http://127.0.0.1:8765/',wait_until='domcontentloaded',timeout=60000)
  assert response.headers['content-encoding']=='gzip'
  page.wait_for_function('window.viewerState?.links && window.viewerMode',timeout=60000)
  assert page.locator('#play').is_enabled()
  if mode=='slow-network':
   page.click('#play');page.wait_for_function('window.viewerState.step>=8',timeout=60000)
   page.click('#pause');page.wait_for_function('!window.viewerState.playing',timeout=60000)
   page.wait_for_function('window.viewerMeshesReady',timeout=120000)
   page.screenshot(path='runs/live-viewer-slow-network.png')
   page.click('#reset');page.wait_for_function('window.viewerState.step===0',timeout=60000)
  else:assert page.evaluate('window.viewerMode')=='canvas'
  assert not errors,errors
  assert not js_requests,js_requests
  results.append({'mode':mode,'renderer':page.evaluate('window.viewerMode'),'external_js_requests':len(js_requests),'gzip':True,'errors':errors})
  browser.close()
print(json.dumps(results))
