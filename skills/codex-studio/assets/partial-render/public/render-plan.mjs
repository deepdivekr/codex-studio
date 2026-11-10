export const FPS=30;
export function canonical(value){if(Array.isArray(value))return value.map(canonical);if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));return value;}
export function normalize(snapshot,layout){
 const result={frames:{},tele:{}};
 for(const [key,e] of Object.entries(snapshot.frames||{})){
  const box=layout.boxes.find(b=>b.key===key);
  if(!box){if(['dt0','dt1','dx','dy','scale'].some(k=>Number(e[k]||0)!==0&&!(k==='scale'&&e[k]===1)))throw Error('장면 경계 변경은 지원하지 않습니다. 영상 상자의 시간을 수정하세요.');continue;}
  const clean={};for(const k of ['dx','dy','scale','dt0','dt1']){const v=Number(e[k]??(k==='scale'?1:0));if(!Number.isFinite(v))throw Error('유효하지 않은 수정값');if(v!==(k==='scale'?1:0))clean[k]=v;}
  if((clean.scale??1)<.3||(clean.scale??1)>2.5||Math.abs(clean.dx||0)>2160||Math.abs(clean.dy||0)>3840)throw Error('위치·크기 범위를 확인하세요.');
  if(box.t0+(clean.dt0||0)<0||box.t1+(clean.dt1||0)>layout.frames.at(-1).t1||box.t0+(clean.dt0||0)>=box.t1+(clean.dt1||0))throw Error('구간 시작·끝을 확인하세요.');
  if(Object.keys(clean).length)result.frames[key]=clean;
 }
 for(const [key,e] of Object.entries(snapshot.tele||{})){
  const line=layout.tele.find(x=>x.beat===key);if(!line)throw Error('알 수 없는 전보');
  if(e.text!=null&&e.text!==line.text){if(typeof e.text!=='string'||e.text.length>240)throw Error('전보는 240자 이내로 입력하세요.');result.tele[key]={text:e.text};}
 }
 return canonical(result);
}
export function changedRanges(before,after,layout){
 const ranges=[];const total=Math.floor(layout.frames.at(-1).t1*FPS);
 for(const group of ['frames','tele'])for(const key of new Set([...Object.keys(before[group]||{}),...Object.keys(after[group]||{})])){
  const a=before[group]?.[key]||{},b=after[group]?.[key]||{};if(JSON.stringify(canonical(a))===JSON.stringify(canonical(b)))continue;
  if(group==='frames'){const f=layout.boxes.find(x=>x.key===key);ranges.push([Math.floor((Math.min(f.t0,f.t0+(a.dt0||0),f.t0+(b.dt0||0))-.1)*FPS),Math.ceil((Math.max(f.t1,f.t1+(a.dt1||0),f.t1+(b.dt1||0))+.1)*FPS)]);}
  else {const i=layout.tele.findIndex(x=>x.beat===key);ranges.push([Math.floor(layout.tele[i].t*FPS),Math.ceil((layout.tele[i+1]?.t??layout.frames.at(-1).t1)*FPS)]);}
 }
 const merged=[];for(let [start,end] of ranges.sort((a,b)=>a[0]-b[0])){start=Math.max(0,start);end=Math.min(total,end);const last=merged.at(-1);if(last&&start<=last.end)last.end=Math.max(last.end,end);else merged.push({start,end});}return merged.flatMap(r=>{const out=[];for(let start=r.start;start<r.end;start+=150)out.push({start,end:Math.min(r.end,start+150)});return out;});
}
export function overlayParts(parts,patches){let out=parts.map(x=>({...x}));for(const p of patches){out=out.flatMap(old=>{if(old.end<=p.start||old.start>=p.end)return[old];const keep=[];if(old.start<p.start)keep.push({...old,end:p.start});if(old.end>p.end)keep.push({...old,start:p.end,offset:old.offset+p.end-old.start});return keep;});out.push(p);out.sort((a,b)=>a.start-b.start);}return out;}
