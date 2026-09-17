import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1280,'height':850})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8765/')
 page.wait_for_function('window.viewerMeshesReady === true',timeout=60000)
 page.screenshot(path='runs/live-viewer-initial.png')
 page.click('#play');page.wait_for_function('window.viewerState.step >= 12',timeout=60000)
 page.click('#pause');page.wait_for_timeout(1500)
 step=page.evaluate('window.viewerState.step')
 page.wait_for_timeout(1000)
 assert page.evaluate('window.viewerState.step')==step
 page.screenshot(path='runs/live-viewer-moving.png')
 page.select_option('#episode','1')
 page.click('#reset');page.wait_for_function('window.viewerState.step === 0',timeout=30000)
 page.click('#play');page.wait_for_function('window.viewerState.step === 200',timeout=120000)
 assert not page.evaluate('window.viewerState.playing')
 page.screenshot(path='runs/live-viewer-finished.png')
 page.click('#reset');page.wait_for_function('window.viewerState.step === 0',timeout=30000)
 assert not errors,errors
 print(json.dumps({'mesh_load':True,'played_to_step':step,'pause_stable':True,'reset':True,'finished_at_200':True,'js_errors':errors}))
 browser.close()
