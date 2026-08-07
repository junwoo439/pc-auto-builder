from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\windows\Documents\pc-auto-builder-main")
TARGET = ROOT / "frontend" / "3d_view.html"

HTML = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PC 3D Safe Viewer</title>
<style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#070b12;color:#eef7ff;font-family:"Malgun Gothic",system-ui,sans-serif}
#stage{position:fixed;inset:0}canvas{display:block;width:100%;height:100%;touch-action:none}
#panel{position:absolute;z-index:5;left:14px;top:14px;width:min(380px,calc(100vw - 28px));max-height:calc(100vh - 28px);overflow:auto;padding:16px;border:1px solid rgba(104,225,255,.28);border-radius:16px;background:rgba(7,12,20,.88);backdrop-filter:blur(12px);box-shadow:0 18px 50px rgba(0,0,0,.35)}
#panel h2{margin:0 0 5px;font-size:17px;color:#7cecff}#panel h3{margin:15px 0 7px;font-size:13px;color:#ffd77a}.muted{margin:0 0 10px;color:#a9bac9;font-size:12px;line-height:1.55}
#badge{display:inline-flex;align-items:center;gap:7px;padding:6px 9px;margin:0 0 10px;border-radius:999px;border:1px solid rgba(124,236,255,.25);background:rgba(124,236,255,.08);font-size:11px;color:#bdf5ff}.dot{width:7px;height:7px;border-radius:50%;background:#59f0a4;box-shadow:0 0 12px #59f0a4}
.legend{display:grid;grid-template-columns:1fr 1fr;gap:5px;font-size:11px;color:#c8d4de}.legend span{display:flex;align-items:center;gap:6px}.sw{width:11px;height:11px;border-radius:3px}
.part,.check{margin:6px 0;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,.045);font-size:11px;line-height:1.45}.part{border-left:3px solid #6de8ff}.ok{border:1px solid rgba(76,226,145,.45);color:#90f5bc}.warn{border:1px solid rgba(255,198,93,.5);color:#ffdd91}.error{border:1px solid rgba(255,92,117,.5);color:#ff9dad}
#hint{position:absolute;right:14px;bottom:14px;z-index:4;padding:8px 10px;border-radius:10px;background:rgba(7,12,20,.75);border:1px solid rgba(255,255,255,.12);font-size:11px;color:#b7c5d1}
@media(max-width:680px){#panel{max-height:44vh;width:calc(100vw - 20px);left:10px;top:10px;padding:12px}#hint{display:none}}
</style>
</head>
<body>
<div id="stage"><canvas id="gl"></canvas></div>
<div id="panel">
  <h2>PC 규격 3D 안전모드</h2>
  <div id="badge"><i class="dot"></i><span id="mode">렌더러 확인 중</span></div>
  <p class="muted">외부 Three.js 없이 실행됩니다. WebGL이 막히면 자동으로 가벼운 2D 아이소메트릭 렌더러로 전환됩니다.</p>
  <div class="legend">
    <span><i class="sw" style="background:#49baff"></i>케이스</span><span><i class="sw" style="background:#56e39f"></i>메인보드</span>
    <span><i class="sw" style="background:#ff6178"></i>그래픽카드</span><span><i class="sw" style="background:#ffd75e"></i>파워</span>
  </div>
  <h3>추천 부품</h3><div id="parts"></div>
  <h3>규격 확인</h3><div id="checks"></div>
</div>
<div id="hint">드래그: 회전 · 휠: 확대/축소</div>
<script>
(()=>{
const canvas=document.getElementById('gl'), modeEl=document.getElementById('mode');
const partsEl=document.getElementById('parts'), checksEl=document.getElementById('checks');
let yaw=-0.7,pitch=0.45,zoom=1,drag=false,lastX=0,lastY=0,model=[];
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const num=(v,f)=>{v=Number(v);return Number.isFinite(v)&&v>0?v:f};
function clear(el){while(el.firstChild)el.removeChild(el.firstChild)}
function addCheck(t,l='ok'){const d=document.createElement('div');d.className='check '+l;d.textContent=t;checksEl.appendChild(d)}
function addParts(full){clear(partsEl);const ps=Array.isArray(full?.parts)?full.parts:[];if(!ps.length){const p=document.createElement('p');p.className='muted';p.textContent='추천 결과를 먼저 생성하세요.';partsEl.appendChild(p);return;}for(const p of ps){const d=document.createElement('div');d.className='part';d.textContent=`[${String(p.category||'부품').toUpperCase()}] ${p.manufacturer||''} ${p.model_name||p.name||'이름 없음'}`.trim();partsEl.appendChild(d)}}
function mapParts(full){const ps=Array.isArray(full?.parts)?full.parts:[];return Object.fromEntries(ps.map(p=>[String(p.category||'').toLowerCase(),p]))}
function boardDims(p,d){const s=p?.specifications||{};if(s.width_mm&&s.height_mm)return{w:num(s.width_mm,244),h:num(s.height_mm,244)};const f=String(s.form_factor||d?.form_factor||'M-ATX').toUpperCase();if(f.includes('E-ATX'))return{w:330,h:305};if(f==='ATX')return{w:305,h:244};if(f.includes('ITX'))return{w:170,h:170};return{w:244,h:244}}
function build(payload){const td=payload?.threeD||payload?.three_d_data||{},full=payload?.full||payload?.fullData||payload||{},p=mapParts(full);clear(checksEl);addParts(full);
 const cs=p.case?.specifications||td.case||{},cw=num(cs.width_mm,218),ch=num(cs.height_mm,473),cd=num(cs.depth_mm,441); model=[];
 model.push({kind:'wire',x:0,y:ch/2,z:0,w:cw,h:ch,d:cd,c:[.29,.73,1,1]});
 const bd=boardDims(p.motherboard,td.motherboard||{});model.push({kind:'solid',x:-cw/2+6,y:Math.min(ch-bd.h/2-25,ch*.58),z:-20,w:10,h:bd.h,d:bd.w,c:[.34,.89,.62,1]});
 const ps=p.psu?.specifications||td.psu||{},pw=num(ps.width_mm,150),ph=num(ps.height_mm,86),pd=num(ps.depth_mm||ps.length_mm,140);model.push({kind:'solid',x:0,y:ph/2+3,z:-cd/2+pd/2+10,w:pw,h:ph,d:pd,c:[1,.84,.37,1]});
 if(p.gpu){const gs=p.gpu.specifications||td.gpu||{},gl=num(gs.length_mm||gs.length,280),gt=num(gs.thickness_mm,45),gh=num(gs.height_mm,120),mx=num(cs.max_gpu_length_mm,cd-20),bad=gl>mx;model.push({kind:'solid',x:18,y:Math.max(ph+gh/2+25,ch*.42),z:-cd/2+gl/2+8,w:gt,h:gh,d:gl,c:bad?[1,.12,.24,1]:[1,.38,.47,1]});addCheck(`그래픽카드 길이 ${gl}mm / 케이스 허용 ${mx}mm`,bad?'error':'ok')}else addCheck('그래픽카드가 없습니다. CPU 내장그래픽 여부를 추천 결과에서 확인하세요.','warn');
 const bf=String(p.motherboard?.specifications?.form_factor||'').toUpperCase(),sup=cs.supported_form_factors||cs.motherboard_form_factors||[];if(p.motherboard&&Array.isArray(sup)&&sup.length){const n=v=>String(v).toUpperCase().replace('MICRO-ATX','M-ATX').replace('MICRO ATX','M-ATX');const ok=sup.map(n).includes(n(bf));addCheck(`메인보드 ${bf||'규격 미상'} / 케이스 지원 ${sup.join(', ')}`,ok?'ok':'error')}
 addCheck(`케이스 외형 ${cw} × ${ch} × ${cd}mm`,'ok'); draw();}

// ---------- Native WebGL renderer ----------
let gl=null,program=null,aPos=null,uMVP=null,uColor=null,bufTri=null,bufLine=null,webglOK=false;
const V=[-1,-1,-1, 1,-1,-1, 1,1,-1,-1,1,-1,-1,-1,1,1,-1,1,1,1,1,-1,1,1];
const T=[0,1,2,0,2,3,4,6,5,4,7,6,0,4,5,0,5,1,1,5,6,1,6,2,2,6,7,2,7,3,3,7,4,3,4,0];
const L=[0,1,1,2,2,3,3,0,4,5,5,6,6,7,7,4,0,4,1,5,2,6,3,7];
function shader(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
function initGL(){try{gl=canvas.getContext('webgl',{antialias:false,alpha:false,powerPreference:'low-power'})||canvas.getContext('experimental-webgl');if(!gl)throw Error('WebGL unavailable');const vs=shader(gl.VERTEX_SHADER,'attribute vec3 p;uniform mat4 m;void main(){gl_Position=m*vec4(p,1.0);}'),fs=shader(gl.FRAGMENT_SHADER,'precision mediump float;uniform vec4 c;void main(){gl_FragColor=c;}');program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));aPos=gl.getAttribLocation(program,'p');uMVP=gl.getUniformLocation(program,'m');uColor=gl.getUniformLocation(program,'c');bufTri=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,bufTri);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(T),gl.STATIC_DRAW);bufLine=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,bufLine);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(L),gl.STATIC_DRAW);const vb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vb);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(V),gl.STATIC_DRAW);gl.enableVertexAttribArray(aPos);gl.vertexAttribPointer(aPos,3,gl.FLOAT,false,0,0);gl.enable(gl.DEPTH_TEST);webglOK=true;modeEl.textContent='저사양 WebGL 렌더러';}catch(e){console.warn('WebGL fallback:',e);webglOK=false;modeEl.textContent='2D 안전모드 (WebGL 미지원)';}}
const I=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
function mul(a,b){const o=new Array(16).fill(0);for(let r=0;r<4;r++)for(let c=0;c<4;c++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o}
function perspective(fov,asp,n,f){const q=1/Math.tan(fov/2),o=new Array(16).fill(0);o[0]=q/asp;o[5]=q;o[10]=(f+n)/(n-f);o[11]=-1;o[14]=2*f*n/(n-f);return o}
function lookAt(e,t,u){let zx=e[0]-t[0],zy=e[1]-t[1],zz=e[2]-t[2],zl=Math.hypot(zx,zy,zz)||1;zx