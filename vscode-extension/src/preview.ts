// preview.ts — 原稿の左、組み上がった PDF を右で見る。
//
// 判断はぜんぶ CLI に寄せてある（bib.ts と同じ方針）:
//   octavo documents --json           どのファイルがどの文書か。講義は回ごとの行範囲つき
//   octavo build … --compile --json   組んで、**できた PDF の場所**を返す
// ここでやるのは「どの文書のどの形式を、いつ組み直し、どの列に出すか」だけ。
// out_dirs や拡張子から出力先を組み立て直さない — ずれると静かに古い PDF を
// 映し続けることになるので、場所は必ず build の結果から取る。
//
// 講義ノート（split_slides）は3列にできる: 原稿 | A4プリント | その回のスライド。
// 3列目はカーソルのある `#` の回に追従し、スライドと台本（typst-notes）を
// 切り替えられる。2列だけにしたいときは「出さない」にする。
//
// **プレビューは分析（.qmd）を走らせない**（build に --no-analysis）。重い推定や
// データの整形が保存のたびに走ると待たされるうえ、時間切れで失敗に見える。
// 代わりに古い分析があれば帯を出し、ボタンで走らせる（analysis.ts）。
import * as path from 'path';
import * as vscode from 'vscode';
import { fetchAnalysis, staleNames } from './analysis';
import { dirOf, findConfig, readToolFile, resolvePathFromTool, runCapture } from './runner';

export interface Part {
    name: string;
    key: string;
    title: string;
    start_line: number;      // 1 始まり
    end_line: number;
}

export interface DocInfo {
    name: string;
    src: string;             // 実行環境側の絶対パス
    rel: string;
    appendix: string | null;
    profile: string;
    targets: string[];
    split_slides: boolean;
    exists: boolean;
    parts: Part[];
}

interface DocumentsReport { root: string; config: string | null; documents: DocInfo[] }
interface BuildOne { doc: string; target: string; ok: boolean; outputs: string[];
                     compiled: string | null; report: string[] }
interface BuildReport { ok: boolean; results: BuildOne[] }

/** 3列目に何を出すか。 */
export type SideMode = 'slides' | 'notes' | 'none';

// PDF を出せる形式。前にあるものほど「本文の列」に向く（docx は PDF にならない）。
const MAIN_ORDER = ['typst', 'latex', 'beamer', 'typst-slides', 'typst-notes'];
const SLIDE_ORDER = ['typst-slides', 'beamer'];

/** stdout に警告が混じることがあるので、最後の JSON だけを読む（bib.ts と同じ）。 */
function lastJson<T>(text: string): T | undefined {
    const t = text.trim();
    if (!t) {
        return undefined;
    }
    const at = t.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? t.slice(at + 1) : t) as T;
    } catch {
        return undefined;
    }
}

function samePath(a: string | undefined, b: string | undefined): boolean {
    if (!a || !b) {
        return false;
    }
    const norm = (s: string): string => s.replace(/\\/g, '/').replace(/\/+$/, '');
    const x = norm(a);
    const y = norm(b);
    return process.platform === 'win32' ? x.toLowerCase() === y.toLowerCase() : x === y;
}

/** 実行環境側の絶対パスを、エディタ側のパスと比べられる形にする。 */
function editorPath(toolPath: string | null | undefined): string | undefined {
    return toolPath ? resolvePathFromTool(toolPath)?.fsPath : undefined;
}

// --------------------------------------------------------------------- 表示
/** PDF を1つ映す webview。中身の差し替えでスクロール位置は保つ。 */
class PdfPanel {
    readonly panel: vscode.WebviewPanel;
    private ready = false;
    private queued: unknown[] = [];

    constructor(private readonly media: vscode.Uri, column: vscode.ViewColumn,
                title: string, onDispose: () => void) {
        this.panel = vscode.window.createWebviewPanel(
            'octavo.preview', title, { viewColumn: column, preserveFocus: true },
            { enableScripts: true, retainContextWhenHidden: true,
              localResourceRoots: [media] });
        this.panel.webview.html = this.html();
        this.panel.webview.onDidReceiveMessage((m: { type?: string }) => {
            if (m?.type === 'runAnalysis') {
                void vscode.commands.executeCommand('octavo.analysisRun');
                return;
            }
            if (m?.type === 'ready') {
                this.ready = true;
                for (const msg of this.queued) {
                    void this.panel.webview.postMessage(msg);
                }
                this.queued = [];
            }
        });
        this.panel.onDidDispose(onDispose);
    }

    private post(msg: unknown): void {
        if (this.ready) {
            void this.panel.webview.postMessage(msg);
        } else {
            this.queued.push(msg);
        }
    }

    setTitle(title: string): void {
        this.panel.title = title;
    }

    busy(on: boolean): void {
        this.post({ type: 'busy', on });
    }

    /** PDF の中身を渡す。webview には base64 で送る（postMessage は JSON なので）。 */
    show(bytes: Uint8Array, label: string): void {
        this.post({ type: 'pdf', label, data: Buffer.from(bytes).toString('base64') });
    }

    error(message: string): void {
        this.post({ type: 'error', message });
    }

    /** 古い分析があることを帯で知らせる（text が空なら帯を消す）。 */
    stale(text: string): void {
        this.post({ type: 'stale', text, button: vscode.l10n.t('Run the analysis') });
    }

    dispose(): void {
        this.panel.dispose();
    }

    private html(): string {
        const w = this.panel.webview;
        const nonce = Array.from({ length: 32 },
            () => 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[
                Math.floor(Math.random() * 62)]).join('');
        const uri = (f: string): vscode.Uri => w.asWebviewUri(vscode.Uri.joinPath(this.media, f));
        // pdf.js はワーカーを blob から起こす。script-src に nonce、worker-src に blob:。
        const csp = [
            `default-src 'none'`,
            `img-src ${w.cspSource} blob: data:`,
            `style-src ${w.cspSource} 'unsafe-inline'`,
            `script-src 'nonce-${nonce}' ${w.cspSource}`,
            `worker-src ${w.cspSource} blob:`,
            `connect-src ${w.cspSource} blob:`,
            `font-src ${w.cspSource}`,
        ].join('; ');
        return `<!DOCTYPE html>
<html lang="${vscode.env.language}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<link rel="stylesheet" href="${uri('preview.css')}">
</head>
<body>
<div id="bar">
  <span id="label"></span>
  <span id="spacer"></span>
  <button id="out" title="${vscode.l10n.t('Zoom out')}">−</button>
  <button id="fit" title="${vscode.l10n.t('Fit to width')}">⤢</button>
  <button id="in" title="${vscode.l10n.t('Zoom in')}">＋</button>
  <span id="pages"></span>
</div>
<div id="stale"><span id="stale-text"></span><button id="stale-run"></button></div>
<div id="view"><div id="pages-host"></div></div>
<div id="message"></div>
<script nonce="${nonce}" type="module" src="${uri('preview.js')}"></script>
</body>
</html>`;
    }
}

// --------------------------------------------------------------------- 本体
export class PreviewManager implements vscode.Disposable {
    private main?: PdfPanel;
    private side?: PdfPanel;
    private doc?: DocInfo;
    private configUri?: vscode.Uri;
    private sideOverride?: SideMode;
    private part?: Part;
    private building = false;
    private again = false;
    private readonly subs: vscode.Disposable[] = [];
    private readonly media: vscode.Uri;

    constructor(context: vscode.ExtensionContext,
                private readonly log: (s: string) => void) {
        this.media = vscode.Uri.joinPath(context.extensionUri, 'media');
        this.subs.push(
            vscode.workspace.onDidSaveTextDocument((d) => this.onSave(d)),
            vscode.window.onDidChangeTextEditorSelection((e) => this.onCursor(e)),
        );
    }

    dispose(): void {
        for (const s of this.subs) {
            s.dispose();
        }
        this.main?.dispose();
        this.side?.dispose();
    }

    private get live(): boolean {
        return this.main !== undefined || this.side !== undefined;
    }

    /** このセッションで選び直していればそれ、無ければ設定の値。 */
    private get sideMode(): SideMode {
        return this.sideOverride ?? vscode.workspace.getConfiguration('octavo')
            .get<SideMode>('previewLectureColumn', 'slides');
    }

    /**
     * タイトルバーの「3列目」ボタンを出すかどうか（package.json の when 句が読む）。
     * 出すのは**スライドのある文書のプレビューが開いているとき**だけ。常に出すと
     * VS Code 標準の Markdown プレビューのボタンと並んで、似たものが3つになる。
     */
    private syncContext(): void {
        void vscode.commands.executeCommand('setContext', 'octavo.previewCanChooseColumn',
                                            this.live && this.slideish);
    }

    /** スライドを出す文書か（論文に台本やスライドの列は要らない）。 */
    private get slideish(): boolean {
        return this.doc?.profile === 'slides' || this.doc?.split_slides === true;
    }

    // -- 開く -----------------------------------------------------------
    async open(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'markdown') {
            void vscode.window.showWarningMessage(
                vscode.l10n.t('Octavo: open the manuscript (.md) first.'));
            return;
        }
        const configUri = await findConfig();
        if (!configUri) {
            void vscode.window.showWarningMessage(
                vscode.l10n.t('No octavo.config.py in this workspace.'));
            return;
        }
        this.configUri = configUri;
        const doc = await this.findDocument(editor.document.uri.fsPath);
        if (!doc) {
            void vscode.window.showWarningMessage(vscode.l10n.t(
                'Octavo: {0} is not registered in octavo.config.py.',
                editor.document.uri.fsPath));
            return;
        }
        this.doc = doc;
        this.part = this.partAt(editor.selection.active.line + 1);
        this.ensurePanels();
        await this.build();
    }

    /** 3列目を「スライド / 台本 / 出さない」から選ぶ（2分割と3分割の切り替え）。 */
    async chooseSide(): Promise<void> {
        const items: (vscode.QuickPickItem & { mode: SideMode })[] = [
            { label: vscode.l10n.t('Slides'), mode: 'slides',
              description: vscode.l10n.t('the deck for the session the cursor is in') },
            { label: vscode.l10n.t('Speaker script'), mode: 'notes',
              description: vscode.l10n.t('the same deck on A4 with ::: notes underneath') },
            { label: vscode.l10n.t('Nothing (two columns)'), mode: 'none',
              description: vscode.l10n.t('manuscript and one PDF only') },
        ];
        const picked = await vscode.window.showQuickPick(items,
            { title: vscode.l10n.t('What goes in the third column?') });
        if (!picked) {
            return;
        }
        if (picked.mode !== 'none' && this.doc && !this.slideish) {
            void vscode.window.showInformationMessage(vscode.l10n.t(
                'Octavo: {0} has no slides, so there is nothing for a third column.',
                this.doc.name));
            return;
        }
        this.sideOverride = picked.mode;
        if (!this.live) {
            await this.open();
            return;
        }
        if (this.sideMode === 'none') {
            this.side?.dispose();
            this.side = undefined;
            return;
        }
        this.ensurePanels();
        await this.build({ sideOnly: true });
    }

    /** 開いていれば組み直す（サイドバーで設定を変えたあとなど）。開いていなければ何もしない。 */
    async rebuildIfOpen(): Promise<void> {
        if (this.live) {
            await this.build();
        }
    }

    /** 手で組み直す。 */
    async refresh(): Promise<void> {
        if (!this.live) {
            await this.open();
            return;
        }
        await this.build();
    }

    // -- 文書を引く -----------------------------------------------------
    private async documents(): Promise<DocInfo[]> {
        if (!this.configUri) {
            return [];
        }
        const r = await runCapture(dirOf(this.configUri), ['documents', '--json'], 30000);
        const got = lastJson<DocumentsReport>(r.stdout);
        if (!got) {
            this.log(`[preview] octavo documents --json: ${r.stderr.trim() || r.stdout.trim()}`);
            return [];
        }
        return got.documents;
    }

    private async findDocument(fsPath: string): Promise<DocInfo | undefined> {
        for (const d of await this.documents()) {
            if (samePath(editorPath(d.src), fsPath) || samePath(editorPath(d.appendix), fsPath)) {
                return d;
            }
        }
        return undefined;
    }

    private partAt(line: number): Part | undefined {
        if (!this.doc?.split_slides) {
            return undefined;
        }
        return this.doc.parts.find((p) => line >= p.start_line && line <= p.end_line)
            ?? this.doc.parts[0];
    }

    // -- 何をどの列に ---------------------------------------------------
    private mainTarget(): string | undefined {
        const t = this.doc?.targets ?? [];
        return MAIN_ORDER.find((x) => t.includes(x));
    }

    private sideTarget(): string | undefined {
        if (!this.doc || this.sideMode === 'none' || !this.slideish) {
            return undefined;
        }
        if (this.sideMode === 'notes') {
            // targets に無くても --to で指せる（台本は「要るときだけ」でよい）
            return 'typst-notes';
        }
        const t = SLIDE_ORDER.find((x) => this.doc?.targets.includes(x));
        return t && t !== this.mainTarget() ? t : undefined;
    }

    private ensurePanels(): void {
        const main = this.mainTarget();
        if (main && !this.main) {
            this.main = new PdfPanel(this.media, vscode.ViewColumn.Two, 'Octavo',
                                     () => { this.main = undefined; this.syncContext(); });
        }
        if (this.sideTarget() && !this.side) {
            this.side = new PdfPanel(this.media, vscode.ViewColumn.Three, 'Octavo',
                                     () => { this.side = undefined; this.syncContext(); });
        }
        this.syncContext();
    }

    // -- 組む -----------------------------------------------------------
    private async build(opt: { sideOnly?: boolean } = {}): Promise<void> {
        if (!this.doc || !this.configUri || !this.live) {
            return;
        }
        if (this.building) {
            this.again = true;          // 走っているあいだの保存は1回にまとめる
            return;
        }
        this.building = true;
        try {
            do {
                this.again = false;
                if (!opt.sideOnly) {
                    await this.buildInto(this.main, this.doc.name, this.mainTarget());
                }
                const part = this.part?.name ?? this.doc.name;
                await this.buildInto(this.side, part, this.sideTarget());
                await this.showStale();
            } while (this.again);
        } finally {
            this.building = false;
        }
    }

    /** 古い分析があれば、開いている列に帯を出す（無ければ消す）。 */
    private async showStale(): Promise<void> {
        if (!this.configUri) {
            return;
        }
        const names = staleNames(await fetchAnalysis(dirOf(this.configUri)));
        const text = names.length
            ? vscode.l10n.t('The analysis is out of date ({0}), so the numbers, figures and tables may be old.',
                            names.map((n) => n.split('/').pop()).join(', '))
            : '';
        this.main?.stale(text);
        this.side?.stale(text);
    }

    private async buildInto(panel: PdfPanel | undefined, docName: string,
                            target: string | undefined): Promise<void> {
        if (!panel || !target || !this.configUri) {
            return;
        }
        panel.setTitle(`${docName} · ${target}`);
        panel.busy(true);
        const r = await runCapture(dirOf(this.configUri),
                                   ['build', docName, '--to', target, '--compile', '--json',
                                    '--no-analysis'],
                                   180000);
        const got = lastJson<BuildReport>(r.stdout);
        panel.busy(false);
        if (!got) {
            const why = (r.stderr.trim() || r.stdout.trim()).split('\n').slice(-12).join('\n');
            panel.error(why || vscode.l10n.t('octavo build --json returned nothing'));
            return;
        }
        const one = got.results.find((x) => x.compiled) ?? got.results[0];
        if (!one || !one.ok || !one.compiled) {
            const lines = got.results.flatMap((x) => x.report);
            panel.error(lines.slice(-14).join('\n')
                        || vscode.l10n.t('Could not build {0}.', docName));
            return;
        }
        const bytes = await readToolFile(one.compiled);
        if (!bytes) {
            panel.error(vscode.l10n.t('Built it, but could not read {0}.', one.compiled));
            return;
        }
        panel.show(bytes, one.compiled.split(/[\\/]/).pop() ?? docName);
    }

    // -- きっかけ -------------------------------------------------------
    private onSave(saved: vscode.TextDocument): void {
        if (!this.live || !this.doc) {
            return;
        }
        const p = saved.uri.fsPath;
        // 巻き込みで組み直すのはプロジェクトの中のものだけ。関係の無いフォルダの
        // .tex を保存しただけで組み直しが走るのは驚きなので、配下かどうかを見る。
        const root = this.configUri ? dirOf(this.configUri) : '';
        const inProject = root !== '' && !path.relative(root, p).startsWith('..');
        const mine = samePath(editorPath(this.doc.src), p)
            || samePath(editorPath(this.doc.appendix), p)
            || (inProject && /\.(bib|qmd|typ|tex|csl)$/i.test(p));
        if (!mine) {
            return;
        }
        // 回の区切りが動いているかもしれないので、原稿そのものなら引き直す
        void (async () => {
            if (samePath(editorPath(this.doc?.src), p)) {
                const fresh = await this.findDocument(p);
                if (fresh) {
                    this.doc = fresh;
                    const line = vscode.window.activeTextEditor?.selection.active.line;
                    this.part = this.partAt((line ?? 0) + 1);
                }
            }
            await this.build();
        })();
    }

    private onCursor(e: vscode.TextEditorSelectionChangeEvent): void {
        if (!this.live || !this.doc?.split_slides || !this.side) {
            return;
        }
        if (!samePath(editorPath(this.doc.src), e.textEditor.document.uri.fsPath)) {
            return;
        }
        const part = this.partAt(e.selections[0].active.line + 1);
        if (!part || part.name === this.part?.name) {
            return;
        }
        this.part = part;
        void this.build({ sideOnly: true });
    }
}
