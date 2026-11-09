'use strict';

let imageSelection = null, imageStage = null, imageMode = 'rect';

function selectionLabel(selection) {
  if (!selection) return '이미지 전체';
  const x = Math.floor(selection.x * selection.image_width);
  const y = Math.floor(selection.y * selection.image_height);
  if (selection.kind === 'point') return `지점 (${Math.min(x,selection.image_width-1)}, ${Math.min(y,selection.image_height-1)})`;
  const width = Math.ceil((selection.x + selection.width) * selection.image_width) - x;
  const height = Math.ceil((selection.y + selection.height) * selection.image_height) - y;
  return `영역 (${x}, ${y}) · ${width} × ${height}px`;
}

function selectImageRegion(selection) {
  imageSelection = selection ? structuredClone(selection) : null;
  $('image-selection').textContent = selection ? selectionLabel(selection) : '이미지 전체에 대한 요청';
  $('image-clear').disabled = !selection;
  if (!imageStage) return;
  const marker = imageStage.querySelector('.image-marker');
  marker.hidden = !selection;
  if (!selection) return;
  marker.className = 'image-marker ' + selection.kind;
  marker.style.left = (selection.x * 100) + '%';
  marker.style.top = (selection.y * 100) + '%';
  marker.style.width = selection.kind === 'rect' ? (selection.width * 100) + '%' : '18px';
  marker.style.height = selection.kind === 'rect' ? (selection.height * 100) + '%' : '18px';
}

function mountImage(preview, id) {
  preview.classList.add('image-preview');
  const stage = node('div'); stage.className = 'image-stage'; stage.tabIndex = 0;
  stage.setAttribute('role', 'group');
  stage.setAttribute('aria-label', '이미지에서 수정 영역 선택');
  stage.title = '드래그 또는 클릭으로 지정 · Enter로 중앙 선택 · 방향키로 이동 · Esc로 해제';
  const img = node('img'); img.alt = artifact.title; img.draggable = false;
  const marker = node('div'); marker.className = 'image-marker'; marker.hidden = true;
  marker.setAttribute('aria-hidden','true');
  stage.append(img, marker); preview.append(stage); imageStage = stage;
  let ready = false, drag = null;
  const sourceHash = artifact.fingerprints.file;
  img.onload = () => { ready = true; stage.style.width = (70 * img.naturalWidth / img.naturalHeight) + 'vh'; };
  img.onerror = () => { ready = false; if (imageStage === stage) status('이미지를 불러오지 못했습니다. 원본 파일을 확인하세요.'); };
  img.src = '/media/' + id + '/file';
  const shape = (kind,x,y,width,height) => ({kind,x,y,
    ...(kind === 'rect' ? {width,height} : {}),
    image_width:img.naturalWidth, image_height:img.naturalHeight, source_sha256:sourceHash});
  const position = event => {
    const box = stage.getBoundingClientRect();
    return {x:Math.max(0,Math.min(1,(event.clientX-box.left)/box.width)),
      y:Math.max(0,Math.min(1,(event.clientY-box.top)/box.height))};
  };
  function mode(value) {
    imageMode = value;
    for (const kind of ['rect','point']) $('image-' + kind).setAttribute('aria-pressed', kind === value);
  }
  $('image-rect').onclick = () => mode('rect');
  $('image-point').onclick = () => mode('point');
  $('image-clear').onclick = () => selectImageRegion(null);
  mode(imageMode); selectImageRegion(null);
  stage.onpointerdown = event => {
    if (!ready || event.button !== 0 || !event.isPrimary) return;
    event.preventDefault(); stage.focus(); stage.setPointerCapture(event.pointerId);
    const p = position(event);
    drag = {...p, pointer:event.pointerId, before:imageSelection};
    if (imageMode === 'point') selectImageRegion(shape('point',p.x,p.y));
  };
  stage.onpointermove = event => {
    if (!drag || event.pointerId !== drag.pointer || imageMode !== 'rect') return;
    const p = position(event);
    selectImageRegion(shape('rect',Math.min(drag.x,p.x),Math.min(drag.y,p.y),Math.abs(p.x-drag.x),Math.abs(p.y-drag.y)));
  };
  stage.onpointerup = event => {
    if (!drag || event.pointerId !== drag.pointer) return;
    if (imageMode === 'rect') {
      const p = position(event), width = Math.abs(p.x-drag.x), height = Math.abs(p.y-drag.y);
      selectImageRegion(width * img.naturalWidth >= 1 && height * img.naturalHeight >= 1
        ? shape('rect',Math.min(drag.x,p.x),Math.min(drag.y,p.y),width,height) : drag.before);
    }
    drag = null;
    if (stage.hasPointerCapture(event.pointerId)) stage.releasePointerCapture(event.pointerId);
  };
  stage.onpointercancel = () => { if (drag) selectImageRegion(drag.before); drag = null; };
  stage.onkeydown = event => {
    if (!ready) return;
    if (event.key === 'Escape') { event.preventDefault(); selectImageRegion(null); }
    else if (event.key === 'Enter') { event.preventDefault(); selectImageRegion(shape(imageMode,.375,.375,.25,.25)); }
    else if (imageSelection && ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key)) {
      event.preventDefault();
      const next = structuredClone(imageSelection), step = event.shiftKey ? .1 : .01;
      next.x = Math.max(0,Math.min(1-(next.width || 0),next.x + (event.key === 'ArrowLeft' ? -step : event.key === 'ArrowRight' ? step : 0)));
      next.y = Math.max(0,Math.min(1-(next.height || 0),next.y + (event.key === 'ArrowUp' ? -step : event.key === 'ArrowDown' ? step : 0)));
      selectImageRegion(next);
    }
  };
}

function imageRequestThumbnail(target, item) {
  const img = new Image();
  img.onload = () => {
    if (!target.isConnected) return;
    const canvas = node('canvas'); canvas.width = 320; canvas.height = 180;
    const ctx = canvas.getContext('2d'); ctx.fillStyle = '#080808'; ctx.fillRect(0,0,320,180);
    const scale = Math.min(320/img.naturalWidth,180/img.naturalHeight);
    const width = img.naturalWidth*scale, height = img.naturalHeight*scale;
    const left = (320-width)/2, top = (180-height)/2;
    ctx.drawImage(img,left,top,width,height);
    const s = item.selection;
    if (s) {
      const x = left+s.x*width, y = top+s.y*height;
      ctx.strokeStyle = '#dfc9ff'; ctx.fillStyle = 'rgba(223,201,255,.2)'; ctx.lineWidth = 3;
      if (s.kind === 'rect') { ctx.fillRect(x,y,s.width*width,s.height*height); ctx.strokeRect(x,y,s.width*width,s.height*height); }
      else { ctx.beginPath(); ctx.arc(x,y,7,0,Math.PI*2); ctx.fill(); ctx.stroke(); }
    }
    const thumbnail = node('img'); thumbnail.alt = item.title + ' · ' + selectionLabel(s);
    thumbnail.src = canvas.toDataURL('image/png'); target.replaceChildren(thumbnail);
  };
  img.onerror = () => { target.textContent = '원본 이미지 확인 필요'; };
  img.src = '/media/' + item.artifact + '/file';
}
