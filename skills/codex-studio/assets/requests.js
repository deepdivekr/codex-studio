'use strict';

const requestStates = {pending:'대기', in_progress:'작업 중', done:'완료', blocked:'확인 필요'};
let savedRequests = [], requestSnapshot = '', requestsLoading = null, thumbnailObserver;
const thumbnailCache = new Map();
let thumbnailQueue = [], thumbnailRunning = false, thumbnailVideo, thumbnailSource;

async function refreshRequests() {
  if (requestsLoading) return requestsLoading;
  requestsLoading = (async () => {
    const rows = await request('/api/requests');
    const snapshot = JSON.stringify(rows);
    savedRequests = rows;
    const pending = rows.filter(item => item.status !== 'done').length;
    $('request-count').textContent = rows.length ? '(' + pending + ')' : '';
    $('request-sync').textContent = '자동 업데이트 · ' + new Date().toLocaleTimeString();
    $('request-unsaved').hidden = !dirty;
    if (snapshot !== requestSnapshot) {
      requestSnapshot = snapshot;
      showRequests();
    }
  })();
  try { await requestsLoading; } finally { requestsLoading = null; }
}

function requestStamp(item) {
  if (item.frame === null) return item.kind === 'image' ? selectionLabel(item.selection) : '문서';
  const [n,d = 1] = item.fps.split('/').map(Number);
  const rate = n / d, seconds = Math.floor(item.frame / rate);
  return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60,
    Math.max(0,item.frame - Math.ceil(seconds * rate))].map(x => String(x).padStart(2,'0')).join(':');
}

async function openRequest(item, result = false) {
  const key = result ? item.result_artifact : item.artifact;
  if (artifact?.id !== key) await openArtifact(key);
  if (artifact?.id !== key) return;
  showPage('review');
  if (!result && item.kind === 'image') selectImageRegion(item.selection || null);
  if (!result && item.frame !== null && player) {
    if (Number.isFinite(player.duration)) seek(item.frame);
    else {
      const selected = player;
      selected.addEventListener('loadedmetadata', () => { if (player === selected) seek(item.frame); }, {once:true});
    }
  }
}

function showRequests() {
  if (!$('requests') || $('requests-page').hidden) return;
  thumbnailObserver?.disconnect();
  thumbnailQueue = [];
  thumbnailObserver = new IntersectionObserver(entries => {
    for (const entry of entries) if (entry.isIntersecting) {
      thumbnailObserver.unobserve(entry.target);
      const item = savedRequests.find(row => row.artifact === entry.target.dataset.artifact && row.id === entry.target.dataset.id);
      if (item) { thumbnailQueue.push({item, target:entry.target}); pumpThumbnails(); }
    }
  }, {rootMargin:'160px'});
  const state = $('request-state').value, key = $('request-artifact').value;
  const rows = savedRequests.filter(item => (!key || item.artifact === key)
    && (state === 'all' || (state === 'open' ? item.status !== 'done' : item.status === state)));
  $('requests-empty').hidden = !!rows.length;
  $('requests-empty').textContent = savedRequests.length ? '이 조건에 맞는 요청이 없습니다.' : '저장한 수정 요청이 없습니다. 장면에 댓글을 남기고 편집안을 저장하세요.';
  $('requests').replaceChildren(...rows.map(item => {
    const card = node('article'); card.className = 'request-card';
    const preview = node('button'); preview.className = 'request-preview';
    preview.setAttribute('aria-label', item.title + ' ' + requestStamp(item) + ' 장면으로 이동');
    preview.onclick = guard(() => openRequest(item));
    const shot = node('span', item.kind === 'html' ? 'HTML' : '썸네일 준비 중');
    shot.className = 'request-shot'; shot.dataset.artifact = item.artifact; shot.dataset.id = item.id;
    preview.append(shot, node('span', requestStamp(item)));
    if (item.kind === 'video') thumbnailObserver.observe(shot);
    else if (item.kind === 'image') {
      imageRequestThumbnail(shot, item);
    }
    const body = node('div'); body.className = 'stack request-body';
    const heading = node('div'); heading.className = 'row spread';
    const badge = node('span', requestStates[item.status]); badge.className = 'request-badge ' + item.status;
    heading.append(node('h3', item.title), badge);
    const comment = node('p', item.text); comment.className = 'request-comment';
    body.append(heading, comment);
    if (item.frame !== null) { const frame = node('p', '프레임 ' + item.frame); frame.className = 'quiet'; body.append(frame); }
    if (item.summary) {
      const response = node('div'); response.className = 'request-result stack';
      response.append(node('strong', (roleNames[item.by] || '에이전트') + ' · ' + requestStates[item.status]), node('p', item.summary));
      if (item.checks) response.append(node('p', '확인: ' + item.checks));
      if (item.files.length) { const files = node('p', '결과 파일: ' + item.files.join(', ')); files.className = 'quiet'; response.append(files); }
      if (item.updated_at) { const when = node('p', new Date(item.updated_at).toLocaleString()); when.className = 'quiet'; response.append(when); }
      body.append(response);
    } else { const waiting = node('p','아직 반영 결과가 없습니다.'); waiting.className = 'quiet'; body.append(waiting); }
    const actions = node('div'); actions.className = 'row';
    if (item.result_artifact) {
      const result = node('button','반영된 작업물 보기'); result.onclick = guard(() => openRequest(item, true)); actions.append(result);
    }
    if (item.status === 'done') {
      const reopen = node('button','다시 확인 요청');
      reopen.onclick = guard(async () => {
        reopen.disabled = true;
        try {
          await request('/api/requests/' + item.artifact + '/' + item.id, {
            revision:item.revision, request_version:item.request_version, status:'pending',
            by:'human', summary:'반영된 내용을 다시 확인해 주세요.', checks:'', files:[]});
          await refreshRequests();
        } finally { reopen.disabled = false; }
      }); actions.append(reopen);
    }
    if (actions.childNodes.length) body.append(actions);
    if (item.history.length > 1 || (item.history.length && !item.summary)) {
      const history = node('details'); history.className = 'request-history'; history.append(node('summary','처리 기록'));
      for (const event of item.history) history.append(node('p',
        new Date(event.at).toLocaleString() + ' · ' + (roleNames[event.by] || event.by) + ' · '
        + requestStates[event.status] + '\n' + event.request_text + '\n' + event.summary));
      body.append(history);
    }
    card.append(preview, body); return card;
  }));
}

function mediaEvent(media, event, action) {
  return new Promise((resolve, reject) => {
    const finish = error => {
      clearTimeout(timer); media.removeEventListener(event, success); media.removeEventListener('error', failed);
      error ? reject(error) : resolve();
    };
    const success = () => finish(), failed = () => finish(new Error('Media unavailable'));
    const timer = setTimeout(failed, 15000);
    media.addEventListener(event, success, {once:true}); media.addEventListener('error', failed, {once:true});
    try { action(); } catch (error) { finish(error); }
  });
}

async function frameThumbnail(item) {
  const source = item.artifact + ':' + item.source_version;
  const key = source + ':' + item.frame;
  if (thumbnailCache.has(key)) return thumbnailCache.get(key);
  if (!thumbnailVideo) { thumbnailVideo = document.createElement('video'); thumbnailVideo.muted = true; thumbnailVideo.preload = 'auto'; }
  const video = thumbnailVideo;
  if (thumbnailSource !== source) {
    thumbnailSource = null;
    await mediaEvent(video, 'loadeddata', () => { video.src = '/media/' + item.artifact + '/file'; video.load(); });
    thumbnailSource = source;
  }
  const [n,d = 1] = item.fps.split('/').map(Number);
  const target = (item.frame + .25) / (n / d);
  if (target >= video.duration) throw new Error('Frame is outside video');
  await mediaEvent(video, 'seeked', () => { video.currentTime = target; });
  const canvas = document.createElement('canvas'); canvas.width = 320; canvas.height = 180;
  const context = canvas.getContext('2d'); context.fillStyle = '#080808'; context.fillRect(0,0,320,180);
  const scale = Math.min(320 / video.videoWidth, 180 / video.videoHeight);
  const width = video.videoWidth * scale, height = video.videoHeight * scale;
  context.drawImage(video, (320-width)/2, (180-height)/2, width, height);
  const image = canvas.toDataURL('image/jpeg', .8);
  if (thumbnailCache.size >= 200) thumbnailCache.delete(thumbnailCache.keys().next().value);
  thumbnailCache.set(key,image); return image;
}

async function pumpThumbnails() {
  if (thumbnailRunning) return;
  thumbnailRunning = true;
  try {
    while (thumbnailQueue.length) {
      const {item,target} = thumbnailQueue.shift();
      if (!target.isConnected || $('requests-page').hidden) continue;
      try {
        const image = node('img'); image.alt = item.title + ' · ' + requestStamp(item); image.src = await frameThumbnail(item);
        if (target.isConnected) target.replaceChildren(image);
      } catch (_) { if (target.isConnected) target.textContent = '썸네일을 불러올 수 없습니다'; }
    }
  } finally { thumbnailRunning = false; }
}
