// runner.ts — octavo CLI をどこで・どう実行するかを一箇所にまとめる。
//
// pandoc / LuaLaTeX / Typst は WSL か Linux サーバに入れる想定（README 参照）。
// VS Code 自体は素の Windows で動いていることが多いので、その場合は
// `wsl.exe` 越しに WSL 内の `octavo` を呼ぶ。Remote-WSL 拡張でウィンドウごと
// WSL の中に開いている場合は、拡張ホスト自体が Linux で動くので普通に
// 直接実行すればよい（`vscode.env.remoteName === 'wsl'` で判別できる）。
//
// Windows のパス（C:\Users\...）は wsl.exe に渡す前に /mnt/c/... に変換する。

import * as cp from 'child_process';
import * as path from 'path';
import * as vscode from 'vscode';

export type ExecutionMode = 'auto' | 'local' | 'wsl';

export interface RunResult {
    code: number | null;
    stdout: string;
    stderr: string;
}

function cfg() {
    return vscode.workspace.getConfiguration('octavo');
}

/** 'auto' を実際のモードに解決する。Remote-WSL の中では常に local 扱い。 */
export function resolveMode(): 'local' | 'wsl' {
    const mode = cfg().get<ExecutionMode>('executionMode', 'auto');
    if (mode !== 'auto') {
        return mode;
    }
    if (vscode.env.remoteName === 'wsl') {
        return 'local';
    }
    return process.platform === 'win32' ? 'wsl' : 'local';
}

/** `C:\Users\me\proj` -> `/mnt/c/Users/me/proj`（wsl.exe に渡すときだけ使う）。 */
export function toWslPath(winPath: string): string {
    const m = /^([A-Za-z]):[\\/](.*)$/.exec(winPath);
    if (!m) {
        // すでに /mnt/... や UNC でない相対パスなど。そのまま POSIX 区切りにするだけ。
        return winPath.replace(/\\/g, '/');
    }
    const drive = m[1].toLowerCase();
    const rest = m[2].replace(/\\/g, '/');
    return `/mnt/${drive}/${rest}`;
}

/** シェルに渡すための POSIX シングルクォート引用。 */
function shq(s: string): string {
    return `'${s.replace(/'/g, `'\\''`)}'`;
}

export interface Target {
    /** 作業ディレクトリ。ローカルなら Windows/POSIX パスそのまま、wsl なら変換前の Windows パス。 */
    cwd: string;
    /** その環境向けに変換済みの cwd（wsl モードなら /mnt/c/... 形式）。 */
    resolvedCwd: string;
    mode: 'local' | 'wsl';
}

export function resolveTarget(cwd: string): Target {
    const mode = resolveMode();
    return {
        cwd,
        resolvedCwd: mode === 'wsl' ? toWslPath(cwd) : cwd,
        mode,
    };
}

/**
 * ターミナルに貼り付けるコマンド文字列を組み立てる（build / watch / init など、対話的/長時間のもの向け）。
 * `commandOverride` を渡すと `octavo.command`（既定 `octavo`）の代わりにそのコマンドを使う
 * （例: `typst` を直接呼びたいとき）。
 */
export function buildShellCommand(cwd: string, args: string[], commandOverride?: string): string {
    const command = commandOverride || cfg().get<string>('command', 'octavo') || 'octavo';
    const target = resolveTarget(cwd);
    const argStr = args.map(shq).join(' ');

    if (target.mode === 'local') {
        return `cd ${shq(target.resolvedCwd)} && ${shq(command)} ${argStr}`;
    }

    const distro = cfg().get<string>('wslDistro', '') || '';
    const inner = `cd ${shq(target.resolvedCwd)} && ${shq(command)} ${argStr}`;
    const distroArgs = distro ? ` -d ${shq(distro)}` : '';
    return `wsl.exe${distroArgs} -e bash -lc ${shq(inner)}`;
}

/** 名前つきの共有ターミナルを使い回す。 */
const terminals = new Map<string, vscode.Terminal>();

export function runInTerminal(
    name: string, cwd: string, args: string[], reveal = true, commandOverride?: string,
): void {
    let term = terminals.get(name);
    if (!term || term.exitStatus !== undefined) {
        term = vscode.window.createTerminal({ name: `Octavo: ${name}` });
        terminals.set(name, term);
    }
    if (reveal) {
        term.show(true);
    }
    term.sendText(buildShellCommand(cwd, args, commandOverride));
}

/**
 * CLI に渡す表示の言語。**VS Code の表示言語に合わせる。**
 * Remote-SSH / wsl.exe 越しの子プロセスは ~/.bashrc を読まないので、
 * そこに書いた OCTAVO_LANG は効かず、サイドバーやプレビューのエラーが
 * VS Code と違う言語で出てしまう。ここで決めて渡す。
 */
function octavoLang(): string {
    return vscode.env.language.toLowerCase().startsWith('ja') ? 'ja' : 'en';
}

/** child_process で叩き、stdout を丸ごと回収する（JSON を読みたいときに使う）。 */
export function runCapture(cwd: string, args: string[], timeoutMs = 20000): Promise<RunResult> {
    const command = cfg().get<string>('command', 'octavo') || 'octavo';
    const target = resolveTarget(cwd);
    const execOpts = { timeout: timeoutMs, maxBuffer: 32 * 1024 * 1024,
                       env: { ...process.env, OCTAVO_LANG: octavoLang() } };

    return new Promise((resolve) => {
        // execFile のエラー型（ExecFileException）は code が number|string の
        // どちらもありうるので、ここでは緩く受けて RunResult.code に丸める。
        const done = (err: unknown, stdout: string, stderr: string): void => {
            const raw = (err as { code?: unknown } | null)?.code;
            const code = typeof raw === 'number' ? raw : (err ? 1 : 0);
            resolve({ code, stdout, stderr });
        };
        if (target.mode === 'local') {
            cp.execFile(command, args, { ...execOpts, cwd: target.resolvedCwd }, done);
        } else {
            const distro = cfg().get<string>('wslDistro', '') || '';
            const inner = `cd ${shq(target.resolvedCwd)} && OCTAVO_LANG=${octavoLang()} `
                + `${shq(command)} ${args.map(shq).join(' ')}`;
            const wslArgs = distro ? ['-d', distro, '-e', 'bash', '-lc', inner]
                                   : ['-e', 'bash', '-lc', inner];
            cp.execFile('wsl.exe', wslArgs, execOpts, done);
        }
    });
}

/**
 * 出力を流しながら実行する（分析のように長いもの向け）。終わったら終了コードを返す。
 * token で取り消すと子プロセスを止める（wsl.exe 越しのときは wsl.exe を止める）。
 */
export function runStreaming(cwd: string, args: string[], onText: (s: string) => void,
                             token?: vscode.CancellationToken): Promise<number | null> {
    const command = cfg().get<string>('command', 'octavo') || 'octavo';
    const target = resolveTarget(cwd);
    const env = { ...process.env, OCTAVO_LANG: octavoLang() };
    let child: cp.ChildProcess;
    if (target.mode === 'local') {
        child = cp.spawn(command, args, { cwd: target.resolvedCwd, env });
    } else {
        const distro = cfg().get<string>('wslDistro', '') || '';
        const inner = `cd ${shq(target.resolvedCwd)} && OCTAVO_LANG=${octavoLang()} `
            + `${shq(command)} ${args.map(shq).join(' ')}`;
        child = cp.spawn('wsl.exe', distro ? ['-d', distro, '-e', 'bash', '-lc', inner]
                                           : ['-e', 'bash', '-lc', inner], { env });
    }
    child.stdout?.on('data', (b: Buffer) => onText(b.toString()));
    child.stderr?.on('data', (b: Buffer) => onText(b.toString()));
    const cancel = token?.onCancellationRequested(() => child.kill());
    return new Promise((resolve) => {
        child.on('error', (e) => { onText(`${e.message}\n`); cancel?.dispose(); resolve(null); });
        child.on('close', (code) => { cancel?.dispose(); resolve(code); });
    });
}

/** octavo.config.py をワークスペース内から探す（設定で明示されていればそれを優先）。 */
export async function findConfig(): Promise<vscode.Uri | undefined> {
    const explicit = cfg().get<string>('configPath', '');
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
        return undefined;
    }
    if (explicit) {
        return vscode.Uri.joinPath(folders[0].uri, explicit);
    }
    const hits = await vscode.workspace.findFiles('**/octavo.config.py',
        '**/{node_modules,build,.git}/**', 5);
    if (hits.length === 0) {
        return undefined;
    }
    // ルートに近いものを優先する。
    hits.sort((a, b) => a.fsPath.split(path.sep).length - b.fsPath.split(path.sep).length);
    return hits[0];
}

export function dirOf(uri: vscode.Uri): string {
    return path.dirname(uri.fsPath);
}

/** `/mnt/c/Users/...` -> `C:\Users\...`。/mnt/<drive>/ 形式でなければ undefined。 */
export function fromWslPath(p: string): string | undefined {
    const m = /^\/mnt\/([a-z])\/(.*)$/i.exec(p);
    if (!m) {
        return undefined;
    }
    return `${m[1].toUpperCase()}:\\${m[2].replace(/\//g, '\\')}`;
}

/**
 * `octavo` の出力に出てくるパス（実行環境側の絶対パス）を、VS Code が
 * `vscode.Uri.file()` で開ける形に変換する。
 *
 * - local モード（Remote-WSL の中、または素の Linux/Mac）: そのまま使える
 * - wsl モード（Windows の VS Code から wsl.exe 越し）: `/mnt/c/...` は
 *   `C:\...` に戻せる。WSL のホーム以下など `/mnt/` の外は Windows 側から
 *   直接は触れないので undefined を返す（呼び出し側はそのパスに対する
 *   診断表示を諦めてよい — エディタで開いているドキュメント自体への
 *   診断には影響しない）。
 */
export function resolvePathFromTool(toolPath: string): vscode.Uri | undefined {
    if (resolveMode() === 'local') {
        return vscode.Uri.file(toolPath);
    }
    const win = fromWslPath(toolPath);
    return win ? vscode.Uri.file(win) : undefined;
}

/** wsl.exe の中で1行のコマンドを走らせて標準出力を取る（octavo 以外を呼ぶとき）。 */
function runInWsl(inner: string, timeoutMs: number): Promise<RunResult> {
    const distro = cfg().get<string>('wslDistro', '') || '';
    const args = distro ? ['-d', distro, '-e', 'bash', '-lc', inner]
                        : ['-e', 'bash', '-lc', inner];
    return new Promise((resolve) => {
        cp.execFile('wsl.exe', args, { timeout: timeoutMs, maxBuffer: 64 * 1024 * 1024 },
            (err, stdout, stderr) => resolve({ code: err ? 1 : 0, stdout, stderr }));
    });
}

/**
 * `octavo` が作ったファイルの中身を読む（プレビューが PDF を読むのに使う）。
 *
 * Windows の VS Code から wsl.exe 越しに動かしていて、しかも出力が `/mnt/`
 * の外（WSL のホーム以下など）にあると、Windows 側から直接は開けない。
 * その場合だけ `base64` で持ってくる。ふだんは普通にファイルを読む。
 */
export async function readToolFile(p: string): Promise<Uint8Array | undefined> {
    const uri = resolvePathFromTool(p);
    if (uri) {
        try {
            return await vscode.workspace.fs.readFile(uri);
        } catch {
            return undefined;
        }
    }
    const r = await runInWsl(`base64 -w0 ${shq(p)}`, 60000);
    if (r.code !== 0 || !r.stdout.trim()) {
        return undefined;
    }
    return new Uint8Array(Buffer.from(r.stdout.trim(), 'base64'));
}

export function describeMode(): string {
    const mode = resolveMode();
    if (mode === 'local') {
        return vscode.env.remoteName === 'wsl'
            ? vscode.l10n.t('directly inside WSL')
            : vscode.l10n.t('directly on this machine');
    }
    const distro = cfg().get<string>('wslDistro', '');
    return distro
        ? vscode.l10n.t('through wsl.exe ({0})', distro)
        : vscode.l10n.t('through wsl.exe');
}
