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
let fps = 30, dirty = false, saving = false, switching = false, replyTo = null;
const status = text => { $('status').textContent = text; };
const guard = callback => async (...args) => {
  try { await callback(...args); } catch (error) { status(error.message); }
};
async function request(path, data) {
  const response = await fetch(path, data === undefined ? {} : {
    method:'POST', headers:{'Content-Type':'application/json','X-Artifact-Token':token},
    body:JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '요청을 처리할 수 없습니다.');
  return result;
}
function route(id) { return '/api/artifacts/' + encodeURIComponent(id); }
function showPage(name) {
  const editing = name === 'review';
  $('review-tab').setAttribute('aria-pressed', editing);
  $('handoff-tab').setAttribute('aria-pressed', !editing);
  $('review-page').hidden = !editing;
  $('handoff-page').hidden = editing;
  if (!editing) player?.pause();
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
  setOptions($('link-artifact'), board.artifacts, '연결 안 함');
  $('empty').hidden = !!board.artifacts.length;
  $('artifacts').disabled = !board.artifacts.length;
  showHandoffs();
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
    $('music-control').hidden = !artifact.music;
    $('edit-mode').value = review.mode;
    $('script-changes').open = false;
    $('srt').href = '/export/' + id + '.srt';
    $('note-title').textContent = isVideo ? '프레임 메모' : '아티펙트 메모';
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
    status(artifact.title + ' · 편집안 v' + review.revision);
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
  if (bed) bed.volume = review.music / 100;
  $('music').value = review.music;
  $('music-value').value = review.music + '%';
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
  for (const field of ['voice','music']) {
    if (!artifact[field]) continue;
    const audio = node('audio');
    audio.preload = 'metadata';
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
function recordFields(item) {
  return [['완료한 일과 결정',item.summary],['이어 할 일',item.next],['검증',item.checks],
    ['관련 파일',item.files.join('\n')],['Git 기준',[item.branch,item.commit].filter(Boolean).join(' · ')],
    ['연결',item.artifact ? item.artifact + ' · 편집안 v' + item.review_revision : '']];
}
function showHandoffs() {
  const current = $('role').value;
  const inbox = board?.handoffs || [];
  const replied = new Set(inbox.map(item => item.reply_to).filter(Boolean));
  const pending = inbox.filter(item => item.to === current && !replied.has(item.id)).length;
  $('inbox-count').textContent = pending ? '(' + pending + ')' : '';
  $('handoffs').replaceChildren();
  if (!inbox.length) $('handoffs').append(node('p','기록된 인계가 없습니다.'));
  for (const item of inbox) {
    const details = node('details');
    details.className = 'record';
    const answered = replied.has(item.id);
    details.open = item.to === current && !answered;
    details.append(node('summary',roleNames[item.from] + ' → ' + roleNames[item.to] + ' · ' + item.title));
    const when = new Date(item.created_at).toLocaleString();
    const state = answered ? '답장 완료' : item.acknowledgment ? '수신 확인' : '수신 대기';
    const hint = node('p',when + ' · ' + state);
    hint.className = 'quiet';
    details.append(hint);
    const fields = node('dl');
    recordFields(item).filter(([,value]) => value).forEach(([key,value]) => fields.append(node('dt',key),node('dd',value)));
    details.append(fields);
    const actions = node('div');
    actions.className = 'row';
    if (item.to === current && !answered) {
      if (!item.acknowledgment) {
        const ack = node('button','수신 확인');
        ack.onclick = guard(async () => {
          await request('/api/handoffs/' + item.id + '/ack',{by:current});
          await refresh(); status('수신 확인을 기록했습니다.');
        });
        actions.append(ack);
      }
      const reply = node('button','답장');
      reply.onclick = () => {
        replyTo = item.id;
        $('recipient').value = item.from;
        $('recipient').disabled = true;
        $('link-artifact').value = item.artifact || '';
        $('form-title').textContent = '인계에 답장';
        $('reply-context').textContent = item.title;
        $('reply-context').hidden = false;
        $('clear-reply').hidden = false;
        $('handoff-title').focus();
      };
      actions.append(reply);
    }
    details.append(actions);
    $('handoffs').append(details);
  }
}
function resetReply() {
  replyTo = null;
  $('recipient').disabled = false;
  $('form-title').textContent = '새 인계';
  $('reply-context').hidden = true;
  $('clear-reply').hidden = true;
  $('recipient').value = $('role').value === 'claude' ? 'codex' : 'claude';
}

$('artifacts').onchange = guard(event => openArtifact(event.target.value));
$('role').onchange = () => { localStorage.setItem('artifact-role', $('role').value); resetReply(); showHandoffs(); };
$('review-tab').onclick = () => showPage('review');
$('handoff-tab').onclick = guard(async () => { showPage('handoff'); await refresh(); });
$('refresh').onclick = guard(async () => {
  await refresh();
  if (!artifact && board.artifacts.length) await openArtifact($('artifacts').value);
  status('목록을 새로고침했습니다.');
});
$('clear-reply').onclick = resetReply;
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
$('music').oninput = event => { review.music = Number(event.target.value); setMusic(); changed(); };
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
  review.notes.push({id:crypto.randomUUID(), frame:frameNow(), author:$('role').value, text});
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
    if (!dirty) review.script_approved = stored.script_approved;
    status(dirty ? '새 변경을 다시 저장하세요.' : '편집안 v' + stored.revision + ' 저장됨');
  } finally { saving = false; $('save').disabled = !dirty; showScript(); }
});
$('handoff-form').onsubmit = guard(async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const sender = $('role').value;
  const recipient = $('recipient').value;
  const id = $('link-artifact').value;
  if (dirty && artifact.id === id) return status('연결할 편집안을 먼저 저장하세요.');
  const submit = form.querySelector('button.primary');
  submit.disabled = true;
  try {
    await request('/api/handoffs', {from:sender,to:recipient,reply_to:replyTo,artifact:id,
      title:$('handoff-title').value,summary:$('summary').value,next:$('next-step').value,
      checks:$('checks').value,files:$('files').value.split('\n').map(x=>x.trim()).filter(Boolean)});
    form.reset(); resetReply(); await refresh(); status('인계서를 기록했습니다.');
  } finally { submit.disabled = false; }
});
window.addEventListener('beforeunload', event => { if (dirty) event.preventDefault(); });
guard(async () => {
  const actor = localStorage.getItem('artifact-role');
  if (Object.hasOwn(roleNames, actor)) $('role').value = actor;
  resetReply();
  await refresh();
  const requested = new URLSearchParams(location.search).get('artifact');
  if (board.artifacts.length) await openArtifact(board.artifacts.some(x=>x.id===requested) ? requested : $('artifacts').value);
  else status('저장소 연결됨');
})();
