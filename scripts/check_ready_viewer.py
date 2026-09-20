"""One-episode integration check of the scripted intervention; never trains."""
import json,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

for _ in range(120):
    try:
        state=json.load(urllib.request.urlopen('http://127.0.0.1:8765/state'))
        if state.get('status')=='error':raise RuntimeError(state.get('error'))
        if state.get('links'):break
    except OSError:pass
    time.sleep(.5)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1280,'height':850})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8765/',wait_until='domcontentloaded')
    page.wait_for_function('window.viewerMeshesReady && window.viewerState.mode==="prepare"')
    assert page.locator('#episode option').count()==1
    page.click('#play')
    page.wait_for_function('window.viewerState.control_source==="스크립트 제어" || window.viewerState.status==="error"',timeout=120000)
    assert page.evaluate('window.viewerState.status')!='error'
    page.screenshot(path='runs/ready-intervention/script-control.png')
    page.wait_for_function('window.viewerState.intervention.phase==="model_second" || window.viewerState.intervention.failure || window.viewerState.status==="error"',timeout=60000)
    page.wait_for_function('!window.viewerState.playing',timeout=180000)
    result=page.evaluate('window.viewerState')
    assert result['status']!='error',result.get('error')
    path=Path(result['intervention']['log']);rows=[json.loads(l) for l in path.read_text().splitlines()]
    events=[r for r in rows if r['event'] not in ('step','policy_input')]
    inputs=[r for r in rows if r['event']=='policy_input' and r['phase']=='model_second']
    if inputs:
        prev=next(r for r in rows if r['event']=='step' and r['step']==inputs[0]['step'])
        assert prev['observation_history']==inputs[0]['observation_history']
    report=dict(status=result['status'],step=result['step'],correct=result['correct'],events=events,
                resumed_with_actual_history=bool(inputs),errors=errors,log=str(path))
    Path('runs/ready-intervention/check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    assert not errors,errors
    # Verify original modes can still be selected, without executing more episodes.
    for mode,count in [('full',4),('demo70',4),('model70',4),('prepare',1)]:
        page.select_option('#mode',mode)
        page.wait_for_function('(mode)=>window.viewerState.mode===mode && window.viewerState.step===0 && !window.viewerState.playing',arg=mode,timeout=60000)
        assert page.locator('#episode option').count()==count
    browser.close()
