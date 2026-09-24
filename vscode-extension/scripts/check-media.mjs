// webview に渡す JavaScript を構文検査する。**実行はしない。**
// VS Code の中の挙動はどのテストも見ていないので、せめて「読めない JS を
// 配ってしまう」だけは防ぐ。node --check は .js を CommonJS として読むため、
// import と最上位 await が通るように .mjs に写してから掛ける。
import { copyFileSync, mkdtempSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tmp = mkdtempSync(join(tmpdir(), 'octavo-media-'));
for (const f of ['preview.js']) {
  const as = join(tmp, f.replace(/\.js$/, '.mjs'));
  copyFileSync(join(root, 'media', f), as);
  execFileSync(process.execPath, ['--check', as], { stdio: 'inherit' });
  console.log('checked', f);
}
