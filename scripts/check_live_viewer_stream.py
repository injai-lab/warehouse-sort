"""Browser checks for quality, selected-state streams, and transport fallback (no policy run)."""
import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    report={}
    for fallback in (False,True):
        page=browser.new_page(viewport={'width':1280,'height':850})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        if fallback:
            page.route('**/stream?*',lambda route:route.abort())
            page.add_init_script("const old=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type.includes('webgl')?null:old.call(this,type,...args)}")
        page.goto('http://127.0.0.1:8765/',wait_until='domcontentloaded')
        page.wait_for_function('window.viewerState?.links && window.transportPerf.transport === '+json.dumps('poll fallback' if fallback else 'sse'))
        if not fallback:
            page.wait_for_function('window.viewerMeshesReady')
            widths=[]
            for quality in ('low','balanced','high'):
                page.select_option('#quality',quality)
                page.wait_for_timeout(200)
                widths.append(page.locator('#scene canvas').evaluate('(c)=>c.width'))
            assert widths[0]<widths[1]<widths[2],widths
            page.uncheck('#smooth');page.check('#smooth')
            page.select_option('#episode','3')
            page.wait_for_function('window.viewerState.selected_env===3')
            s=page.evaluate('window.viewerState')
            full=page.request.get('http://127.0.0.1:8765/state').json()
            assert s['correct'][0]==full['correct'][3]
            assert max(abs(a-b) for a,b in zip(s['tcp'][0],full['tcp'][3]))<1e-4
            report['render_widths']=widths
        else:
            assert page.evaluate('window.viewerMode')=='canvas'
        report['fallback' if fallback else 'stream']={'transport':page.evaluate('window.transportPerf.transport'),'errors':errors}
        assert not errors,errors
        page.close()
    browser.close()
    print(json.dumps(report,indent=2))
