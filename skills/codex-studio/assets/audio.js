'use strict';

// Small decoded windows keep mobile memory bounded. All layers share one clock.
class StudioAudioMixer {
  constructor(video, manifest, levels, notify) {
    this.video = video; this.manifest = manifest; this.notify = notify;
    this.levels = {...levels}; this.cache = new Map(); this.sources = [];
    this.scheduled = new Set(); this.wanted = false; this.generation = 0;
    this.context = null; this.gains = {}; this.anchor = null; this.busy = false;
    this.disposed = false; this.listeners = [];
    this.listen('playing', () => { if (this.wanted) this.schedule(); });
    this.listen('pause', () => this.stopAudio());
    for (const event of ['waiting','seeking']) this.listen(event, () => this.stopAudio());
    this.listen('ended', () => this.pause());
    this.timer = setInterval(() => this.tick(), 100);
  }
  listen(event, fn) { this.video.addEventListener(event,fn); this.listeners.push([event,fn]); }
  init() {
    if (this.context) return;
    const Context = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (!Context) throw new Error('이 브라우저에서 음원을 재생할 수 없습니다. Safari 또는 Chrome으로 열어주세요.');
    this.context = new Context();
    for (const field of Object.keys(this.manifest.layers)) {
      const gain = this.context.createGain();
      gain.gain.value = (this.levels[field] ?? 100) / 100;
      gain.connect(this.context.destination); this.gains[field] = gain;
    }
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (_) {}
  }
  setLevel(field, value) {
    this.levels[field] = value;
    if (this.gains[field]) this.gains[field].gain.setTargetAtTime(value/100,this.context.currentTime,.015);
  }
  index() { return Math.min(this.manifest.count-1, Math.floor(this.video.currentTime/this.manifest.segment_seconds)); }
  async load(index) {
    if (index < 0 || index >= this.manifest.count) return;
    if (this.cache.has(index)) return this.cache.get(index).promise;
    const item = {buffers:null, controller:new AbortController()};
    this.cache.set(index,item);
    item.promise = Promise.all(Object.entries(this.manifest.layers).map(async ([field, urls]) => {
      const response = await fetch(urls[index],{signal:item.controller.signal});
      if (!response.ok) throw new Error('음원을 불러오지 못했습니다. 재생을 다시 눌러주세요.');
      const buffer = await this.context.decodeAudioData(await response.arrayBuffer());
      return [field,buffer];
    })).then(entries => item.buffers = Object.fromEntries(entries)).catch(error => {
      if (this.cache.get(index) === item) this.cache.delete(index);
      throw error;
    });
    return item.promise;
  }
  prune(index) {
    for (const [key,item] of this.cache) if (key < index-1 || key > index+1) {
      item.controller.abort(); this.cache.delete(key);
    }
  }
  async play() {
    this.init();
    const resumed = this.context.resume(); // Called synchronously from the tap.
    this.wanted = true;
    const generation = ++this.generation;
    this.notify('음원 준비 중…'); this.busy = true;
    try {
      await resumed;
      if (this.context.state !== 'running') throw new Error('소리를 켜려면 재생을 다시 눌러주세요.');
      const index = this.index(); this.prune(index);
      await this.load(index);
      if (this.disposed || !this.wanted || generation !== this.generation) return;
      this.load(index+1).catch(()=>{});
      await this.video.play(); // The silent, inline video is allowed after loading.
      if (!this.wanted || generation !== this.generation) { this.video.pause(); return; }
      this.notify('재생 중'); this.schedule();
    } catch (error) {
      if (!this.disposed && generation === this.generation) { this.pause(); this.notify(error.message); }
    } finally { if (generation === this.generation) this.busy = false; }
  }
  pause() {
    this.wanted = false; this.generation++; this.busy = false;
    this.video.pause(); this.stopAudio();
  }
  stopAudio() {
    for (const source of this.sources) { try {source.stop();} catch (_) {} source.disconnect(); }
    this.sources = []; this.scheduled.clear(); this.anchor = null;
  }
  schedule() {
    if (!this.context || !this.wanted || this.video.paused || this.video.seeking || this.video.readyState < 3) return;
    const index = this.index();
    if (!this.cache.get(index)?.buffers) return;
    if (!this.anchor) this.anchor = {audio:this.context.currentTime, video:this.video.currentTime};
    for (const part of [index,index+1]) {
      const buffers = this.cache.get(part)?.buffers;
      if (!buffers || this.scheduled.has(part)) continue;
      const start = part*this.manifest.segment_seconds;
      const when = Math.max(this.context.currentTime,this.anchor.audio + Math.max(0,start-this.anchor.video));
      const offset = Math.max(0,this.anchor.video+when-this.anchor.audio-start);
      for (const [field,buffer] of Object.entries(buffers)) {
        const length = Math.min(buffer.duration-offset,this.manifest.segment_seconds-offset,this.manifest.duration-start-offset);
        if (length <= 0) continue;
        const source = this.context.createBufferSource();
        source.buffer = buffer; source.connect(this.gains[field]);
        source.start(when,offset,length); this.sources.push(source);
        source.onended = () => {source.disconnect();this.sources=this.sources.filter(item=>item!==source);};
      }
      this.scheduled.add(part);
    }
  }
  tick() {
    if (!this.wanted || this.busy || this.video.paused || this.video.seeking || !this.context) return;
    if (this.context.state !== 'running') {this.pause();this.notify('소리가 일시정지됐습니다. 재생을 다시 눌러주세요.');return;}
    const index = this.index(); this.prune(index);
    if (!this.cache.get(index)?.buffers) {
      this.video.pause(); this.stopAudio(); this.play(); return;
    }
    this.load(index+1).catch(()=>{});
    if (this.anchor && Math.abs(this.anchor.video+this.context.currentTime-this.anchor.audio-this.video.currentTime)>.3) this.stopAudio();
    this.schedule();
  }
  dispose() {
    this.disposed = true; this.pause(); clearInterval(this.timer);
    for (const [event,fn] of this.listeners) this.video.removeEventListener(event,fn);
    for (const item of this.cache.values()) item.controller.abort();
    this.cache.clear(); this.context?.close().catch(()=>{});
  }
}
globalThis.StudioAudioMixer = StudioAudioMixer;
