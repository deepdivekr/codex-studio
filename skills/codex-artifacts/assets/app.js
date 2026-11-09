'use strict';

const $ = id => document.getElementById(id);
const node = (tag, text) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  return element;
};
const token = document.querySelector('meta[name=artifact-token]').content;
const roleNames = {human:'사용자', codex:'Codex', claude:'Claude'};
let board, artifact, review, cues = [], player, tracks = [], bed, overlay, activeCue = -2;
let fps = 30, dirty = false, saving = false, switching = false, connected = false;
const status = text => { $('status').textContent = text; };
const guard = callback => async (...args) => {
  try { await callback(...args); } catch (error) { status(error.message); }
};
async function request(path, data) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(path, {signal:controller.signal, ...(data === undefined ? {} : {
      method:'POST', headers:{'Content-Type':'application/json','X-Artifact-Token':token},
      body:JSON.stringify(data)
    })});
    if (!response.headers.get('Content-Type')?.includes('application/json'))
      throw new Error('편집 서버의 응답이 아닙니다. 대화에서 편집실을 다시 열어달라고 요청하세요.');
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '요청을 처리할 수 없습니다.');
    return result;
  } catch (error) {
    if (error.name === 'AbortError' || error instanceof TypeError)
      throw new Error(data === undefined
        ? '편집 서버에 연결하지 못했습니다. 서버가 켜져 있는지 확인하거나 대화에서 편집실을 다시 열어달라고 요청하세요.'
        : '저장 결과를 확인하지 못했습니다. 현재 내용을 보관하고 저장된 기록을 확인한 뒤 다시 시도하세요.');
    throw error;
  } finally { clearTimeout(timeout); }
}
function route(id) { return '/api/artifacts/' + encodeURIComponent(id); }
function showPage(name) {
  const editing = name === 'review';
  for (const page of ['review','requests','versions']) {
    $(page + '-tab').setAttribute('aria-pressed', name === page);
    $(page + '-page').hidden = name !== page;
  }
  if (name !== 'versions') $('version-detail').querySelector('video')?.pause();
  $('request-unsaved').hidden = !dirty;
  if (!editing) { player?.pause(); showRequests(); }
}
function setOptions(select, rows, placeholder) {
  const before = select.value;
  select.replaceChildren();
  if (placeholder !== undefined) select.add(new Option(placeholder,''));
  rows.forEach(row => select.add(new Option(row.title,row.id)));
  if (Array.from(select.options).some(item=>item.value===before)) select.value = before;
}
async function refresh() {
  board = await request('/api/board');
  $('project').textContent = board.project;
  setOptions($('artifacts'), board.artifacts);
  setOptions($('request-artifact'), board.artifacts, '모든 작업물');
  setOptions($('versions-artifact'), board.artifacts.filter(item => item.kind === 'video'));
  $('empty').hidden = !!board.artifacts.length;
  $('artifacts').disabled = !board.artifacts.length;
  await refreshRequests();
  if (!$('versions-page').hidden) await refreshVersions();
}
function allowSwitch() {
  if (saving || switching) return false;
  return !dirty || confirm('저장하지 않은 편집안을 버리고 다른 아티펙트로 이동할까요?');
}
async function openArtifact(id) {
  if (!id || !allowSwitch()) {
    if (artifact) $('artifacts').value = artifact.id;
    return;
  }
  switching = true;
  try {
    const result = await request(route(id));
    player?.pause();
    pauseTracks();
    player = null; bed = null; tracks = []; activeCue = -2;
    ({artifact, cues, review} = result);
    review.mode ??= "caption";
    review.voice ??= 100; review.effects ??= 100;
    dirty = false;
    $('save').disabled = true;
    $('artifacts').value = id;
    $('workspace').hidden = false;
    $('screen').replaceChildren();
    const preview = node('div');
    preview.className = 'preview';
    $('screen').append(preview);
    const isVideo = artifact.kind === 'video';
    $('transport').hidden = !isVideo;
    $('subtitle-box').hidden = !isVideo || !cues.length;

    $('edit-mode').value = review.mode;
    $('script-changes').open = false;
    $('srt').href = '/export/' + id + '.srt';
    $('note-title').textContent = isVideo ? '이 프레임의 수정 요청' : '수정 요청';
    $('note').value = '';
    if (isVideo) mountVideo(preview, id);
    if (artifact.kind === 'image') {
      const img = node('img');
      img.alt = artifact.title;
      img.src = '/media/' + id + '/file';
      preview.append(img);
    }
    if (artifact.kind === 'html') {
      const iframe = node('iframe');
      iframe.title = artifact.title;
      iframe.setAttribute('sandbox','allow-scripts');
      iframe.src = artifact.preview;
      preview.append(iframe);
    }
    showNotes();
    showScript();
    status(artifact.title + (review.saved_rev ? ' · rev' + review.saved_rev + ' 편집안' : ' · 편집안'));
  } catch (error) {
    if (artifact) $('artifacts').value = artifact.id;
    throw error;
  } finally { switching = false; }
}
const pad = n => String(n).padStart(2,'0');
function timecode(frame) {
  const t = Math.floor(frame / fps);
  const f = frame - Math.ceil(t * fps);
  return [Math.floor(t / 3600), Math.floor(t / 60) % 60, t % 60, Math.max(0,f)].map(pad).join(':');
}
const frameNow = () => player ? Math.floor(player.currentTime * fps + .000001) : null;
function maxFrame() {
  return Math.max(0, Math.ceil((Number.isFinite(player.duration) ? player.duration : 0) * fps) - 1);
}
function seek(frame) {
  if (!player || !Number.isFinite(player.duration)) return;
  player.pause();
  player.currentTime = Math.min(player.duration, (Math.min(maxFrame(), Math.max(0,frame)) + .2) / fps);
  drawVideo();
}
function cueAt(time) {
  let lo = 0, hi = cues.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (cues[mid].start <= time) lo = mid + 1;
    else hi = mid;
  }
  return lo > 0 && cues[lo-1].end > time ? lo - 1 : -1;
}
const subtitleText = index => index < 0 ? '' : (review.captions[index] ?? cues[index].text);
function drawVideo() {
  const index = cueAt(player.currentTime);
  $('scrub').value = player.currentTime;
  $('time').value = timecode(frameNow());
  overlay.textContent = subtitleText(index);
  if (activeCue === index) return;
  activeCue = index;
  $('caption').value = subtitleText(index);
  $('caption').disabled = index < 0;
  $('reset-caption').disabled = index < 0;
  $('cue-label').textContent = index < 0 ? '자막이 없는 구간' : timecode(Math.ceil(cues[index].start * fps));
}
function setMusic() {
  for (const field of ['voice','music','effects']) {
    const available = field === 'voice' || !!artifact[field];
    const level = review[field] ?? 100;
    const track = tracks.find(item => item.dataset.layer === field);
    if (track) track.volume = level / 100;
    if (field === 'voice' && player && !artifact.voice) player.volume = level / 100;
    $(field).value = level;
    $(field).disabled = !available;
    $(field + '-value').value = available ? level + '%' : '미연결';
    $(field + '-mute').disabled = !available;
    $(field + '-mute').setAttribute('aria-pressed', level === 0);
    $(field + '-mute').textContent = level === 0 ? '켜기' : '음소거';
  }
  $('voice-label').textContent = artifact.voice ? '나레이션' : '원본 소리';
  $('voice').setAttribute('aria-label', artifact.voice ? '나레이션 볼륨' : '원본 소리 볼륨');
  const missing = [['music','배경음악'],['effects','효과음']].filter(([field]) => !artifact[field]).map(([,label]) => label);
  $('audio-hint').textContent = !artifact.voice
    ? '원본 소리에는 여러 소리가 함께 들어 있을 수 있습니다. 개별 조절에는 분리된 원본 음원이 필요합니다.'
    : missing.length ? missing.join(' · ') + ' 원본을 연결하면 개별 조절할 수 있습니다.' : '나레이션 · 배경음악 · 효과음이 각각 연결되어 있습니다.';
}
function pauseTracks() { tracks.forEach(track => track.pause()); }
function syncTracks(force = false) {
  tracks.forEach(track => {
    if (!track.readyState || !Number.isFinite(track.duration)) return;
    const target = Math.min(player.currentTime, track.duration);
    if (force || Math.abs(track.currentTime - target) > .12) track.currentTime = target;
  });
}
function playTracks() {
  tracks.forEach(track => {
    if (!Number.isFinite(track.duration) || player.currentTime < track.duration)
      track.play().catch(() => status('별도 음원을 재생하지 못했습니다.'));
  });
}
function mountVideo(preview, id) {
  const rate = artifact.fps.split('/').map(Number);
  fps = rate[0] / (rate[1] || 1);
  const video = node('video');
  player = video;
  video.playsInline = true;
  video.preload = 'metadata';
  video.muted = !!artifact.voice;
  const mask = node('div');
  mask.className = 'caption-mask';
  mask.style.height = artifact.mask + '%';
  overlay = node('div');
  overlay.className = 'overlay';
  preview.append(video, mask, overlay);
  for (const field of ['voice','music','effects']) {
    if (!artifact[field]) continue;
    const audio = node('audio');
    audio.preload = 'metadata';
    audio.dataset.layer = field;
    audio.src = '/media/' + id + '/' + field;
    tracks.push(audio);
    preview.append(audio);
    if (field === 'music') bed = audio;
  }
  const current = fn => () => { if (player === video) fn(); };
  video.onloadedmetadata = current(() => {
    $('scrub').max = video.duration;
    for (const name of ['scrub','play','back','next']) $(name).disabled = false;
    drawVideo();
  });
  video.onplaying = current(() => {
    $('play').textContent = '일시정지'; syncTracks(true); playTracks();
  });
  video.onpause = current(() => { pauseTracks(); $('play').textContent = '재생'; drawVideo(); });
  video.onwaiting = current(pauseTracks);
  video.onseeking = current(pauseTracks);
  video.onseeked = current(() => { syncTracks(true); drawVideo(); if (!video.paused) playTracks(); });
  video.ontimeupdate = current(() => { drawVideo(); if (!video.paused && !video.seeking) syncTracks(); });
  video.onerror = current(() => status('영상 파일을 재생할 수 없습니다. 브라우저 코덱과 등록 경로를 확인하세요.'));
  for (const name of ['scrub','play','back','next']) $(name).disabled = true;
  $('play').textContent = '재생';
  video.src = '/media/' + id + '/file';
  if (video.requestVideoFrameCallback) {
    const refreshFrame = () => {
      if (player !== video) return;
      drawVideo();
      video.requestVideoFrameCallback(refreshFrame);
    };
    video.requestVideoFrameCallback(refreshFrame);
  }
  drawVideo();
  setMusic();
}
function showScript() {
  const script = review.mode === "script";
  const edits = cues.map((cue, index) => ({cue, index, after: review.captions[index]}))
    .filter(change => change.after !== undefined && change.after !== change.cue.text);
  $("srt").hidden = !cues.length || script;
  $("script-changes").hidden = !script;
  if (!script) return;
  $("script-count").textContent = "(" + edits.length + ")";
  $("script-diff").replaceChildren(...edits.map(({cue, index, after}) => {
    const item = node("li");
    item.append(node("span", (index + 1) + " · " + timecode(Math.ceil(cue.start * fps))),
      node("span", "기존: " + cue.text), node("span", "수정: " + after));
    return item;
  }));
  $("approve-script").disabled = dirty || saving || !!review.script_approved || !edits.length;
  $("copy-sync").hidden = !review.script_approved;
  $("copy-sync").disabled = dirty || saving;
  $("script-state").textContent = review.script_approved
    ? "승인된 대본입니다. 새 나레이션을 준비한 뒤 이 대본으로 컷과 자막을 맞출 수 있습니다."
    : "지금 재생되는 음성은 기존 나레이션입니다. 변경을 저장한 다음 대본을 검토하고 승인하세요.";
}
function changed() {
  dirty = true;
  $('save').disabled = saving;
  status('저장하지 않은 편집이 있습니다.');
  showScript();
  $('request-unsaved').hidden = !dirty;
}
function showNotes() {
  $('notes').replaceChildren();
  for (const note of review.notes) {
    const li = node('li');
    const stamp = note.frame === null ? node('span', roleNames[note.author]) : node('button',timecode(note.frame));
    if (note.frame !== null) stamp.onclick = () => seek(note.frame);
    const text = node('span', note.frame === null ? note.text : roleNames[note.author] + ' · ' + note.text);
    const remove = node('button','삭제');
    remove.onclick = () => { review.notes = review.notes.filter(item=>item.id!==note.id); showNotes(); changed(); };
    li.append(stamp, text, remove);
    $('notes').append(li);
  }
}
$('artifacts').onchange = guard(event => openArtifact(event.target.value));
$('review-tab').onclick = () => showPage('review');
$('requests-tab').onclick = guard(async () => { showPage('requests'); await refreshRequests(); });
$('versions-tab').onclick = guard(async () => {
  if (artifact?.kind === 'video') $('versions-artifact').value = artifact.id;
  showPage('versions'); await refreshVersions();
});
$('versions-artifact').onchange = guard(() => refreshVersions(true));
$('request-artifact').onchange = showRequests;
$('request-state').onchange = showRequests;

$('play').onclick = guard(async () => {
  if (!player) return;
  if (!player.paused) return player.pause();
  syncTracks(true);
  playTracks();
  try { await player.play(); } catch (error) { pauseTracks(); throw error; }
});
$('back').onclick = () => seek(frameNow() - 1);
$('next').onclick = () => seek(frameNow() + 1);
$('scrub').oninput = event => seek(Math.round(Number(event.target.value) * fps));
$('jump-form').onsubmit = event => {
  event.preventDefault();
  if (!player) return;
  const parts = $('jump').value.trim().split(':');
  if (parts.length > 3 || !parts.every(x => /^\d+(\.\d+)?$/.test(x))) return status('예: 03:21.185');
  const time = parts.reduce((t,x)=>t*60+Number(x),0);
  if (!Number.isFinite(time) || time >= player.duration) return status('영상 길이 안의 시각을 입력하세요.');
  seek(Math.floor(time*fps));
};
for (const field of ['voice','music','effects']) {
  $(field).oninput = event => { review[field] = Number(event.target.value); setMusic(); changed(); };
  $(field + '-mute').onclick = () => {
    const slider = $(field);
    if (review[field]) { slider.dataset.previous = review[field]; review[field] = 0; }
    else review[field] = Number(slider.dataset.previous || 100);
    setMusic(); changed();
  };
}
$('edit-mode').onchange = event => {
  review.mode = event.target.value;
  delete review.script_approved;
  changed();
};
$('copy-sync').onclick = guard(async () => {
  const prompt = '이 저장소의 $codex-artifacts에서 승인된 대본 ' + artifact.id
    + ' (편집안 v' + review.revision + ')을 읽어줘. 기존 음성 제작·정렬 방식을 확인하고 새 나레이션에 컷과 자막을 맞춰 별도 MP4로 만들어줘.';
  await navigator.clipboard.writeText(prompt);
  status('싱크 작업 요청을 복사했습니다.');
});
$('approve-script').onclick = guard(async () => {
  if (dirty || saving) return;
  saving = true;
  player?.pause();
  showScript();
  try {
    const stored = await request(route(artifact.id) + '/approve-script', {revision:review.revision});
    review.revision = stored.revision;
    review.saved_rev = stored.saved_rev;
    if (!dirty) review.script_approved = stored.script_approved;
    status('대본 승인 완료 · 새 나레이션에 맞춰 싱크를 조정할 수 있습니다.');
  } finally {
    saving = false;
    $('save').disabled = !dirty;
    showScript();
  }
});
$('caption').onfocus = () => player?.pause();
$('caption').oninput = () => {
  if (activeCue >= 0) {
    review.captions[activeCue] = $('caption').value;
    delete review.script_approved;
    drawVideo();
    changed();
  }
};
$('reset-caption').onclick = () => {
  if (activeCue >= 0) {
    delete review.captions[activeCue];
    delete review.script_approved;
    $('caption').value = subtitleText(activeCue);
    drawVideo();
    changed();
  }
};
$('note').onfocus = () => player?.pause();
$('add-note').onclick = () => {
  const text = $('note').value.trim();
  if (!text) return;
  if (player && !Number.isFinite(player.duration)) return status('영상이 열린 후 메모를 추가하세요.');
  player?.pause();
  review.notes.push({id:crypto.randomUUID(), frame:frameNow(), author:'human', text});
  review.notes.sort((a,b)=>(a.frame ?? 0)-(b.frame ?? 0));
  $('note').value = '';
  showNotes();
  changed();
};
$('save').onclick = guard(async () => {
  if (saving || switching) return;
  saving = true;
  $('save').disabled = true;
  const snapshot = JSON.stringify(review);
  try {
    const stored = await request(route(artifact.id),JSON.parse(snapshot));
    dirty = snapshot !== JSON.stringify(review);
    review.revision = stored.revision;
    review.saved_rev = stored.saved_rev;
    if (!dirty) review.script_approved = stored.script_approved;
    status(dirty ? '새 변경을 다시 저장하세요.' : (stored.saved_rev ? 'rev' + stored.saved_rev : '편집안') + ' 저장됨 · 수정 요청과 버전 탭에서 확인하세요.');
    await refreshRequests();
  } finally { saving = false; $('save').disabled = !dirty; showScript(); }
});
window.addEventListener('beforeunload', event => { if (dirty) event.preventDefault(); });
async function connect() {
  connected = false;
  const directFile = location.protocol === 'file:';
  $('connection-help').hidden = true;
  document.querySelector('nav').hidden = true;
  document.querySelector('main').hidden = true;
  $('retry-connection').disabled = true;
  $('retry-connection').hidden = directFile;
  status('편집실에 연결하는 중…');
  try {
    if (directFile) throw new Error('HTML 파일을 직접 열었습니다. 대화에서 “이 프로젝트의 아티펙트 편집실 열어줘”라고 요청하세요. 실행 중인 편집실의 http://127.0.0.1:포트/ 주소로 연결합니다.');
    await refresh();
    const requested = new URLSearchParams(location.search).get('artifact');
    if (requested && !board.artifacts.some(x=>x.id===requested))
      throw new Error('이 편집실에 요청한 아티펙트가 없습니다. 대화에서 해당 파일의 편집실을 다시 열어달라고 요청하세요.');
    if (board.artifacts.length) await openArtifact(requested || $('artifacts').value);
    else status('편집실 연결됨');
    document.querySelector('nav').hidden = false;
    document.querySelector('main').hidden = false;
    connected = true;
  } catch (error) {
    status(directFile ? '로컬 편집 주소로 열어주세요.' : '편집실에 연결할 수 없습니다.');
    $('connection-message').textContent = error.message;
    $('connection-help').hidden = false;
  } finally { $('retry-connection').disabled = false; }
}
$('retry-connection').onclick = connect;
connect();

let autoRefreshing = false;
async function autoRefresh() {
  if (!connected || document.hidden || autoRefreshing || saving || switching) return;
  autoRefreshing = true;
  try {
    await refresh();
    if (!artifact && board.artifacts.length) await openArtifact($('artifacts').value);
  } catch (_) {
    $('request-sync').textContent = '연결이 끊겼습니다. 자동으로 다시 확인합니다.';
  } finally { autoRefreshing = false; }
}
setInterval(autoRefresh, 5000);
window.addEventListener('focus', autoRefresh);
