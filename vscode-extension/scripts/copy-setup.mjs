// リポジトリ直下の setup.sh と setup.ps1（Windows 用）を setup/ に置く（.vsix に入る）。
// 拡張機能の「準備する」はこれを走らせるので、利用者は clone も pip も要らない。
// 中身は同じファイルを写すだけ（2つ持つと食い違う）。
import { mkdirSync, copyFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const to = join(root, 'setup');
mkdirSync(to, { recursive: true });
for (const name of ['setup.sh', 'setup.ps1']) {
  const from = join(root, '..', name);
  if (!existsSync(from)) {
    console.error(`${name} が無い（リポジトリの vscode-extension/ から走らせること）。`);
    process.exit(1);
  }
  copyFileSync(from, join(to, name));
  console.log(`copied ${name} -> setup/${name}`);
}
