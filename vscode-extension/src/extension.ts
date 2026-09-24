// extension.ts — 入口。コマンド登録とプロバイダの配線だけをここに置く。
//
// 実際のロジックは:
//   runner.ts       octavo CLI をどこで・どう実行するか（WSL 越し／直接）
//   bib.ts          `octavo checkbib --json` のキャッシュ
//   citations.ts    @key の補完・ホバー・挿入
//   diagnostics.ts  無い引用キー・書誌の傷への警告
//   values.ts       `octavo values --json` のキャッシュ
//   valueui.ts      {{名前}} の補完・ホバー・未解決への警告

import * as path from 'path';
import * as vscode from 'vscode';
import { AnalysisUnit, fetchAnalysis, runAnalysisWithProgress } from './analysis';
import { BibCache } from './bib';
import { CitationCompletionProvider, CitationHoverProvider, insertCitationCommand } from './citations';
import { DiagnosticsManager } from './diagnostics';
import { PreviewManager } from './preview';
import { OctavoTree, Setting } from './sidebar';
import { describeMode, dirOf, findConfig, resolvePathFromTool, runInTerminal } from './runner';
import { ValuesCache } from './values';
import { ValueCompletionProvider, ValueDiagnostics, ValueHoverProvider } from './valueui';

/** LaTeX Workshop がPDFに登録しているカスタムエディタのviewType。
 *  公式APIではなく拡張機能側の内部実装なので、LaTeX Workshopの将来のバージョンで
 *  変わる可能性がある。失敗しても watch 自体は動き続けるので、失敗は静かに無視する。 */
const LATEX_WORKSHOP_PDF_VIEWTYPE = 'latex-workshop-pdf-hook';
const LATEX_WORKSHOP_EXTENSION_ID = 'james-yu.latex-workshop';

// octavo/config.py::BACKENDS と手で合わせる（自動生成ではない）。
// 翻訳を引くので定数ではなく関数にしてある。
function targetItems(): (vscode.QuickPickItem & { id: string })[] {
    return [
        { id: 'typst', label: '$(file-text) typst', description: vscode.l10n.t('Typst (needs pandoc 3.1+)') },
        { id: 'typst-slides', label: '$(device-camera) typst-slides', description: vscode.l10n.t('Talk and lecture slides (needs Typst 0.12+; a standalone .typ)') },
        { id: 'typst-notes', label: '$(note) typst-notes', description: vscode.l10n.t('The speaker script for a deck (A4, with ::: notes)') },
        { id: 'docx', label: '$(file-word) docx', description: 'Word' },
        { id: 'latex', label: '$(file-text) latex', description: vscode.l10n.t('LuaLaTeX (needs TeX; body.tex, or a standalone .tex for handouts)') },
        { id: 'beamer', label: '$(device-camera) beamer', description: vscode.l10n.t('Talk and lecture slides (needs TeX; a standalone .tex)') },
    ];
}

export function activate(context: vscode.ExtensionContext): void {
    const output = vscode.window.createOutputChannel('Octavo');
    const cache = new BibCache();
    const diagnostics = new DiagnosticsManager(cache);
    const valuesCache = new ValuesCache();
    const valueDiagnostics = new ValueDiagnostics(valuesCache);
    const preview = new PreviewManager(context, (line) => output.appendLine(line));
    const tree = new OctavoTree((line) => output.appendLine(line));
    context.subscriptions.push(valuesCache, valueDiagnostics, preview, tree,
        vscode.window.registerTreeDataProvider('octavo.project', tree));

    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.command = 'octavo.build';
    statusBar.text = '$(book) Octavo';
    statusBar.tooltip = vscode.l10n.t('Runs: {0}', describeMode());
    statusBar.show();

    const updateStatusBar = (): void => {
        const report = cache.current;
        if (!report) {
            statusBar.text = '$(book) Octavo';
            statusBar.backgroundColor = undefined;
            return;
        }
        if (report.missing.length > 0) {
            statusBar.text = '$(warning) ' +
                vscode.l10n.t('Octavo: {0} references missing', report.missing.length);
            statusBar.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        } else {
            statusBar.text = '$(check) ' + vscode.l10n.t('Octavo: references OK');
            statusBar.backgroundColor = undefined;
        }
    };

    context.subscriptions.push(
        output,
        cache,
        diagnostics,
        statusBar,
        cache.onDidUpdate(() => updateStatusBar()),
        cache.onError((msg) => {
            output.appendLine(`[${vscode.l10n.t('error')}] ${msg}`);
        }),
    );

    // -- 新しく開いたマークダウンにも、すでにあるキャッシュから即座に反映する ---
    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument((doc) => {
            if (doc.languageId === 'markdown') {
                diagnostics.applyToMarkdown(doc, cache.current);
                valueDiagnostics.applyToMarkdown(doc, valuesCache.current);
            }
        }),
        vscode.workspace.onDidSaveTextDocument((doc) => {
            const isRelevant = doc.languageId === 'markdown' || doc.fileName.endsWith('.bib') ||
                doc.fileName.endsWith('octavo.config.py');
            if (isRelevant && vscode.workspace.getConfiguration('octavo')
                .get<boolean>('diagnosticsOnSave', true)) {
                void cache.refresh(true);
                void valuesCache.refresh(true);
            }
        }),
    );

    // -- IntelliSense ---------------------------------------------------
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            { language: 'markdown' }, new CitationCompletionProvider(cache), '@'),
        vscode.languages.registerHoverProvider(
            { language: 'markdown' }, new CitationHoverProvider(cache)),
        // `{` を打った時点で候補を出す（2つ目の `{` まで待つと遅い）
        vscode.languages.registerCompletionItemProvider(
            { language: 'markdown' }, new ValueCompletionProvider(valuesCache), '{'),
        vscode.languages.registerHoverProvider(
            { language: 'markdown' }, new ValueHoverProvider(valuesCache)),
    );

    // -- 補助関数 ---------------------------------------------------------
    let analysisRunning = false;
    async function runAnalysis(cwd: string, names: string[]): Promise<void> {
        if (analysisRunning) {
            void vscode.window.showInformationMessage(
                vscode.l10n.t('Octavo: the analysis is already running.'));
            return;
        }
        analysisRunning = true;
        try {
            await runAnalysisWithProgress(cwd, names, output);
        } finally {
            analysisRunning = false;
        }
        tree.refreshAnalysis();
        void valuesCache.refresh(true);
        await preview.rebuildIfOpen();
    }

    async function requireConfig(): Promise<vscode.Uri | undefined> {
        const configUri = await findConfig();
        if (!configUri) {
            const choice = await vscode.window.showWarningMessage(
                vscode.l10n.t('No octavo.config.py in this workspace.'),
                vscode.l10n.t('New project'), vscode.l10n.t('Cancel'));
            if (choice === vscode.l10n.t('New project')) {
                await vscode.commands.executeCommand('octavo.init');
            }
            return undefined;
        }
        return configUri;
    }

    async function pickTargets(): Promise<string[] | undefined> {
        const defaults = vscode.workspace.getConfiguration('octavo')
            .get<string[]>('defaultTargets', []);
        if (defaults && defaults.length > 0) {
            return defaults;
        }
        const picked = await vscode.window.showQuickPick(targetItems(), {
            title: vscode.l10n.t(
                'Pick the formats (several is fine; none means the configured default)'),
            canPickMany: true,
        });
        if (picked === undefined) {
            return undefined; // Esc でキャンセル
        }
        return picked.map((p) => p.id);
    }

    // -- コマンド ----------------------------------------------------------
    context.subscriptions.push(
        vscode.commands.registerCommand('octavo.build', async () => {
            const configUri = await requireConfig();
            if (!configUri) return;
            const targets = await pickTargets();
            if (targets === undefined) return;

            const docName = await vscode.window.showInputBox({
                title: vscode.l10n.t(
                    'Document name (empty builds every document in octavo.config.py)'),
                placeHolder: vscode.l10n.t(
                    'e.g. example-paper / example-talk / example-lecture / example-lecture-03'),
            });
            if (docName === undefined) return; // Esc

            const compilePick = await vscode.window.showQuickPick(
                [{ label: vscode.l10n.t('Convert only (default)'), value: false },
                 { label: vscode.l10n.t(
                     'Typeset as well (--compile; runs latexmk / typst compile)'), value: true }],
                { title: vscode.l10n.t('Typeset as well?') });
            if (compilePick === undefined) return;

            const args = ['build'];
            if (docName.trim()) args.push(docName.trim());
            if (targets.length > 0) args.push('--to', targets.join(','));
            if (compilePick.value) args.push('--compile');
            runInTerminal('build', dirOf(configUri), args);
        }),

        vscode.commands.registerCommand('octavo.buildAll', async () => {
            const configUri = await requireConfig();
            if (!configUri) return;
            runInTerminal('build', dirOf(configUri), ['build', '--to', 'all']);
        }),

        vscode.commands.registerCommand('octavo.watch', async () => {
            const configUri = await requireConfig();
            if (!configUri) return;
            const targets = await pickTargets();
            if (targets === undefined) return;
            const args = ['watch'];
            if (targets.length > 0) args.push('--to', targets.join(','));
            runInTerminal('watch', dirOf(configUri), args);
        }),

        // octavo.watch（原稿のMarkdownをmtime監視してpandocで作り直す）とは別物。
        // こちらは開いている .typ ファイル自体を typst の差分コンパイラで直接
        // watch する（octavo build を経由しない）。手で編集する main.typ の
        // プリアンブル調整などで使う想定。
        vscode.commands.registerCommand('octavo.watchTypstFile', async () => {
            const doc = vscode.window.activeTextEditor?.document;
            if (!doc || !doc.fileName.toLowerCase().endsWith('.typ')) {
                void vscode.window.showWarningMessage(
                    vscode.l10n.t(
                        'Octavo: open a .typ file in the active editor first.'));
                return;
            }
            const fileUri = doc.uri;
            const cwd = dirOf(fileUri);
            const fileName = path.basename(fileUri.fsPath);
            const typstCommand = vscode.workspace.getConfiguration('octavo')
                .get<string>('typstCommand', 'typst') || 'typst';
            runInTerminal('typst-watch', cwd, ['watch', fileName], true, typstCommand);

            const autoOpen = vscode.workspace.getConfiguration('octavo')
                .get<boolean>('typstAutoOpenPdf', true);
            if (!autoOpen) return;

            const pdfUri = vscode.Uri.file(fileUri.fsPath.replace(/\.typ$/i, '.pdf'));
            if (vscode.extensions.getExtension(LATEX_WORKSHOP_EXTENSION_ID)) {
                // 初回コンパイルがPDFを書き出すまで少し待つ。既に無くても
                // LaTeX Workshop 側のファイルウォッチャーが後から拾って表示する。
                setTimeout(() => {
                    void vscode.commands.executeCommand(
                        'vscode.openWith', pdfUri, LATEX_WORKSHOP_PDF_VIEWTYPE)
                        .then(undefined, () => { /* 失敗しても watch 自体は継続する */ });
                }, 1500);
            } else {
                const choice = await vscode.window.showInformationMessage(
                    vscode.l10n.t(
                        'Octavo: to watch the PDF refresh on every save, the LaTeX Workshop '
                        + 'extension (with its built-in PDF viewer) is handy.'),
                    vscode.l10n.t('Find the extension'), vscode.l10n.t('Not now'));
                if (choice === vscode.l10n.t('Find the extension')) {
                    void vscode.commands.executeCommand(
                        'workbench.extensions.search', LATEX_WORKSHOP_EXTENSION_ID);
                }
            }
        }),

        vscode.commands.registerCommand('octavo.preview', () => preview.open()),

        // -- アクティビティバー ------------------------------------------------
        vscode.commands.registerCommand('octavo.sidebarRefresh', () => tree.refresh()),
        vscode.commands.registerCommand('octavo.openConfig', () => tree.openConfig()),
        vscode.commands.registerCommand('octavo.editSetting', async (s: Setting) => {
            if (s && await tree.edit(s)) {
                await preview.rebuildIfOpen();      // 変えた結果がすぐ見えるように
            }
        }),
        vscode.commands.registerCommand('octavo.previewDoc', async (node: { doc?: { src: string } }) => {
            const uri = node?.doc ? resolvePathFromTool(node.doc.src) : undefined;
            if (!uri) return;
            await vscode.window.showTextDocument(uri, { viewColumn: vscode.ViewColumn.One });
            await preview.open();
        }),
        vscode.commands.registerCommand('octavo.buildDoc', async (node: { doc?: { name: string } }) => {
            const configUri = await requireConfig();
            if (!configUri || !node?.doc) return;
            runInTerminal('build', dirOf(configUri), ['build', node.doc.name, '--compile'], true);
        }),
        vscode.commands.registerCommand('octavo.check', async () => {
            const configUri = await requireConfig();
            if (!configUri) return;
            runInTerminal('check', dirOf(configUri), ['check'], true);
        }),
        // 分析はターミナルではなく、通知の進み具合＋出力パネルで走らせる。
        // 終わったことが分かるので、サイドバー・プレビュー・{{…}} の候補を更新できる。
        vscode.commands.registerCommand('octavo.analysisRun', async () => {
            const configUri = await requireConfig();
            if (!configUri) return;
            await runAnalysis(dirOf(configUri), []);
        }),
        // 1本だけ。サイドバーの行（node.u）、エディタの .qmd（Uri）、パレット（選ばせる）から。
        vscode.commands.registerCommand('octavo.analysisRunOne',
            async (arg?: { u?: AnalysisUnit } | vscode.Uri) => {
                const configUri = await requireConfig();
                if (!configUri) return;
                const cwd = dirOf(configUri);
                let name: string | undefined;
                if (arg instanceof vscode.Uri) {
                    const editor = vscode.window.visibleTextEditors.find(
                        (e) => e.document.uri.toString() === arg.toString());
                    if (editor?.document.isDirty) {
                        await editor.document.save();
                    }
                    name = path.relative(cwd, arg.fsPath).split(path.sep).join('/');
                } else if (arg && 'u' in arg && arg.u) {
                    name = arg.u.key;
                } else {
                    const report = await fetchAnalysis(cwd);
                    const units = report?.units.filter((u) => u.exists) ?? [];
                    if (!units.length) {
                        void vscode.window.showInformationMessage(
                            vscode.l10n.t('No analysis (.qmd) is registered.'));
                        return;
                    }
                    const picked = await vscode.window.showQuickPick(units.map((u) => ({
                        label: u.key,
                        description: (u.stale ? vscode.l10n.t('stale') : vscode.l10n.t('up to date'))
                            + (u.manual ? ` · ${vscode.l10n.t('manual')}` : ''),
                        key: u.key,
                    })), { title: vscode.l10n.t('Which analysis should run?') });
                    name = picked?.key;
                }
                if (name) {
                    await runAnalysis(cwd, [name]);
                }
            }),
        vscode.commands.registerCommand('octavo.previewColumn', () => preview.chooseSide()),
        vscode.commands.registerCommand('octavo.previewRefresh', () => preview.refresh()),

        vscode.commands.registerCommand('octavo.checkbib', async () => {
            const configUri = await requireConfig();
            if (!configUri) return;
            runInTerminal('checkbib', dirOf(configUri), ['checkbib'], true);
            const report = await cache.refresh(true);
            if (report) {
                const n = report.missing.length + report.problems.length;
                if (n === 0) {
                    void vscode.window.showInformationMessage(
                        vscode.l10n.t('Octavo: the bibliography looks fine.'));
                } else {
                    void vscode.window.showWarningMessage(
                        vscode.l10n.t(
                            'Octavo: {0} to look at ({1} citation keys not in the .bib). '
                            + 'Check the squiggles in the Markdown and the terminal output.',
                            n, report.missing.length));
                }
            }
        }),

        vscode.commands.registerCommand('octavo.doctor', async () => {
            const configUri = await findConfig();
            const cwd = configUri ? dirOf(configUri) :
                vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
            if (!cwd) {
                void vscode.window.showWarningMessage(
                    vscode.l10n.t('No workspace is open.'));
                return;
            }
            runInTerminal('doctor', cwd, ['doctor']);
        }),

        vscode.commands.registerCommand('octavo.selftest', async () => {
            const configUri = await findConfig();
            const cwd = configUri ? dirOf(configUri) :
                vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
            if (!cwd) {
                void vscode.window.showWarningMessage(
                    vscode.l10n.t('No workspace is open.'));
                return;
            }
            runInTerminal('selftest', cwd, ['selftest']);
        }),

        vscode.commands.registerCommand('octavo.init', async () => {
            const parents = await vscode.window.showOpenDialog({
                canSelectFiles: false, canSelectFolders: true, canSelectMany: false,
                openLabel: vscode.l10n.t('Create it here'),
                defaultUri: vscode.workspace.workspaceFolders?.[0]?.uri,
            });
            if (!parents || parents.length === 0) return;

            const name = await vscode.window.showInputBox({
                title: vscode.l10n.t('Project name (becomes the folder name)'),
                placeHolder: vscode.l10n.t('e.g. 2026-example-lecture'),
                validateInput: (v) => (v.trim() ? undefined
                    : vscode.l10n.t('It cannot be empty')),
            });
            if (!name) return;

            const lang = await vscode.window.showQuickPick(
                [{ label: 'ja', value: 'ja' }, { label: 'en', value: 'en' }],
                { title: vscode.l10n.t('Main language') });
            if (!lang) return;

            runInTerminal('init', parents[0].fsPath,
                ['init', name, '--lang', lang.value]);

            const open = await vscode.window.showInformationMessage(
                vscode.l10n.t(
                    'Made {0}. Add a manuscript with "Add a Manuscript". Open the folder?',
                    name),
                vscode.l10n.t('Open'), vscode.l10n.t('Later'));
            if (open === vscode.l10n.t('Open')) {
                const newUri = vscode.Uri.joinPath(parents[0], name);
                await vscode.commands.executeCommand('vscode.openFolder', newUri, false);
            }
        }),

        vscode.commands.registerCommand('octavo.new', async () => {
            const configUri = await requireConfig();
            if (!configUri) return;
            // 種類の違いは原稿のテンプレートだけ。どれも何本でも足せる
            const kind = await vscode.window.showQuickPick(
                [
                    { label: 'paper', description: vscode.l10n.t('A paper — papers/<name>/paper.md'), value: 'paper' },
                    { label: 'slides', description: vscode.l10n.t('Talk slides — slides/<name>.md'), value: 'slides' },
                    { label: 'lecture', description: vscode.l10n.t('Lecture notes (an A4 handout + a deck per session) — lectures/<name>.md'), value: 'lecture' },
                ],
                { title: vscode.l10n.t('What kind of manuscript?') });
            if (!kind) return;

            const name = await vscode.window.showInputBox({
                title: vscode.l10n.t(
                    'Document name (becomes the file or folder name; octavo build <name>)'),
                placeHolder: vscode.l10n.t('e.g. example-paper / example-talk / example-lecture'),
                validateInput: (v) => (/^[^\s/\\.][^\s/\\]*$/.test(v.trim())
                    ? undefined : vscode.l10n.t(
                        'No spaces, no / or \\, and it cannot start with a dot')),
            });
            if (!name) return;

            runInTerminal('new', dirOf(configUri), ['new', kind.value, name.trim()]);
        }),

        vscode.commands.registerCommand('octavo.bibPull', async () => {
            const configUri = await requireConfig();
            if (!configUri) return;
            const collection = await vscode.window.showInputBox({
                title: vscode.l10n.t(
                    'Zotero collection name (empty means the whole library)'),
            });
            if (collection === undefined) return;
            const args = ['bib', 'pull'];
            if (collection.trim()) args.push('--collection', collection.trim());
            runInTerminal('bib', dirOf(configUri), args);
            // 少し待ってからキャッシュを更新（Zotero からの取得は数秒かかることがある）。
            setTimeout(() => {
                void cache.refresh(true);
                void valuesCache.refresh(true);
            }, 4000);
        }),

        vscode.commands.registerCommand('octavo.insertCitation', () => insertCitationCommand(cache)),

        vscode.commands.registerCommand('octavo.refreshBib', async () => {
            const report = await cache.refresh(true);
            if (report) {
                void vscode.window.showInformationMessage(
                    vscode.l10n.t(
                        'Bibliography cache refreshed ({0} entries, {1} missing keys).',
                        report.entry_count, report.missing.length));
            } else {
                void vscode.window.showWarningMessage(
                    vscode.l10n.t(
                        'Could not refresh: no octavo.config.py or literature.bib found.'));
            }
        }),

        vscode.commands.registerCommand('octavo.refreshValues', async () => {
            const report = await valuesCache.refresh(true);
            if (report) {
                void vscode.window.showInformationMessage(
                    vscode.l10n.t('Analysis values refreshed ({0} values, {1} unresolved).',
                        Object.keys(report.values).length, report.missing.length));
            } else {
                void vscode.window.showWarningMessage(
                    vscode.l10n.t('Could not refresh: no octavo.config.py found.'));
            }
        }),

        vscode.commands.registerCommand('octavo.showOutput', () => output.show()),
    );

    // .qmd の「この分析を走らせる」ボタンは Octavo のプロジェクトの中だけに出す
    // （Quarto だけを使っている .qmd に出ると紛らわしい）。
    const syncHasConfig = (): void => {
        void findConfig().then((u) => vscode.commands.executeCommand(
            'setContext', 'octavo.hasConfig', u !== undefined));
    };
    const cfgWatcher = vscode.workspace.createFileSystemWatcher('**/octavo.config.py');
    context.subscriptions.push(cfgWatcher, cfgWatcher.onDidCreate(syncHasConfig),
                               cfgWatcher.onDidDelete(syncHasConfig));
    syncHasConfig();

    // 起動時に一度だけ静かに温めておく（補完・ホバーをすぐ使えるように）。
    void findConfig().then((u) => {
        if (u) {
            void cache.refresh();
            void valuesCache.refresh();
        }
    });
}

export function deactivate(): void {
    // 特に片付けるものは無い（Disposable は context.subscriptions が処理する）。
}
