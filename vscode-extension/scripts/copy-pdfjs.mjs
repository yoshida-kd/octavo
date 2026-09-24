// pdf.js を media/pdfjs/ に置く。npm の devDependency から**コピーする**ので、
// ビルド済みの 1.5MB をリポジトリに入れずに済む（.vsix には入る）。
// vscode:prepublish から走るので、vsce package すれば必ず揃う。
import { mkdirSync, copyFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const from = join(root, 'node_modules', 'pdfjs-dist', 'legacy', 'build');
const to = join(root, 'media', 'pdfjs');

if (!existsSync(from)) {
  console.error('pdfjs-dist が無い。npm ci してから。');
  process.exit(1);
}
mkdirSync(to, { recursive: true });
// **.js に置き換えて**置く。webview はファイルを拡張子で配るので、.mjs だと
// JavaScript として配られないことがある。module かどうかは <script type=module>
// と import 側が決めるので、拡張子が .js でも module として読める。
for (const [f, as] of [['pdf.min.mjs', 'pdf.min.js'],
                       ['pdf.worker.min.mjs', 'pdf.worker.min.js']]) {
  copyFileSync(join(from, f), join(to, as));
  console.log('copied', f, '->', as);
}
