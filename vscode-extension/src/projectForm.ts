// projectForm.ts — 「新しいプロジェクト」を1画面で作る。
//
// 場所・名前・言語・最初に置くもの（分析は R か Python か）・見本にするかを1枚の
// フォームで決めて、`octavo init` を1回だけ呼ぶ。何がどこに作られるかの決まりは CLI
// （scaffold.py）が持っていて、フォームに出す「作られるもの」の一覧は目安にすぎない。
// 分析を選んだときは、そのまま `octavo env` で環境（.venv、R なら renv）まで整える。
import * as os from 'os';
import * as vscode from 'vscode';
import { findConfig, runStreaming } from './runner';
import { oldCliMessage } from './setup';

export interface ProjectFormDeps {
    log: (s: string) => void;
    /** 分析の環境を整える（進捗の通知つき）。 */
    envSetup: (cwd: string) => Promise<boolean>;
    /** 開いているフォルダにプロジェクトを作ったあと（一覧などを読み直す）。 */
    afterCreate: () => void;
}

interface CreateData {
    mode: 'new' | 'here';
    where: string;
    name: string;
    lang: 'ja' | 'en';
    engine: 'r' | 'python';
    parts: { kind: string; name: string }[];
    example: boolean;
}

const esc = (s: string): string => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;')
    .replace(/</g, '&lt;');

let current: vscode.WebviewPanel | undefined;

export async function showProjectForm(
    context: vscode.ExtensionContext, deps: ProjectFormDeps,
): Promise<void> {
    if (current) {
        current.reveal();
        return;
    }
    const folder = vscode.workspace.workspaceFolders?.[0];
    const inProject = (await findConfig()) !== undefined;
    // 開いているフォルダがまだ Octavo のプロジェクトでなければ、そこに作るのを既定にする
    const canUseHere = folder !== undefined && !inProject;

    const media = vscode.Uri.joinPath(context.extensionUri, 'media');
    const panel = vscode.window.createWebviewPanel(
        'octavo.projectForm', vscode.l10n.t('New Octavo project'), vscode.ViewColumn.Active,
        { enableScripts: true, localResourceRoots: [media] });
    current = panel;
    panel.onDidDispose(() => { current = undefined; });
    panel.webview.html = html(panel.webview, media, {
        canUseHere, workspaceName: folder?.name ?? '',
        where: folder?.uri.fsPath ?? os.homedir(),
    });

    panel.webview.onDidReceiveMessage(async (m: { type: string; data?: CreateData }) => {
        if (m.type === 'browse') {
            const picked = await vscode.window.showOpenDialog({
                canSelectFiles: false, canSelectFolders: true, canSelectMany: false,
                openLabel: vscode.l10n.t('Create it here'), defaultUri: folder?.uri,
            });
            if (picked?.[0]) {
                void panel.webview.postMessage({ type: 'where', path: picked[0].fsPath });
            }
        } else if (m.type === 'cancel') {
            panel.dispose();
        } else if (m.type === 'create' && m.data) {
            const failed = await create(m.data, folder, deps);
            if (failed) {
                void panel.webview.postMessage({ type: 'failed', message: failed });
            } else {
                panel.dispose();
            }
        }
    });
}

/** 作る。失敗したら画面に出す文を返す（成功は undefined）。 */
async function create(
    d: CreateData, folder: vscode.WorkspaceFolder | undefined, deps: ProjectFormDeps,
): Promise<string | undefined> {
    const here = d.mode === 'here';
    if (here && !folder) {
        return vscode.l10n.t('No folder is open.');
    }
    const cwd = here ? folder!.uri.fsPath : d.where;
    const target = here ? '.' : d.name;
    const args = ['init', target, '--lang', d.lang];
    if (d.parts.length) {
        args.push('--with', d.parts.map((p) => (p.name === p.kind ? p.kind : `${p.kind}=${p.name}`))
            .join(','));
    }
    if (d.parts.some((p) => p.kind === 'analysis') && d.engine === 'python') {
        args.push('--engine', 'python');
    }
    if (d.example) {
        args.push('--example');
    }

    let text = '';
    deps.log(`\n== octavo ${args.join(' ')}`);
    const code = await runStreaming(cwd, args, (s) => {
        text += s;
        deps.log(s.replace(/\n$/, ''));
    });
    if (code !== 0) {
        return oldCliMessage(text)
            ?? (text.trim().split('\n').slice(-6).join('\n')
                || vscode.l10n.t('Could not make the project.'));
    }

    const dest = here ? folder!.uri : vscode.Uri.joinPath(vscode.Uri.file(d.where), d.name);
    // 分析を選んだら、環境（.venv、R なら renv）もそのまま整える。失敗しても
    // プロジェクトはできているので、通知に任せて先へ進む（あとで「env」で何度でもやり直せる）
    if (d.parts.some((p) => p.kind === 'analysis')) {
        await deps.envSetup(dest.fsPath);
    }
    if (here) {
        deps.afterCreate();
    } else {
        await vscode.commands.executeCommand('vscode.openFolder', dest, false);
    }
    return undefined;
}

interface FormInit {
    canUseHere: boolean;
    workspaceName: string;
    where: string;
}

function html(w: vscode.Webview, media: vscode.Uri, init: FormInit): string {
    const nonce = Array.from({ length: 32 },
        () => 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[
            Math.floor(Math.random() * 62)]).join('');
    const uri = (f: string): vscode.Uri => w.asWebviewUri(vscode.Uri.joinPath(media, f));
    const csp = [`default-src 'none'`, `style-src ${w.cspSource}`,
                 `script-src 'nonce-${nonce}'`].join('; ');
    const words = {
        workspaceName: init.workspaceName,
        nameWord: vscode.l10n.t('name'),
        create: vscode.l10n.t('Create the project'),
        working: vscode.l10n.t('Creating…'),
        fix: vscode.l10n.t('Fill in the red fields (no spaces, no / or \\, and not starting with a dot).'),
        envNote: vscode.l10n.t('The analysis environment (.venv, and renv for R) is set up right after. The first time it takes a few minutes.'),
    };
    const part = (id: string, label: string, goes: string, extra = ''): string => `
  <div class="part off" id="part-${id}">
    <div class="head">
      <input type="checkbox" id="use-${id}"><label for="use-${id}"><b>${esc(label)}</b></label>
      <span class="where-it-goes">${esc(goes)}</span>
    </div>
    <div class="detail">
      <span class="lab">${esc(vscode.l10n.t('Name'))}</span>
      <input type="text" id="name-${id}" value="${id}" size="22">
      ${extra}
    </div>
  </div>`;
    const engine = `
      <span class="lab">${esc(vscode.l10n.t('Language'))}</span>
      <label><input type="radio" name="engine" value="r" checked> R</label>
      <label><input type="radio" name="engine" value="python"> Python</label>`;
    return `<!DOCTYPE html>
<html lang="${vscode.env.language}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<link rel="stylesheet" href="${uri('project.css')}">
</head>
<body data-words="${esc(JSON.stringify(words))}">
<h1>${esc(vscode.l10n.t('New Octavo project'))}</h1>
<p class="lead">${esc(vscode.l10n.t('Pick what you need now. Everything else can be added later from the Octavo sidebar.'))}</p>

<fieldset>
  <legend>${esc(vscode.l10n.t('Where'))}</legend>
  ${init.canUseHere ? `
  <div class="row">
    <label><input type="radio" name="mode" value="here" checked>
      ${esc(vscode.l10n.t('In the open folder ({0})', init.workspaceName))}</label>
  </div>
  <div class="row">
    <label><input type="radio" name="mode" value="new">
      ${esc(vscode.l10n.t('In a new folder'))}</label>
  </div>` : `<input type="radio" name="mode" value="new" checked hidden>`}
  <div class="row" id="where-row">
    <input type="text" id="where" readonly value="${esc(init.where)}">
    <button id="browse" type="button">${esc(vscode.l10n.t('Choose…'))}</button>
  </div>
  <div class="row" id="name-row">
    <span>${esc(vscode.l10n.t('Project name'))}</span>
    <input type="text" id="name" size="28" placeholder="${esc(vscode.l10n.t('e.g. 2026-example-lecture'))}">
  </div>
  <p class="hint">${esc(vscode.l10n.t('The name becomes the folder name.'))}</p>
</fieldset>

<fieldset>
  <legend>${esc(vscode.l10n.t('Language of the writing'))}</legend>
  <div class="row">
    <label><input type="radio" name="lang" value="ja" checked> 日本語</label>
    <label><input type="radio" name="lang" value="en"> English</label>
  </div>
</fieldset>

<fieldset>
  <legend>${esc(vscode.l10n.t('What to start with'))}</legend>
  ${part('analysis', vscode.l10n.t('Analysis'), 'analysis/<name>.qmd', engine)}
  ${part('paper', vscode.l10n.t('Paper'), 'docs/<name>/<name>.md')}
  ${part('slides', vscode.l10n.t('Talk slides'), 'docs/<name>/<name>.md')}
  ${part('lecture', vscode.l10n.t('Lecture notes'), 'docs/<name>/<name>.md')}
  ${part('poster', vscode.l10n.t('Poster'), 'docs/<name>/<name>.md')}
  <div class="row">
    <label><input type="checkbox" id="example">
      ${esc(vscode.l10n.t('Fill them with examples (made-up data), to look at'))}</label>
  </div>
</fieldset>

<fieldset>
  <legend>${esc(vscode.l10n.t('What will be made'))}</legend>
  <pre id="summary"></pre>
  <p id="note"></p>
</fieldset>

<div class="actions">
  <button id="create" class="primary" type="button">${esc(words.create)}</button>
  <button id="cancel" type="button">${esc(vscode.l10n.t('Cancel'))}</button>
</div>
<div id="error"></div>
<script nonce="${nonce}" src="${uri('project.js')}"></script>
</body>
</html>`;
}
