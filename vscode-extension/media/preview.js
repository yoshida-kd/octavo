// Octavo のプレビューの中身。pdf.js でページを canvas に描き、その上に
// 文字の層（選択・コピーできる。pdf.js の text layer）とリンクの層（目次・相互参照・
// URL）を重ねる。しおり（PDF のアウトライン）は ☰ から開く。
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
const staleMark = document.getElementById('stale-mark');
const staleClose = document.getElementById('stale-close');
staleRun.onclick = () => vscode.postMessage({ type: 'runAnalysis' });
staleMark.onclick = () => vscode.postMessage({ type: 'markFresh' });
staleClose.onclick = () => vscode.postMessage({ type: 'dismissStale' });

let scale = 0;            // 0 = 幅に合わせる
let doc = null;
let bytes = null;         // 最後に受け取った PDF（倍率を変えるとき描き直す）
let rendering = false;
let pending = null;       // 描いている最中に次の PDF が来たとき
let follow = true;        // 原稿のカーソルにスクロールを合わせるか（拡張機能が決める）
let pendingSync = null;   // 描いている最中に来た「ここへ」（描き終えてから合わせる）
const followBtn = document.getElementById('follow');
followBtn.onclick = () => vscode.postMessage({ type: 'toggleFollow' });

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

let pageBoxes = [];        // 描いたページの div（リンク先へ飛ぶときに使う）
let viewports = [];

// ページ内の点（PDF の座標）を、プレビューの縦位置にする
function scrollToPoint(index, x, y) {
  const box = pageBoxes[index];
  if (!box) return;
  let top = box.offsetTop - 8;
  if (typeof y === 'number' && viewports[index]) {
    top += viewports[index].convertToViewportPoint(x || 0, y)[1];
  }
  view.scrollTop = Math.max(0, top);
}

// PDF の行き先（名前か配列）へ飛ぶ
async function goTo(dest) {
  if (!doc || !dest) return;
  try {
    const explicit = typeof dest === 'string' ? await doc.getDestination(dest) : dest;
    if (!Array.isArray(explicit)) return;
    const ref = explicit[0];
    const index = typeof ref === 'number' ? ref : await doc.getPageIndex(ref);
    // [ref, {name: 'XYZ'}, left, top, zoom] のときだけ位置まで合わせる
    const kind = explicit[1] && explicit[1].name;
    if (kind === 'XYZ') scrollToPoint(index, explicit[2], explicit[3]);
    else scrollToPoint(index);
  } catch (e) { /* 行き先が読めなければ何もしない */ }
}

// リンクの層: 注釈のうちリンクだけを、透明な <a> にして重ねる
async function linkLayer(page, vp) {
  const layer = document.createElement('div');
  layer.className = 'linkLayer';
  let annots = [];
  try { annots = await page.getAnnotations({ intent: 'display' }); } catch (e) { return layer; }
  for (const a of annots) {
    if (a.subtype !== 'Link') continue;
    const [x1, y1, x2, y2] = vp.convertToViewportRectangle(a.rect);
    const el = document.createElement('a');
    el.style.left = Math.min(x1, x2) + 'px';
    el.style.top = Math.min(y1, y2) + 'px';
    el.style.width = Math.abs(x2 - x1) + 'px';
    el.style.height = Math.abs(y2 - y1) + 'px';
    if (a.url) {
      el.href = a.url;
      el.title = a.url;
      el.onclick = (ev) => { ev.preventDefault(); vscode.postMessage({ type: 'open', url: a.url }); };
    } else if (a.dest) {
      el.href = '#';
      el.onclick = (ev) => { ev.preventDefault(); goTo(a.dest); };
    } else {
      continue;
    }
    layer.appendChild(el);
  }
  return layer;
}

// 文字の層: pdf.js が文字の位置に透明な span を並べる（選択・コピー用）
async function textLayer(page, vp, layer) {
  layer.className = 'textLayer';
  layer.style.setProperty('--scale-factor', vp.scale);
  try {
    // ストリームではなく、まとめて取る形（ワーカーなしで動くときもこれなら止まらない）
    const content = await page.getTextContent({ includeMarkedContent: true });
    await pdfjs.renderTextLayer({ textContentSource: content, container: layer,
                                  viewport: vp, textDivs: [] }).promise;
  } catch (e) { /* 文字の層が作れなくても絵は出す */ }
}

// 文字とリンクの層は、ページを見せた**あとで**足す。層づくりで何か詰まっても、
// PDF そのものは必ず出る（層を待ってから見せると、詰まったときに何も出ない）
async function addLayers(items, doc0) {
  for (const { page, vp, box } of items) {
    if (doc !== doc0) return;                 // 次の PDF が来たら、古い層は作らない
    const text = document.createElement('div');
    box.appendChild(text);
    await textLayer(page, vp, text);
    try { box.appendChild(await linkLayer(page, vp)); } catch (e) { /* リンクなしで続ける */ }
  }
}

// しおり（アウトライン）
const outlineBox = document.getElementById('outline');
document.getElementById('toc').onclick = () => outlineBox.classList.toggle('on');
async function buildOutline() {
  outlineBox.replaceChildren();
  let items = null;
  try { items = await doc.getOutline(); } catch (e) { items = null; }
  document.getElementById('toc').style.display = items && items.length ? '' : 'none';
  const add = (list, depth) => {
    for (const it of list || []) {
      const b = document.createElement('button');
      b.textContent = it.title;
      b.style.paddingLeft = (8 + depth * 14) + 'px';
      b.onclick = () => { outlineBox.classList.remove('on'); goTo(it.dest); };
      outlineBox.appendChild(b);
      add(it.items, depth + 1);
    }
  };
  add(items, 0);
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
    const boxes = [];
    const vps = [];
    const layers = [];
    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      const base = page.getViewport({ scale: 1 });
      // 幅に合わせるときは、余白を引いた表示幅から倍率を出す
      const s = scale || Math.max(0.1, (view.clientWidth - 28) / base.width);
      const vp = page.getViewport({ scale: s });
      const box = document.createElement('div');
      box.className = 'page';
      box.style.width = Math.floor(vp.width) + 'px';
      box.style.height = Math.floor(vp.height) + 'px';
      const canvas = document.createElement('canvas');
      canvas.width = Math.floor(vp.width * dpr);
      canvas.height = Math.floor(vp.height * dpr);
      canvas.style.width = Math.floor(vp.width) + 'px';
      canvas.style.height = Math.floor(vp.height) + 'px';
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      await page.render({ canvasContext: ctx, viewport: vp }).promise;
      box.appendChild(canvas);
      layers.push({ page, vp, box });
      frag.appendChild(box);
      boxes.push(box);
      vps.push(vp);
    }
    host.replaceChildren(frag);
    pageBoxes = boxes;
    viewports = vps;
    pagesLabel.textContent = doc.numPages + 'p';
    restore(keep);
    textIndex = null;
    message.classList.remove('on');
    addLayers(layers, doc);
    buildOutline();
  } catch (e) {
    show_error(String(e && e.message ? e.message : e));
  } finally {
    rendering = false;
    if (pending) { const b = pending; pending = null; render(b); }
    else if (pendingSync) { const m = pendingSync; pendingSync = null; applySync(m); }
  }
}

// ---- 原稿のカーソルに合わせてスクロールする（forward sync）
// SyncTeX のような「原稿の行 → PDF の位置」の対応表は Typst にないので、文字で探す:
// 原稿のその行の頭の十数文字（と、見つからなければ直前の見出し）を PDF の文字の中から
// 探し、同じ文が何か所かあるときは、原稿の位置の割合に近いものを取る。
// どれも見つからなければ、割合だけで合わせる（見出しも文もない行、まだ保存していない行）。
let textIndex = null;

function normalize(s) {
  return s.normalize('NFKC').replace(/\s+/g, '').toLowerCase();
}

// ページごとに、文字を1本につないだもの（空白なし）と、各断片の始まりと縦位置
async function indexText(d) {
  if (textIndex && textIndex.doc === d) return textIndex;
  const pages = [];
  for (let n = 1; n <= d.numPages; n++) {
    const page = await d.getPage(n);
    const h = page.getViewport({ scale: 1 }).height;
    let content;
    try { content = await page.getTextContent(); } catch (e) { content = { items: [] }; }
    let text = '';
    const spans = [];
    for (const it of content.items) {
      const t = normalize(it.str || '');
      if (!t) continue;
      spans.push({ start: text.length, y: it.transform[5] });
      text += t;
    }
    pages.push({ text, spans, h });
  }
  textIndex = { doc: d, pages };
  return textIndex;
}

function spanAt(spans, at) {
  let lo = 0, hi = spans.length - 1, found = spans[0];
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (spans[mid].start <= at) { found = spans[mid]; lo = mid + 1; } else hi = mid - 1;
  }
  return found;
}

function findText(idx, needle, ratio) {
  let best = null;
  idx.pages.forEach((p, pi) => {
    let at = -1;
    while ((at = p.text.indexOf(needle, at + 1)) >= 0 && p.spans.length) {
      const span = spanAt(p.spans, at);
      const frac = (pi + (1 - span.y / p.h)) / idx.pages.length;
      const d = Math.abs(frac - ratio);
      if (!best || d < best.d) best = { page: pi, y: span.y, d };
    }
  });
  return best;
}

async function applySync(m) {
  if (!follow || !doc) return;
  const d0 = doc;
  const idx = await indexText(d0);
  if (doc !== d0) return;
  const ratio = Math.min(1, Math.max(0, m.ratio || 0));
  let hit = null;
  for (const raw of m.needles || []) {
    const needle = normalize(raw);
    if (needle.length < 3) continue;
    hit = findText(idx, needle, ratio);
    if (hit) break;
  }
  let top;
  if (hit && viewports[hit.page] && pageBoxes[hit.page]) {
    top = pageBoxes[hit.page].offsetTop + viewports[hit.page].convertToViewportPoint(0, hit.y)[1];
  } else {
    // 割合だけで合わせる
    top = ratio * (view.scrollHeight - view.clientHeight) + view.clientHeight * 0.3;
  }
  // すでに見える位置（上から 12%〜80%）なら動かさない。1行打つたびに画面が揺れないように
  const rel = top - view.scrollTop;
  if (rel < view.clientHeight * 0.12 || rel > view.clientHeight * 0.8) {
    view.scrollTop = Math.max(0, top - view.clientHeight * 0.3);
  }
}

function setFollow(on) {
  follow = !!on;
  followBtn.classList.toggle('on', follow);
}
setFollow(true);

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
  } else if (m.type === 'follow') {
    setFollow(m.on);
  } else if (m.type === 'sync') {
    if (rendering || !doc) pendingSync = m; else applySync(m);
  } else if (m.type === 'stale') {
    staleText.textContent = m.text || '';
    staleRun.textContent = m.button || '';
    staleMark.textContent = m.mark || '';
    staleMark.title = m.markTitle || '';
    staleClose.title = m.close || '';
    staleBar.classList.toggle('on', !!m.text);
  }
});

vscode.postMessage({ type: 'ready' });
