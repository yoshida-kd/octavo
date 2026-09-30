// scaffold.ts — プロジェクトを作る（octavo init）・中身を足す（octavo new）画面。
//
// 何ができたか・どのファイルを開くかは `octavo new --json` が返す（パスをここで
// 組み立てない。置き場所の決まりは CLI の scaffold.py だけが知っている）。
import * as vscode from 'vscode';
import { dirOf, findConfig, resolvePathFromTool, runCapture, runInTerminal } from './runner';
import { TableEditorProvider } from './tableEditor';

/** octavo new --json が返すもの。 */
export interface NewReport {
    ok: boolean;
    error: string | null;
    open: string | null;
    made: string[];
}

type Kind = 'analysis' | 'paper' | 'slides' | 'lecture' | 'figure' | 'table';

const NAME_OK = /^[^\s/\\.][^\s/\\]*$/;

function kindItems(): (vscode.QuickPickItem & { part: Kind })[] {
    return [
        { part: 'paper', label: '$(book) ' + vscode.l10n.t('Paper'),
          description: 'papers/<name>/paper.md' },
        { part: 'slides', label: '$(vm) ' + vscode.l10n.t('Talk slides'),
          description: 'slides/<name>.md' },
        { part: 'lecture', label: '$(mortar-board) ' + vscode.l10n.t('Lecture notes'),
          description: vscode.l10n.t('lectures/<name>.md — an A4 handout + a deck per session') },
        { part: 'analysis', label: '$(graph) ' + vscode.l10n.t('Analysis (.qmd)'),
          description: vscode.l10n.t('analysis/<name>.qmd — data/ and the rest come with the first one') },
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

/** 新しいプロジェクト。何を最初に置くかを選ばせる（何も選ばなければ枠だけ）。 */
export async function initProject(): Promise<void> {
    const parents = await vscode.window.showOpenDialog({
        canSelectFiles: false, canSelectFolders: true, canSelectMany: false,
        openLabel: vscode.l10n.t('Create it here'),
        defaultUri: vscode.workspace.workspaceFolders?.[0]?.uri,
    });
    if (!parents || parents.length === 0) return;

    const name = await vscode.window.showInputBox({
        title: vscode.l10n.t('Project name (becomes the folder name)'),
        placeHolder: vscode.l10n.t('e.g. 2026-example-lecture'),
        validateInput: (v) => (v.trim() ? undefined : vscode.l10n.t('It cannot be empty')),
    });
    if (!name) return;

    const lang = await vscode.window.showQuickPick(
        [{ label: 'ja', value: 'ja' }, { label: 'en', value: 'en' }],
        { title: vscode.l10n.t('Main language') });
    if (!lang) return;

    // 最初に置くもの。どれも後から「足す」でいくらでも足せる
    const parts = await vscode.window.showQuickPick(
        kindItems().filter((k) => k.part !== 'figure' && k.part !== 'table')
            .sort((a, b) => (a.part === 'analysis' ? -1 : b.part === 'analysis' ? 1 : 0)),
        { canPickMany: true,
          title: vscode.l10n.t('What to start with (pick none for just the frame; anything can be added later)') });
    if (!parts) return;

    // 名前は部品の名前を入れておく（Enter でそのまま）
    const named: string[] = [];
    for (const p of parts) {
        const n = await askName(p.part, p.part);
        if (!n) return;
        named.push(n === p.part ? p.part : `${p.part}=${n}`);
    }

    // 既定は骨組み。見本は後で消すものなので、選んだときだけ
    const contents = await vscode.window.showQuickPick(
        [{ label: vscode.l10n.t('Empty'),
           description: vscode.l10n.t('only what you keep using'), example: false },
         { label: vscode.l10n.t('With examples'),
           description: parts.length
               ? vscode.l10n.t('each one as an example (fake data), to look at')
               : vscode.l10n.t('an analysis of made-up data and an example paper, to look at'),
           example: true }],
        { title: vscode.l10n.t('What to put in it') });
    if (!contents) return;

    const args = ['init', name, '--lang', lang.value];
    if (named.length) args.push('--with', named.join(','));
    if (contents.example) args.push('--example');
    runInTerminal('init', parents[0].fsPath, args);

    const open = await vscode.window.showInformationMessage(
        vscode.l10n.t('Made {0}. Anything else can be added from the Octavo sidebar. Open the folder?',
                      name),
        vscode.l10n.t('Open'), vscode.l10n.t('Later'));
    if (open === vscode.l10n.t('Open')) {
        await vscode.commands.executeCommand(
            'vscode.openFolder', vscode.Uri.joinPath(parents[0], name), false);
    }
}

/** 足すもの。'manuscript' は「原稿のどれか」（種類を選ばせる。分析と図は出さない）。 */
export type AddKind = Kind | 'manuscript';

export interface AddOptions {
    kind?: AddKind;
    name?: string;
    appendix?: boolean;
    tex?: boolean;
}

/** 原稿・分析・図を足す。何も渡さなければ種類・名前・オプションを尋ねる。
 *  足せたら開いて、true を返す（呼んだ側がサイドバーなどを読み直す）。 */
export async function addToProject(
    log: (s: string) => void, preset: AddOptions = {},
): Promise<boolean> {
    const configUri = await findConfig();
    if (!configUri) {
        void vscode.window.showWarningMessage(
            vscode.l10n.t('No octavo.config.py in this workspace. Make a project first.'));
        return false;
    }
    let kind: Kind;
    if (!preset.kind || preset.kind === 'manuscript') {
        const items = kindItems().filter(
            (k) => preset.kind !== 'manuscript'
                || (k.part !== 'analysis' && k.part !== 'figure' && k.part !== 'table'));
        const picked = await vscode.window.showQuickPick(items,
            { title: preset.kind === 'manuscript' ? vscode.l10n.t('What kind of manuscript?')
                                                  : vscode.l10n.t('What to add?') });
        if (!picked) return false;
        kind = picked.part;
    } else {
        kind = preset.kind;
    }
    const name = preset.name ?? await askName(kind);
    if (!name) return false;

    const flags: string[] = [];
    if (preset.appendix) flags.push('--appendix');
    if (preset.tex) flags.push('--tex');
    if (!preset.name && kind !== 'figure' && kind !== 'table') {
        // 新しく足すときだけオプションを尋ねる（付録・main.tex を後から足すときは不要）
        const opts: (vscode.QuickPickItem & { flag: string })[] = [
            { label: vscode.l10n.t('Make it an example'),
              description: vscode.l10n.t('with the example analysis and bibliography it uses'),
              flag: '--example' },
        ];
        if (kind === 'paper') {
            opts.push({ label: vscode.l10n.t('With an appendix'), description: 'appendix.md',
                        flag: '--appendix' },
                      { label: vscode.l10n.t('With main.tex, for LaTeX'), description: 'main.tex',
                        flag: '--tex' });
        }
        const chosen = await vscode.window.showQuickPick(opts, {
            canPickMany: true,
            title: vscode.l10n.t('Options (none: bare headings)'),
        });
        if (!chosen) return false;
        flags.push(...chosen.map((c) => c.flag));
    }

    const r = await runCapture(dirOf(configUri), ['new', kind, name, ...flags, '--json'], 60000);
    let report: NewReport | undefined;
    try {
        report = JSON.parse(r.stdout.trim().split('\n').pop() ?? '') as NewReport;
    } catch {
        report = undefined;
    }
    if (!report) {
        log(`[new] ${r.stderr.trim()}`);
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
    return true;
}
