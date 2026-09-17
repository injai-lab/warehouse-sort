import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {GLTFLoader} from './vendor/GLTFLoader.js';
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
async function initVisuals(visuals){initialized=true;await Promise.all(visuals.map(async v=>{const gltf=await loader.loadAsync('./'+v.url);let root=links.get(v.link);if(!root){root=new THREE.Group();links.set(v.link,root);scene.add(root);}const local=new THREE.Group();local.position.fromArray(v.xyz);local.rotation.set(...v.rpy,'ZYX');local.scale.fromArray(v.scale);local.add(gltf.scene);root.add(local);}));window.viewerMeshesReady=true;}
function apply(s){if(!s.links)return;const i=Number(el('episode').value);for(const [name,obj] of links){if(s.links[name])pose(obj,s.links[name][i]);}parcels.forEach((p,j)=>pose(p,s.parcels[j][i]));bins.forEach((p,j)=>pose(p,s.bins[j][i]));el('step').textContent=`${s.step} / 200`;el('correct').textContent=s.correct[i].map(x=>x?'성공':'미완료').join(' / ');el('grasp').textContent=s.grasped[i].map(x=>x?'잡음':'없음').join(' / ');el('tcp').textContent=s.tcp[i].map(x=>x.toFixed(3)).join(', ');el('action').textContent=s.action[i].map(x=>x.toFixed(3)).join(', ');}
const statuses={loading:'시뮬레이터 준비 중',ready:'준비 완료 · 일시정지',inferring:'행동 예측 중',running:'실시간 실행 중',finished:'200스텝 완료',error:'실행 오류'};
async function poll(){try{const response=await fetch('./state',{cache:'no-store'});if(!response.ok)throw Error(`HTTP ${response.status}`);const s=await response.json();last=s;if(s.visuals&&!initialized)await initVisuals(s.visuals);el('status').textContent=s.playing?(statuses[s.status]||s.status):(s.status==='finished'?statuses.finished:s.status==='loading'?statuses.loading:'일시정지');el('play').disabled=!s.links||s.step>=200;el('error').textContent=s.error||'';apply(s);window.viewerState=s;}catch(e){el('error').textContent='연결 / 화면 오류: '+e.message;}finally{setTimeout(poll,100);}}
for(const command of ['play','pause','reset'])el(command).onclick=async()=>{const r=await fetch('./control',{method:'POST',headers:{'Content-Type':'application/json','X-Control-Key':window.controlKey},body:JSON.stringify({command})});if(!r.ok)el('error').textContent='제어 요청 실패: '+r.status;};
el('episode').onchange=()=>{if(last)apply(last);};
new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(host);
function draw(){requestAnimationFrame(draw);controls.update();renderer.render(scene,camera);}draw();poll();
