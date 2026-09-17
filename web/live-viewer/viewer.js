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
function apply(s){if(!s.links)return;const i=Number(el('episode').value);for(const [name,obj] of links){if(s.links[name])pose(obj,s.links[name][i]);}parcels.forEach((p,j)=>pose(p,s.parcels[j][i]));bins.forEach((p,j)=>pose(p,s.bins[j][i]));el('step').textContent=`${s.step} / 200`;el('correct').textContent=s.correct[i].map(x=>x?'성공':'미완료').join(' / ');el('grasp').textContent=s.grasped[i].map(x=>x?'잡음':'없음').join(' / ');el('tcp').textContent=s.tcp[i].map(x=>x.toFixed(3)).join(', ');el('action').textContent=s.action[i].map(x=>x.toFixed(3)).join(', ');}

let meshError=null;
new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(host);
function draw(){requestAnimationFrame(draw);controls.update();renderer.render(scene,camera);}draw();
return {apply(s){last=s;if(s.visuals&&!initialized)initVisuals(s.visuals).catch(e=>{meshError=e;window.dispatchEvent(new CustomEvent('viewer-render-error',{detail:'로봇 메시 로딩 실패: '+e.message}));});apply(s);},dispose(){renderer.dispose();renderer.domElement.remove();}};
}
