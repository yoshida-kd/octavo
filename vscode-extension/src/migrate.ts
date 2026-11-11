// migrate.ts — 前に作ったプロジェクトを今の形にする（octavo migrate）を GUI から。
//
// 何を今の形にできるかは `octavo migrate --json` が決める（原稿の場所・書き方・約束事の
// ファイル・分析のヘルパー）。ここでは選ばせて、まず --dry-run で何が変わるかを出力パネルに
// 出し、確かめてから実行するだけ。コミットしていない変更があって CLI が止まったときは、
// CLI の言うことをそのまま見せる（--allow-dirty はターミナルから）。
import * as vscode from 'vscode';
import { runCapture, runStreaming } from './runner';

/** `octavo migrate --json` の1つ。args は `octavo migrate` に足す引数。 */
export interface Update { key: string; args: string[]; label: string; detail: string }
export interface MigrateReport { updates: Update[]; notes: string[] }

function lastJson<T>(text: string): T | undefined {
    const s = text.trim();
    const at = s.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? s.slice(at + 1) : s) as T;
    } catch {
        return undefined;
    }
}

/** 今の形にできるもの。古い CLI（--json がない）なら undefined。 */
export async function fetchUpdates(cwd: string): Promise<MigrateReport | undefined> {
    const r = await runCapture(cwd, ['migrate', '--json'], 30000);
    const got = lastJson<MigrateReport>(r.stdout);
    return got && Array.isArray(got.updates) ? got : undefined;
}

/** 選ぶ → 何が変わるかを見せる → 確かめる → 実行。何か変えたら true。 */
export async function migrateProject(cwd: string, output: vscode.OutputChannel): Promise<boolean> {
    const report = await fetchUpdates(cwd);
    if (!report) {
        void vscode.window.showWarningMessage(
            vscode.l10n.t('Octavo: could not read what can be updated. The octavo command may be older than this extension (Install or Update the Tools).'));
        return false;
    }
    if (!report.updates.length) {
        const notes = report.notes.length ? '\n' + report.notes.join('\n') : '';
        void vscode.window.showInformationMessage(
            vscode.l10n.t('Octavo: this project is already in the current form.') + notes);
        return false;
    }
    const picked = await vscode.window.showQuickPick(
        report.updates.map((u) => ({ label: u.label, description: u.detail, u })),
        { title: vscode.l10n.t('What to bring up to date (one at a time; you see what changes before anything is changed)'),
          ignoreFocusOut: true });
    if (!picked) {
        return false;
    }
    const u = picked.u;
    const run = (extra: string[], title: string): Thenable<number | null> => vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title, cancellable: true },
        (_progress, token) => runStreaming(cwd, ['migrate', ...u.args, ...extra],
                                           (text) => output.append(text), token));

    output.appendLine(`\n== ${u.label} (${vscode.l10n.t('what would change')})`);
    output.show(true);
    const dry = await run(['--dry-run'], vscode.l10n.t('Octavo: looking at what would change'));
    if (dry !== 0) {
        void vscode.window.showErrorMessage(dry === null
            ? vscode.l10n.t('Octavo: the update was stopped, or could not be started.')
            : vscode.l10n.t('Octavo: could not work out what would change (see the output).'));
        return false;
    }
    const go = vscode.l10n.t('Update');
    const answer = await vscode.window.showQuickPick(
        [{ label: go, description: u.label }, { label: vscode.l10n.t('Cancel') }],
        { title: vscode.l10n.t('What would change is in the output panel. Go ahead?'),
          ignoreFocusOut: true });
    if (answer?.label !== go) {
        return false;
    }
    output.appendLine(`\n== ${u.label}`);
    const code = await run([], vscode.l10n.t('Octavo: updating the project'));
    if (code === 0) {
        void vscode.window.showInformationMessage(vscode.l10n.t('Octavo: updated ({0}).', u.label));
        return true;
    }
    const show = vscode.l10n.t('Show the output');
    const msg = code === null
        ? vscode.l10n.t('Octavo: the update was stopped, or could not be started.')
        : vscode.l10n.t('Octavo: the update did not go through. The output says why (for example, changes that are not committed yet).');
    void vscode.window.showErrorMessage(msg, show).then((p) => {
        if (p === show) {
            output.show();
        }
    });
    return true;        // 途中まで変わっているかもしれないので、読み直させる
}
