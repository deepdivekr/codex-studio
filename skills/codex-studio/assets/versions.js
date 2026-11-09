'use strict';

let videoVersions = [], versionKey = '', selectedRev = null, versionsSnapshot = '';
async function refreshVersions(reset = false) {
  const key = $('versions-artifact').value;
  if (!key) { videoVersions = []; showVersions(); return; }
  const rows = await request('/api/versions/' + key);
  if ($('versions-artifact').value !== key) return;
  const snapshot = JSON.stringify(rows);
  if (reset || versionKey !== key) { selectedRev = null; versionsSnapshot = ''; }
  versionKey = key;
  videoVersions = rows;
  if (versionsSnapshot !== snapshot) { versionsSnapshot = snapshot; showVersions(); }
}

function showVersions() {
  $('versions-empty').hidden = !!videoVersions.length;
  $('version-detail').hidden = !videoVersions.length;
  if (!videoVersions.some(item => item.rev === selectedRev)) selectedRev = videoVersions[0]?.rev;
  $('version-list').replaceChildren(...videoVersions.map(item => {
    const button = node('button'); button.className = 'version-choice';
    button.setAttribute('aria-pressed',item.rev === selectedRev);
    button.append(node('strong','rev' + item.rev), node('span',item.state === 'ready' ? '반영 완료 · MP4' : '반영 대기'),
      node('small',new Date(item.created_at).toLocaleString()));
    button.onclick = () => { selectedRev = item.rev; showVersions(); };
    return button;
  }));
  $('version-detail').querySelector('video')?.pause();
  $('version-detail').replaceChildren();
  const item = videoVersions.find(row => row.rev === selectedRev);
  if (!item) return;
  const detail = $('version-detail');
  const heading = node('div'); heading.className = 'row spread';
  heading.append(node('h3', 'rev' + item.rev + ' · ' + item.title));
  if (item.state === 'ready') {
    const download = node('a','rev' + item.rev + ' MP4 다운로드'); download.className = 'button primary';
    download.href = '/versions/' + item.artifact + '/' + item.rev + '/download';
    heading.append(download);
  }
  detail.append(heading);
  if (item.state === 'ready') {
    const video = node('video'); video.controls = true; video.playsInline = true; video.preload = 'metadata';
    video.src = '/versions/' + item.artifact + '/' + item.rev + '/video'; video.className = 'version-video';
    video.setAttribute('aria-label','rev' + item.rev + ' 완료 영상');
    const result = node('div'); result.className = 'request-result stack';
    result.append(node('strong',(roleNames[item.by] || '에이전트') + ' · 반영 완료'), node('p',item.summary), node('p','확인: ' + item.checks));
    detail.append(video,result);
  } else {
    const pending = node('p','이 편집안의 수정 영상은 아직 준비되지 않았습니다. 반영이 완료되면 여기에서 재생하고 내려받을 수 있습니다.');
    pending.className = 'notice'; detail.append(pending);
  }
  detail.append(node('h3','이 버전에 저장한 수정사항'));
  const levels = node('p','나레이션 ' + (item.review.voice ?? 100) + '% · 배경음악 ' + item.review.music + '% · 효과음 ' + (item.review.effects ?? 100) + '%');
  levels.className = 'quiet'; detail.append(levels);
  for (const note of item.review.notes) {
    const result = item.request_results.find(row => row.id === note.id);
    const block = node('div'); block.className = 'version-note';
    const stamp = requestStamp({...note, fps:item.source.fps, kind:item.source.kind});
    block.append(node('strong', stamp + (result ? ' · ' + requestStates[result.status] : '')),node('p', note.text));
    if (result?.summary) block.append(node('p',result.summary));
    detail.append(block);
  }
  const captions = Object.entries(item.review.captions);
  if (captions.length) {
    const edits = node('details'); edits.append(node('summary',item.review.mode === 'script' ? '저장한 대본 수정' : '저장한 자막 수정'));
    for (const [index,text] of captions) edits.append(node('p',(Number(index)+1) + '. ' + text));
    detail.append(edits);
  }
}
