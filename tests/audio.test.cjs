const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../skills/codex-studio/assets/audio.js'),'utf8');
function setup(fetcher) {
  const events={};const started=[];
  const video={paused:true,seeking:false,currentTime:5,readyState:4,addEventListener:(e,f)=>events[e]=f,removeEventListener(){},async play(){this.paused=false;events.playing?.();},pause(){this.paused=true;events.pause?.();}};
  class Context {
    constructor(){this.currentTime=10;this.state='suspended';this.destination={};}
    async resume(){this.state='running';}async close(){}
    createGain(){return {gain:{value:1,setTargetAtTime(v){this.value=v;}},connect(){}};}
    createBufferSource(){const item={connect(){},disconnect(){},stop(){this.stopped=true;},start(...values){started.push({item,values});}};return item;}
    async decodeAudioData(){return {duration:20};}
  }
  const context={AudioContext:Context,fetch:fetcher||(async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(1)})),AbortController,setInterval:()=>1,clearInterval(){},navigator:{}};
  vm.runInNewContext(source,context);
  const manifest={count:3,duration:60,segment_seconds:20,layers:{voice:['v0','v1','v2'],music:['m0','m1','m2'],effects:['e0','e1','e2']}};
  const mixer=new context.StudioAudioMixer(video,manifest,{voice:100,music:60,effects:60},()=>{});
  return {mixer,video,started,events};
}
test('layers use a common clock, gains and bounded segment windows',async()=>{
  const {mixer,video,started}=setup();await mixer.play();await mixer.load(1);mixer.schedule();
  assert.equal(video.paused,false);assert.equal(started.length,6);
  for(const s of started.slice(0,3))assert.deepEqual(s.values,[10,5,15]);
  for(const s of started.slice(3))assert.deepEqual(s.values,[25,0,20]);
  mixer.setLevel('music',25);assert.equal(mixer.gains.music.gain.value,.25);
  mixer.context.currentTime=27;video.currentTime=22;mixer.tick();await mixer.load(2);
  assert(mixer.cache.size<=3);mixer.pause();assert(started.every(s=>s.item.stopped));
});
test('pause while loading never starts the video later',async()=>{
  let resolve;const promise=new Promise(r=>resolve=r);
  const {mixer,video,started}=setup(async()=>{await promise;return {ok:true,arrayBuffer:async()=>new ArrayBuffer(1)};});
  const pending=mixer.play();mixer.pause();resolve();await pending;
  assert(video.paused);assert.equal(started.length,0);
});
test('buffering pauses sound and resumes from current picture time',async()=>{
  const {mixer,video,started,events}=setup();await mixer.play();events.waiting();assert.equal(mixer.anchor,null);
  video.currentTime=8;mixer.context.currentTime=15;events.playing();
  for(const s of started.slice(-3))assert.deepEqual(s.values,[15,8,12]);
});
