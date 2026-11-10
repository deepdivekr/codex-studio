import {env} from 'cloudflare:workers';
import layout from '../../../../public/render-layout.json';
import {normalize,changedRanges,overlayParts} from '../../../../public/render-plan.mjs';
const H={'Cache-Control':'no-store'};
const base={id:'base',snapshot:{frames:{},tele:{}},status:'ready',parts:[{start:0,end:Math.floor(layout.frames.at(-1)!.t1*30),offset:0,url:'/base.mp4'}]};
const key=(id:string)=>'render-revisions:'+id;
async function row(id:string){if(id==='base')return base;const r=await env.DB.prepare('SELECT body FROM records WHERE key=?').bind(key(id)).first();return r?JSON.parse(r.body):null;}
async function handle(req:Request){try{
 const url=new URL(req.url),[id,action,index]=url.pathname.split('/').filter(Boolean).slice(2);
 if(id&&!/^[\w-]{1,80}$/.test(id))return new Response('Invalid id',{status:400});
 const origin=req.headers.get('origin');if(req.method!=='GET'&&origin&&origin!==url.origin)return new Response('Forbidden',{status:403});
 if(req.method==='GET'&&action==='media'){
  if(!/^\d+$/.test(index||''))return new Response('Invalid media',{status:400});
  const obj=await env.BUCKET.get(`renders/${id}/${index}.mp4`,{range:req.headers});if(!obj)return new Response('Not found',{status:404});
  const headers=new Headers({'Content-Type':'video/mp4','Accept-Ranges':'bytes','Cache-Control':'private, max-age=31536000, immutable'});obj.writeHttpMetadata(headers);headers.set('ETag',obj.httpEtag);
  if(obj.range){headers.set('Content-Range',`bytes ${obj.range.offset}-${obj.range.offset+obj.range.length-1}/${obj.size}`);headers.set('Content-Length',String(obj.range.length));}else headers.set('Content-Length',String(obj.size));
  return new Response(obj.body,{status:obj.range?206:200,headers});
 }
 if(req.method==='GET'){
  if(id)return Response.json(await row(id),{headers:H});
  const rows=await env.DB.prepare("SELECT body FROM records WHERE collection='render-revisions' ORDER BY key DESC").all();
  const head=await env.DB.prepare("SELECT body FROM records WHERE key='render-head:current'").first();
  const worker=await env.DB.prepare("SELECT body FROM records WHERE key='render-worker:current'").first();
  return Response.json({head:head?JSON.parse(head.body).id:'base',versions:rows.results.map(r=>JSON.parse(r.body)),worker:worker?JSON.parse(worker.body):null},{headers:H});
 }
 if(req.method==='PUT'&&action==='media'){
  const job=await row(id);if(!job||job.status!=='running'||req.headers.get('X-Render-Lease')!==job.lease)return new Response('Lease expired',{status:409});
  if(!/^\d+$/.test(index||'')||!job.ranges[Number(index)])return new Response('Invalid media',{status:400});
  const chunk=Number(url.searchParams.get('chunk')),count=Number(url.searchParams.get('count'));
  const size=Number(req.headers.get('Content-Length'));if(!size||size>262144||!Number.isInteger(chunk)||!Number.isInteger(count)||count<1||count>128||chunk<0||chunk>=count)return new Response('Invalid chunk',{status:413});
  const prefix=`uploads/${id}/${job.lease}/${index}/${count}/`;
  await env.BUCKET.put(prefix+chunk,req.body);
  if(chunk===count-1){const buffers=[];for(let j=0;j<count;j++){const part=await env.BUCKET.get(prefix+j);if(!part)return new Response('Upload incomplete',{status:409});buffers.push(await part.arrayBuffer());}
   const media=await new Blob(buffers).arrayBuffer();if(new TextDecoder().decode(media.slice(4,8))!=='ftyp')return new Response('Invalid MP4',{status:400});
   await env.BUCKET.put(`renders/${id}/${index}.mp4`,media,{httpMetadata:{contentType:'video/mp4'}});await env.BUCKET.delete(Array.from({length:count},(_,j)=>prefix+j));
  }return Response.json({ok:true});
 }
 const raw=await req.text();if(raw.length>50000)return new Response('Too large',{status:413});const input=JSON.parse(raw||'{}');
 if(id==='heartbeat'){
  const body=JSON.stringify({at:Date.now(),name:'렌더 PC',job:input.job||null});await env.DB.prepare("INSERT INTO records(key,collection,id,body) VALUES('render-worker:current','render-worker','current',?) ON CONFLICT(key) DO UPDATE SET body=excluded.body").bind(body).run();return Response.json({ok:true});
 }
 if(!id&&req.method==='POST'){
  const parent=await row(input.parent||'base');if(!parent)return new Response('Parent missing',{status:409});
  if(parent.status!=='ready')return new Response('이전 렌더가 끝난 뒤 저장하세요.',{status:409});
  const snapshot=normalize(input.snapshot,layout),ranges=changedRanges(parent.snapshot,snapshot,layout);
  if(!ranges.length)return new Response('변경된 구간이 없습니다.',{status:400});
  const job={id:Date.now()+'-'+crypto.randomUUID().slice(0,8),parent:parent.id,base:'base',created:Date.now(),title:String(input.title||'구간 수정').slice(0,100),snapshot,ranges,status:'queued',progress:0,parts:[],error:null};
  const head=await env.DB.prepare("SELECT body FROM records WHERE key='render-head:current'").first();
  if((head?JSON.parse(head.body).id:'base')!==parent.id)return new Response('다른 기기에서 버전이 변경되었습니다. 새로고침하세요.',{status:409});
  const expected=head?.body??null,body=JSON.stringify(job);
  const results=await env.DB.batch([
   env.DB.prepare("INSERT INTO records(key,collection,id,body) SELECT ?, 'render-revisions', ?, ? WHERE COALESCE((SELECT body FROM records WHERE key='render-head:current'),'')=?").bind(key(job.id),job.id,body,expected??''),
   env.DB.prepare("INSERT INTO records(key,collection,id,body) SELECT 'render-head:current','render-head','current',? WHERE EXISTS(SELECT 1 FROM records WHERE key=?) ON CONFLICT(key) DO UPDATE SET body=excluded.body").bind(JSON.stringify({id:job.id}),key(job.id))
  ]);if(!results[0].meta.changes)return new Response('Version conflict',{status:409});return Response.json(job,{status:201,headers:H});
 }
 const job=await row(id);if(!job)return new Response('Not found',{status:404});const old=JSON.stringify(job);
 if(action==='claim'){
  if(job.status!=='queued'&&!(job.status==='running'&&Date.now()-job.updated>120000))return new Response('Already claimed',{status:409});
  job.status='running';job.lease=crypto.randomUUID();job.updated=Date.now();job.error=null;
 }else if(action==='progress'){
  if(job.status!=='running'||input.lease!==job.lease)return new Response('Lease expired',{status:409});job.updated=Date.now();job.progress=Math.max(job.progress,Math.min(99,Number(input.progress)||0));
 }else if(action==='finish'){
  if(job.status!=='running'||input.lease!==job.lease)return new Response('Lease expired',{status:409});
  const parent=await row(job.parent),patches=[];
  for(let i=0;i<job.ranges.length;i++){if(!await env.BUCKET.head(`renders/${id}/${i}.mp4`))return new Response('Media missing',{status:409});patches.push({...job.ranges[i],offset:0,url:`/api/renders/${id}/media/${i}`});}
  job.parts=overlayParts(parent.parts,patches);job.status='ready';job.progress=100;job.finished=Date.now();job.receipt=input.receipt;
 }else if(action==='fail'){
  if(input.lease!==job.lease)return new Response('Lease expired',{status:409});job.status='failed';job.error=String(input.error||'렌더 실패').slice(0,500);
 }else if(action==='retry'){
  if(job.status!=='failed')return new Response('Not failed',{status:409});job.status='queued';job.progress=0;job.error=null;
 }else return new Response('Not found',{status:404});
 const updated=await env.DB.prepare('UPDATE records SET body=? WHERE key=? AND body=?').bind(JSON.stringify(job),key(id),old).run();
 if(!updated.meta.changes)return new Response('Version conflict',{status:409});return Response.json(job,{headers:H});
 }catch(e){return new Response(e.message||'Render request failed',{status:400});}}
export const GET=handle;export const POST=handle;export const PUT=handle;
