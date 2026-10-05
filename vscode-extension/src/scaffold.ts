// scaffold.ts — プロジェクトを作る（octavo init）・中身を足す（octavo new）画面。
//
// 何ができたか・どのファイルを開くかは `octavo new --json` が返す（パスをここで
// 組み立てない。置き場所の決まりは CLI の scaffold.py だけが知っている）。
import * as vscode from 'vscode';
import { dirOf, findConfig, resolvePathFromTool, runCapture } from './runner';
import { showIfOldCli } from './setup';
import { TableEditorProvider } from './tableEditor';

/** octavo new --json が返すもの。 */
export interface NewReport {
    ok: boolean;
    error: string | null;
    open: string | null;
    made: string[];
    /** 分析を足したが、その環境（.venv、R なら renv）がまだない。 */
    env_needed?: boolean;
}

type Kind = 'analysis' | 'paper' | 'slides' | 'lecture' | 'poster' | 'figure' | 'table';

const NAME_OK = /^[^\s/\\.][^\s/\\]*$/;

type Engine = 'r' | 'python';

function kindItems(): (vscode.QuickPickItem & { part: Kind; engine?: Engine })[] {
    return [
        { part: 'paper', label: '$(book) ' + vscode.l10n.t('Paper'),
          description: vscode.l10n.t('docs/<name>/<name>.md — with main.typ, the journal layout') },
        { part: 'slides', label: '$(vm) ' + vscode.l10n.t('Talk slides'),
          description: 'docs/<name>/<name>.md' },
        { part: 'lecture', label: '$(mortar-board) ' + vscode.l10n.t('Lecture notes'),
          description: vscode.l10n.t('docs/<name>/<name>.md — an A4 handout + a deck per session') },
        { part: 'poster', label: '$(layout) ' + vscode.l10n.t('Poster'),
          description: vscode.l10n.t('docs/<name>/<name>.md — A0, the top-level headings make the cells') },
        { part: 'analysis', engine: 'r', label: '$(graph) ' + vscode.l10n.t('Analysis in R (.qmd)'),
          description: vscode.l10n.t('analysis/<name>.qmd — the first one also sets up the environment') },
        { part: 'analysis', engine: 'python', label: '$(symbol-method) ' + vscode.l10n.t('Analysis in Python (.qmd)'),
          description: vscode.l10n.t('analysis/<name>.qmd — the first one also sets up the environment') },
        { part: 'figure', label: '$(type-hierarchy) ' + vscode.l10n.t('Figure drawn in Typst'),
          description: vscode.l10n.t('figures/<name>.typ — boxes and arrows, where TikZ used to be') },
        { part: 'table', label: '$(table) ' + vscode.l10n.t('Table made by hand'),
          description: vscode.l10n.t('tables/<name>.csv — edited as a table; the manuscript places it with a caption line') },
    ];
}

function askName(kind: Kind, value?: string): Thenable<string | undefined> {
    const title = kind === 'analysis'
        ? vscode.l10n.t('Name of the analysis (becomes analysis/<name>.qmd)')
        : kind === 'figure'
        ? vscode.l10n.t('Name of the figure (becomes figures/<name>.typ; the manuscript refers to it as assets/figures/<name>.png)')
        : kind === 'table'
        ? vscode.l10n.t('Name of the table (becomes tables/<name>.csv; the manuscript places it with : Caption {#tbl-<name>})')
        : vscode.l10n.t('Document name (becomes the file or folder name; octavo build <name>)');
    return vscode.window.showInputBox({
        title,
        value,
        placeHolder: kind === 'analysis' ? 'model / 01-clean'
            : kind === 'figure' ? 'dag / flow'
            : kind === 'table' ? 'compare / sources'
            : vscode.l10n.t('e.g. example-paper / example-talk / example-lecture'),
        validateInput: (v) => (NAME_OK.test(v.trim()) ? undefined
            : vscode.l10n.t('No spaces, no / or \\, and it cannot start with a dot')),
    }).then((v) => v?.trim());
}

/** 足すもの。'manuscript' は「原稿のどれか」（種類を選ばせる。分析と図は出さない）。 */
export type AddKind = Kind | 'manuscript';

export interface AddOptions {
    kind?: AddKind;
    engine?: Engine;
    name?: string;
    appendix?: boolean;
    tex?: boolean;
}

/** 原稿・分析・図を足す。何も渡さなければ種類・名前・オプションを尋ねる。
 *  足せたら開いて、true を返す（呼んだ側がサイドバーなどを読み直す）。 */
export async function addToProject(
    log: (s: string) => void, preset: AddOptions = {},
    envSetup?: (cwd: string) => Promise<boolean>,
): Promise<boolean> {
    const configUri = await findConfig();
    if (!configUri) {
        void vscode.window.showWarningMessage(
            vscode.l10n.t('No octavo.config.py in this workspace. Make a project first.'));
        return false;
    }
    let kind: Kind;
    let engine: Engine | undefined = preset.engine;
    if (!preset.kind || preset.kind === 'manuscript') {
        const items = kindItems().filter(
            (k) => preset.kind !== 'manuscript'
                || (k.part !== 'analysis' && k.part !== 'figure' && k.part !== 'table'));
        const picked = await vscode.window.showQuickPick(items,
            { title: preset.kind === 'manuscript' ? vscode.l10n.t('What kind of manuscript?')
                                                  : vscode.l10n.t('What to add?') });
        if (!picked) return false;
        kind = picked.part;
        engine = picked.engine;
    } else {
        kind = preset.kind;
    }
    if (kind === 'analysis' && !engine) {
        // サイドバーの「分析を足す」から来たとき: R か Python かを聞く
        const e = await vscode.window.showQuickPick(
            kindItems().filter((k) => k.part === 'analysis'),
            { title: vscode.l10n.t('Which language is the analysis written in?') });
        if (!e) return false;
        engine = e.engine;
    }
    const name = preset.name ?? await askName(kind);
    if (!name) return false;

    const flags: string[] = [];
    if (preset.appendix) flags.push('--appendix');
    if (preset.tex) flags.push('--tex');
    if (kind === 'analysis' && engine === 'python') flags.push('--engine', 'python');
    const r = await runCapture(dirOf(configUri), ['new', kind, name, ...flags, '--json'], 60000);
    let report: NewReport | undefined;
    try {
        report = JSON.parse(r.stdout.trim().split('\n').pop() ?? '') as NewReport;
    } catch {
        report = undefined;
    }
    if (!report) {
        log(`[new] ${r.stderr.trim()}`);
        if (showIfOldCli(r.stderr)) {
            return false;
        }
        void vscode.window.showErrorMessage(
            r.stderr.trim() || vscode.l10n.t('Could not add {0}.', name));
        return false;
    }
    for (const m of report.made) {
        log(`[new] ${m}`);
    }
    if (!report.ok) {
        void vscode.window.showErrorMessage(report.error ?? vscode.l10n.t('Could not add {0}.', name));
        return false;
    }
    const uri = report.open ? resolvePathFromTool(report.open) : undefined;
    if (uri && kind === 'table') {
        // 手で作る表は、表の編集画面で開く（ふだんの .csv はテキストのまま。ボタンで切り替える）
        await vscode.commands.executeCommand('vscode.openWith', uri, TableEditorProvider.viewType);
    } else if (uri) {
        await vscode.window.showTextDocument(uri);
    }
    // 初めての分析なら、その環境（.venv、R なら renv）も整える。時間がかかるので、
    // 進捗は通知に出し、出力は出力パネルへ（`octavo env` を何度やっても同じ結果になる）
    if (report.env_needed && envSetup) {
        void envSetup(dirOf(configUri));
    }
    return true;
}
