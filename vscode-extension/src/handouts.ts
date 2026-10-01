// handouts.ts — 講義ノートの回ごとの配布資料（octavo extract → build/handouts/）。
//
// 手で作る（サイドバーの「回ごとの配布資料を作る」）ほか、回の区切りのある講義ノートを
// 保存するたびに裏で作り直す（octavo.updateHandoutsOnSave）。プレビューと同じ
// build/typst/<名前>.typ を書くので、プレビューが組んでいるあいだは始めず、
// 途中でプレビューが組み始めたら止めて、終わってからやり直す。
// 保存のたびの更新では通知を出さない（ステータスバーだけ。失敗は出力パネルへ）。

import * as vscode from 'vscode';
import { DocInfo, editorPath, PreviewManager, samePath } from './preview';
import { dirOf, findConfig, resolvePathFromTool, runCapture, runStreaming } from './runner';

interface ExtractReport { ok?: boolean; error?: string; made?: { key: string; pdf: string }[] }

function lastJson<T>(text: string): T | undefined {
    const line = text.trim().split('\n').pop() ?? '';
    try {
        return JSON.parse(line) as T;
    } catch {
        return undefined;
    }
}

interface Job { cwd: string; name: string }

export class HandoutManager implements vscode.Disposable {
    private readonly status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 99);
    private readonly subs: vscode.Disposable[] = [];
    private pending?: Job;               // 次に作り直すもの（保存が続けば最後の1つ）
    private timer?: NodeJS.Timeout;
    private running?: vscode.CancellationTokenSource;
    private hide?: NodeJS.Timeout;

    constructor(private readonly preview: PreviewManager,
                private readonly log: (s: string) => void) {
        this.subs.push(
            vscode.workspace.onDidSaveTextDocument((d) => void this.onSave(d)),
            // プレビューが組み始めたら止め、組み終わったら残りを片付ける
            preview.onBusy((busy) => {
                if (busy) {
                    this.stop();
                } else {
                    this.kick(500);
                }
            }),
        );
    }

    dispose(): void {
        this.stop();
        clearTimeout(this.timer);
        clearTimeout(this.hide);
        this.status.dispose();
        for (const s of this.subs) {
            s.dispose();
        }
    }

    /** 手で作る。結果は通知で知らせ、フォルダーを開けるようにする。 */
    async makeNow(name: string): Promise<void> {
        const configUri = await findConfig();
        if (!configUri) {
            return;
        }
        this.stop();
        this.pending = undefined;
        const cwd = dirOf(configUri);
        let text = '';
        const code = await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification, cancellable: true,
            title: vscode.l10n.t('Octavo: cutting {0} into session handouts…', name),
        }, (_p, token) => runStreaming(cwd, ['extract', name, '--json'],
                                       (s) => { text += s; }, token));
        const res = lastJson<ExtractReport>(text) ?? {};
        if (code !== 0 || !res.ok) {
            this.log(text);
            void vscode.window.showErrorMessage(res.error
                ?? vscode.l10n.t('Octavo: could not cut the handout (see the Output panel).'));
            return;
        }
        const made = res.made ?? [];
        const open = vscode.l10n.t('Open the folder');
        const picked = await vscode.window.showInformationMessage(
            vscode.l10n.t('Octavo: made {0} session handouts in build/handouts/.', made.length), open);
        const first = made.length ? resolvePathFromTool(made[0].pdf) : undefined;
        if (picked === open && first) {
            await vscode.commands.executeCommand('revealFileInOS', first);
        }
    }

    // -- 保存のたびの更新 ---------------------------------------------------
    private async onSave(saved: vscode.TextDocument): Promise<void> {
        if (saved.languageId !== 'markdown'
            || !vscode.workspace.getConfiguration('octavo').get<boolean>('updateHandoutsOnSave', true)) {
            return;
        }
        const configUri = await findConfig();
        if (!configUri) {
            return;
        }
        const cwd = dirOf(configUri);
        const r = await runCapture(cwd, ['documents', '--json']);
        const docs = lastJson<{ documents: DocInfo[] }>(r.stdout)?.documents ?? [];
        const doc = docs.find((d) => d.handouts && samePath(editorPath(d.src), saved.uri.fsPath));
        if (!doc) {
            return;
        }
        this.pending = { cwd, name: doc.name };
        this.kick(800);
    }

    /** 少し待ってから、プレビューが組んでいなければ作り直す。 */
    private kick(delay: number): void {
        clearTimeout(this.timer);
        this.timer = setTimeout(() => void this.run(), delay);
    }

    /** 途中のものを止める（止めたものは pending に戻して、あとでやり直す）。 */
    private stop(): void {
        this.running?.cancel();
    }

    private async run(): Promise<void> {
        const job = this.pending;
        if (!job || this.running || this.preview.busy) {
            return;                       // 組み終わり（onBusy）か、今の実行の後でまた来る
        }
        this.pending = undefined;
        const source = new vscode.CancellationTokenSource();
        this.running = source;
        clearTimeout(this.hide);
        this.status.text = `$(sync~spin) ${vscode.l10n.t('Handouts')}`;
        this.status.tooltip = vscode.l10n.t('Octavo: updating the session handouts of {0}…', job.name);
        this.status.command = undefined;
        this.status.show();
        let text = '';
        const code = await runStreaming(job.cwd, ['extract', job.name, '--json'],
                                        (s) => { text += s; }, source.token);
        const cancelled = source.token.isCancellationRequested;
        source.dispose();
        this.running = undefined;
        if (cancelled) {
            this.pending ??= job;         // プレビューのあとでやり直す
            this.status.hide();
            return;
        }
        const res = lastJson<ExtractReport>(text) ?? {};
        if (code !== 0 || !res.ok) {
            this.log(`[handouts] ${job.name}\n${text.trim()}`);
            this.status.text = `$(warning) ${vscode.l10n.t('Handouts')}`;
            this.status.tooltip = vscode.l10n.t(
                'Octavo: could not update the session handouts of {0} (click for the Output panel).', job.name);
            this.status.command = 'octavo.showOutput';
            return;
        }
        this.status.text = `$(check) ${vscode.l10n.t('Handouts')}`;
        this.status.tooltip = vscode.l10n.t('Octavo: updated {0} session handouts in build/handouts/.',
                                            (res.made ?? []).length);
        this.hide = setTimeout(() => this.status.hide(), 4000);
        if (this.pending) {
            this.kick(0);
        }
    }
}
