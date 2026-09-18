import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {GLTFLoader} from './vendor/GLTFLoader.js';
export function createViewer(){
const el=id=>document.getElementById(id), host=el('scene');
const scene=new THREE.Scene();scene.background=new THREE.Color('#162231');
const camera=new THREE.PerspectiveCamera(42,1,.01,30);camera.up.set(0,0,1);camera.position.set(1.1,1.25,1.1);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(-.12,0,.15);controls.update();
scene.add(new THREE.HemisphereLight(0xffffff,0x586779,2.5));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(1,1,3);scene.add(light);
function box(size,color){return new THREE.Mesh(new THREE.BoxGeometry(...size),new THREE.MeshStandardMaterial({color,roughness:.55}));}
const table=box([1.5,1.2,.04],0x8c969e);table.position.set(-.2,0,-.021);scene.add(table);
const parcels=[box([.052,.052,.06],0xe54949),box([.052,.052,.06],0x387fe9)];parcels.forEach(p=>scene.add(p));
function bin(color){const group=new THREE.Group();const floor=box([.22,.26,.008],color);floor.position.z=.004;group.add(floor);for(const y of [-.13,.13]){const m=box([.23,.01,.06],color);m.position.set(0,y,.03);group.add(m);}for(const x of [-.11,.11]){const m=box([.01,.26,.06],color);m.position.set(x,0,.03);group.add(m);}scene.add(group);return group;}
const bins=[bin(0xb02f39),bin(0x285baa)],links=new Map(),loader=new GLTFLoader();let initialized=false,last=null;
function pose(obj,p){obj.position.set(p[0],p[1],p[2]);obj.quaternion.set(p[4],p[5],p[6],p[3]);}
async function initVisuals(visuals){initialized=true;for(const v of visuals){const gltf=await loader.loadAsync('./'+v.url);let root=links.get(v.link);if(!root){root=new THREE.Group();links.set(v.link,root);scene.add(root);}const local=new THREE.Group();local.position.fromArray(v.xyz);local.rotation.set(...v.rpy,'ZYX');local.scale.fromArray(v.scale);local.add(gltf.scene);root.add(local);window.dispatchEvent(new CustomEvent('viewer-load-progress',{detail:links.size+'/'+visuals.length}));}window.viewerMeshesReady=true;}

let pending=null,displayTime=null,targetTime=null,fromTime=null,blendStart=0,targets=[],disposed=false;
let lastStep=-1,lastMode=null,lastSelected=-1,smoothing=true,quality='balanced';
const qualityScale={low:.65,balanced:1,high:1.5};
const maxWidth={low:960,balanced:1280,high:1920};
function resize(){const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;renderer.setPixelRatio(Math.min(qualityScale[quality],maxWidth[quality]/w));renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}
function retarget(s){
 if(!s.links)return;
 const i=s.render_index??Number(el('episode').value),selected=s.selected_env??i;
 const snap=!displayTime||s.step<lastStep||s.mode!==lastMode||selected!==lastSelected||!s.playing;
 const objects=[];
 for(const [name,obj] of links)if(s.links[name])objects.push([obj,s.links[name][i]]);
 parcels.forEach((p,j)=>objects.push([p,s.parcels[j][i]]));bins.forEach((p,j)=>objects.push([p,s.bins[j][i]]));
 targets=objects.map(([obj,p])=>({obj,from:obj.position.clone(),rotation:obj.quaternion.clone(),to:new THREE.Vector3(p[0],p[1],p[2]),toRotation:new THREE.Quaternion(p[4],p[5],p[6],p[3]).normalize()}));
 blendStart=performance.now();fromTime=displayTime??s.timestamp;targetTime=s.timestamp;
 if(snap||!smoothing){for(const t of targets){t.obj.position.copy(t.to);t.obj.quaternion.copy(t.toRotation);}displayTime=targetTime;blendStart-=80;}
 lastStep=s.step;lastMode=s.mode;lastSelected=selected;
}
window.viewerPerf={frames:[],render:[],visibleAge:[],fps:0,submitMs:0,ageMs:0};
let previousDraw=performance.now(),reportStart=previousDraw,frameCount=0,submitSum=0,animation;
const observer=new ResizeObserver(resize);observer.observe(host);resize();
function draw(){
 if(disposed)return;animation=requestAnimationFrame(draw);const t=performance.now();
 if(document.hidden){previousDraw=t;return;}
 if(pending){const s=pending;pending=null;retarget(s);}
 const alpha=smoothing?Math.max(0,Math.min(1,(t-blendStart)/80)):1;
 for(const item of targets){item.obj.position.lerpVectors(item.from,item.to,alpha);item.obj.quaternion.slerpQuaternions(item.rotation,item.toRotation,alpha);}
 if(targetTime)displayTime=fromTime+(targetTime-fromTime)*alpha;
 controls.update();renderer.render(scene,camera);
 const cost=performance.now()-t;frameCount++;submitSum+=cost;
 const perf=window.viewerPerf;perf.frames.push(t-previousDraw);perf.render.push(cost);previousDraw=t;
 if(displayTime){perf.visibleAge.push(Date.now()-displayTime*1000);perf.ageMs=Math.max(0,Date.now()+(window.viewerClockOffset||0)-displayTime*1000);}
 if(perf.frames.length>10000){perf.frames.shift();perf.render.shift();perf.visibleAge.shift();}
 if(t-reportStart>=1000){perf.fps=frameCount*1000/(t-reportStart);perf.submitMs=submitSum/frameCount;frameCount=0;submitSum=0;reportStart=t;}
}
draw();
return {
 apply(s){last=s;pending=s;if(s.visuals&&!initialized)initVisuals(s.visuals).then(()=>{pending=last;}).catch(e=>window.dispatchEvent(new CustomEvent('viewer-render-error',{detail:'로봇 메시 로딩 실패: '+e.message})));},
 setQuality(value){quality=value;resize();},setSmoothing(value){smoothing=value;},
 dispose(){disposed=true;cancelAnimationFrame(animation);observer.disconnect();controls.dispose();renderer.dispose();renderer.domElement.remove();}
};
}
