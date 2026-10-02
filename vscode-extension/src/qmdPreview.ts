// qmdPreview.ts — .qmd を開いたとき、その分析の**いまある HTML**（Quarto が書き出したもの）を
// エディタの右に出す。
//
// ここは「見せるだけ」: .qmd を保存しても組み直さない（分析の実行は analysis.ts の
// ボタンか `octavo analysis run`。重い推定が保存のたびに走るのを避けるため）。実行が
// 終わって HTML が書き換わったら、出ている画面を自動で読み直す。
//
// 出すのは Octavo のプロジェクトの中の .qmd だけ（Quarto だけを使っている .qmd には出ない）。
// HTML は `embed-resources: true`（新しい .qmd の既定）で1枚に収まっている前提。
// 画面を自分で閉じたら、その .qmd を開き直すまで出さない。
// Quarto 拡張機能のプレビュー（Preview ボタン）が動いているあいだは出さない。始まったら
// こちらを閉じる（同じ HTML が2つ並ばないように）。検知は、Quarto が開くターミナル
// 「Quarto Preview」と、その画面（webview の viewType quarto.previewView）で行う。
import * as vscode from 'vscode';
import { dirOf, findConfig } from './runner';
import { samePath } from './preview';

const isQmd = (p: string): boolean => /\.qmd$/i.test(p);
const htmlOf = (qmd: string): string => qmd.replace(/\.qmd$/i, '.html');

const QUARTO_TERMINAL = 'Quarto Preview';

/** Quarto のプレビューが動いているか（ターミナルか画面のどちらかがある）。 */
export function quartoPreviewRunning(): boolean {
    if (vscode.window.terminals.some((t) => t.name === QUARTO_TERMINAL && t.exitStatus === undefined)) {
        return true;
    }
    return vscode.window.tabGroups.all.some((g) => g.tabs.some((tab) =>
        tab.input instanceof vscode.TabInputWebview && /quarto\.previewView$/.test(tab.input.viewType)));
}

export class QmdPreview implements vscode.Disposable {
    private panel?: vscode.WebviewPanel;
    private current?: string;            // いま映している .qmd
    private closedByUser?: string;       // 自分で閉じた .qmd（開き直すまで出さない）
    private reloadTimer?: NodeJS.Timeout;
    private readonly subs: vscode.Disposable[] = [];

    constructor(private readonly log: (s: string) => void) {
        const watcher = vscode.workspace.createFileSystemWatcher('**/*.html');
        const changed = (u: vscode.Uri): void => this.onHtmlChanged(u.fsPath);
        this.subs.push(
            watcher, watcher.onDidChange(changed), watcher.onDidCreate(changed),
            vscode.window.onDidChangeActiveTextEditor((e) => void this.onEditor(e)),
            vscode.window.onDidOpenTerminal(() => this.onQuartoChange()),
            vscode.window.onDidCloseTerminal(() => this.onQuartoChange()),
            vscode.window.tabGroups.onDidChangeTabs(() => this.onQuartoChange()),
        );
        void this.onEditor(vscode.window.activeTextEditor);
    }

    dispose(): void {
        clearTimeout(this.reloadTimer);
        this.disposing = true;
        for (const s of this.subs) {
            s.dispose();
        }
        this.panel?.dispose();
    }

    private quarto = false;

    /** Quarto のプレビューが始まったらこちらを閉じ、終わったら（.qmd を開いていれば）出し直す。 */
    private onQuartoChange(): void {
        const running = quartoPreviewRunning();
        if (running === this.quarto) {
            return;
        }
        this.quarto = running;
        if (running && this.panel) {
            this.closingForQuarto = true;    // 利用者が閉じたことにしない（onDidDispose が読む）
            this.panel.dispose();
            this.log('[qmd] Quarto Preview is running: closed the HTML view');
        } else if (!running) {
            this.closedByUser = undefined;
            void this.onEditor(vscode.window.activeTextEditor);
        }
    }

    private get enabled(): boolean {
        return vscode.workspace.getConfiguration('octavo').get<boolean>('qmdPreview', true);
    }

    /** Octavo のプロジェクトの中の .qmd か。 */
    private async inProject(fsPath: string): Promise<boolean> {
        const config = await findConfig();
        if (!config) {
            return false;
        }
        const root = dirOf(config).replace(/\\/g, '/').replace(/\/+$/, '');
        const p = fsPath.replace(/\\/g, '/');
        return p.toLowerCase().startsWith(root.toLowerCase() + '/');
    }

    private async onEditor(editor: vscode.TextEditor | undefined): Promise<void> {
        // 画面（webview）にフォーカスが移ったときは editor が undefined になる。何もしない
        if (!editor || !this.enabled || quartoPreviewRunning()) {
            return;
        }
        const p = editor.document.uri.fsPath;
        if (!isQmd(p)) {
            this.closedByUser = undefined;
            return;
        }
        if (samePath(this.closedByUser, p)) {
            return;
        }
        this.closedByUser = undefined;
        if (samePath(this.current, p) && this.panel) {
            return;
        }
        if (!(await this.inProject(p))) {
            return;
        }
        await this.show(p);
    }

    private onHtmlChanged(htmlPath: string): void {
        if (!this.panel || !this.current || !samePath(htmlOf(this.current), htmlPath)) {
            return;
        }
        // 書き出しの途中を読まないように、少し待ってから読み直す
        clearTimeout(this.reloadTimer);
        this.reloadTimer = setTimeout(() => void this.show(this.current!, true), 400);
    }

    private async show(qmd: string, reload = false): Promise<void> {
        const uri = vscode.Uri.file(htmlOf(qmd));
        let text: string | undefined;
        try {
            text = Buffer.from(await vscode.workspace.fs.readFile(uri)).toString('utf-8');
        } catch {
            text = undefined;
        }
        // まだ組んでいない分析: 画面がすでに出ているときだけ、その旨を出す（出ていなければ何も出さない）
        if (text === undefined && !this.panel) {
            return;
        }
        const name = qmd.replace(/\\/g, '/').split('/').pop() ?? qmd;
        if (!this.panel) {
            this.panel = vscode.window.createWebviewPanel(
                'octavo.qmdPreview', htmlOf(name), { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true },
                { enableScripts: true, retainContextWhenHidden: true });
            this.panel.onDidDispose(() => {
                if (this.current && !this.disposing && !this.closingForQuarto) {
                    this.closedByUser = this.current;
                }
                this.closingForQuarto = false;
                this.panel = undefined;
            });
        }
        this.current = qmd;
        this.panel.title = htmlOf(name);
        this.panel.webview.html = text === undefined
            ? this.notRendered(name)
            : withScrollMemory(text, qmd);
        if (!reload) {
            this.log(`[qmd] ${htmlOf(name)}`);
        }
    }

    private disposing = false;
    private closingForQuarto = false;

    private notRendered(name: string): string {
        const msg = vscode.l10n.t('{0} has not been rendered yet. Run the analysis (the ▶ button in the title bar) and the result appears here.', name);
        const esc = msg.replace(/&/g, '&amp;').replace(/</g, '&lt;');
        return `<!DOCTYPE html><html><body style="font-family:var(--vscode-font-family);`
            + `color:var(--vscode-foreground);padding:24px"><p>${esc}</p></body></html>`;
    }
}

/**
 * 読み直しても同じ場所に残るように、スクロール位置を覚える（webview の state）。
 * Quarto の HTML は自前のスクリプトを持つので、それとは別の1枚を末尾に足すだけにする。
 */
export function withScrollMemory(html: string, key: string): string {
    const k = JSON.stringify(key);
    const script = `<script>(function(){var vs=acquireVsCodeApi();var K=${k};`
        + `var s=vs.getState();if(s&&s.k===K){window.addEventListener('load',function(){window.scrollTo(0,s.y||0);});}`
        + `var t;window.addEventListener('scroll',function(){clearTimeout(t);`
        + `t=setTimeout(function(){vs.setState({k:K,y:window.scrollY});},100);});})();</script>`;
    return /<\/body>/i.test(html) ? html.replace(/<\/body>/i, () => script + '</body>') : html + script;
}
