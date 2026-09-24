// Octavo のプレビューの中身。pdf.js でページをそのまま canvas に描くだけ。
//
// 組み直すたびに PDF まるごとが送られてくるので、**スクロール位置を割合で
// 覚えておいて描き直したあとに戻す**。これをしないと1文字打って保存する
// たびに先頭へ跳ね、プレビューとして使いものにならない。
import * as pdfjs from './pdfjs/pdf.min.js';

// ワーカーは blob から起こす。webview の生成元（vscode-webview:）と、
// ファイルを配る生成元（…vscode-resource…）は別なので、後者の URL をそのまま
// `new Worker()` に渡すと生成元違いで作れない。取ってきて blob にすれば
// 同一生成元になる。pdf.worker.min.js は他を import しない1枚もの。
const workerUrl = new URL('./pdfjs/pdf.worker.min.js', import.meta.url).href;
try {
  const src = await (await fetch(workerUrl)).text();
  pdfjs.GlobalWorkerOptions.workerSrc =
    URL.createObjectURL(new Blob([src], { type: 'text/javascript' }));
} catch (e) {
  // 作れなくても pdf.js は本体スレッドで動く（遅いだけ）
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
}

const vscode = acquireVsCodeApi();
const view = document.getElementById('view');
const host = document.getElementById('pages-host');
const bar = document.getElementById('bar');
const label = document.getElementById('label');
const pagesLabel = document.getElementById('pages');
const message = document.getElementById('message');
const staleBar = document.getElementById('stale');
const staleText = document.getElementById('stale-text');
const staleRun = document.getElementById('stale-run');
staleRun.onclick = () => vscode.postMessage({ type: 'runAnalysis' });

let scale = 0;            // 0 = 幅に合わせる
let doc = null;
let bytes = null;         // 最後に受け取った PDF（倍率を変えるとき描き直す）
let rendering = false;
let pending = null;       // 描いている最中に次の PDF が来たとき

function b64(data) {
  const bin = atob(data);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function ratio() {
  const max = view.scrollHeight - view.clientHeight;
  return max > 0 ? view.scrollTop / max : 0;
}

function restore(r) {
  const max = view.scrollHeight - view.clientHeight;
  view.scrollTop = max > 0 ? Math.round(r * max) : 0;
}

async function render(data) {
  if (rendering) { pending = data; return; }
  rendering = true;
  bytes = data;
  const keep = ratio();
  try {
    // getDocument は渡した配列を持っていくので、描き直せるように複製を渡す
    const next = await pdfjs.getDocument({ data: data.slice(),
                                           isEvalSupported: false }).promise;
    if (doc) { try { await doc.destroy(); } catch (e) { /* 前のを捨てるだけ */ } }
    doc = next;
    const dpr = window.devicePixelRatio || 1;
    const frag = document.createDocumentFragment();
    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      const base = page.getViewport({ scale: 1 });
      // 幅に合わせるときは、余白を引いた表示幅から倍率を出す
      const s = scale || Math.max(0.1, (view.clientWidth - 28) / base.width);
      const vp = page.getViewport({ scale: s });
      const canvas = document.createElement('canvas');
      canvas.width = Math.floor(vp.width * dpr);
      canvas.height = Math.floor(vp.height * dpr);
      canvas.style.width = Math.floor(vp.width) + 'px';
      canvas.style.height = Math.floor(vp.height) + 'px';
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      await page.render({ canvasContext: ctx, viewport: vp }).promise;
      frag.appendChild(canvas);
    }
    host.replaceChildren(frag);
    pagesLabel.textContent = doc.numPages + 'p';
    restore(keep);
    message.classList.remove('on');
  } catch (e) {
    show_error(String(e && e.message ? e.message : e));
  } finally {
    rendering = false;
    if (pending) { const b = pending; pending = null; render(b); }
  }
}

function show_error(text) {
  message.textContent = text;
  message.classList.add('on');
}

function rescale(next) {
  scale = next;
  if (bytes) { render(bytes); }
}

document.getElementById('in').onclick = () => rescale((scale || 1) * 1.25);
document.getElementById('out').onclick = () => rescale((scale || 1) / 1.25);
document.getElementById('fit').onclick = () => rescale(0);

let resizeAt = 0;
window.addEventListener('resize', () => {
  if (scale !== 0) return;                    // 倍率を決めているなら追わない
  clearTimeout(resizeAt);
  resizeAt = setTimeout(() => rescale(0), 250);
});

window.addEventListener('message', (ev) => {
  const m = ev.data;
  if (!m) return;
  if (m.type === 'pdf') {
    label.textContent = m.label || '';
    render(b64(m.data));
  } else if (m.type === 'error') {
    show_error(m.message || '');
  } else if (m.type === 'busy') {
    bar.classList.toggle('busy', !!m.on);
  } else if (m.type === 'stale') {
    staleText.textContent = m.text || '';
    staleRun.textContent = m.button || '';
    staleBar.classList.toggle('on', !!m.text);
  }
});

vscode.postMessage({ type: 'ready' });
