// analysis.ts — 分析（.qmd）の状態を読み、GUI から走らせる。
//
// 状態は `octavo analysis --json` から取る（どれが古いか・手動かは CLI が決める。
// ここで更新時刻を比べ直したりしない）。走らせるのは `octavo analysis run`。
// 進み具合を通知に出し、出力は「Octavo」の出力パネルに流す。ターミナルを
// 使わないのは、ターミナルに慣れていない人でもボタンだけで済むようにするためと、
// 終わったことを拡張が知ってプレビューやサイドバーを更新するため。
import * as vscode from 'vscode';
import { runCapture, runStreaming } from './runner';

export interface AnalysisUnit {
    key: string;
    src: string;
    exists: boolean;
    stale: boolean;
    manual: boolean;
    deps: number;
    rendered_at: number | null;
}

export interface AnalysisReport { quarto: string | null; units: AnalysisUnit[]; stale: number }

function lastJson<T>(text: string): T | undefined {
    const s = text.trim();
    const at = s.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? s.slice(at + 1) : s) as T;
    } catch {
        return undefined;
    }
}

export async function fetchAnalysis(cwd: string): Promise<AnalysisReport | undefined> {
    const r = await runCapture(cwd, ['analysis', '--json'], 30000);
    return lastJson<AnalysisReport>(r.stdout);
}

/** 古い分析の名前（プレビューの帯・通知に出す）。 */
export function staleNames(report: AnalysisReport | undefined): string[] {
    return (report?.units ?? []).filter((u) => u.exists && u.stale).map((u) => u.key);
}

/**
 * 分析を走らせる。names が空なら古いもの全部（手動のものも含む）、
 * 名指しすれば古くなくてもそれを走らせる。成功したら true。
 */
export async function runAnalysisWithProgress(cwd: string, names: string[],
                                              output: vscode.OutputChannel): Promise<boolean> {
    const title = names.length
        ? vscode.l10n.t('Octavo: running {0}', names.join(', '))
        : vscode.l10n.t('Octavo: running the analysis');
    output.appendLine(`\n== ${title}`);
    const code = await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title, cancellable: true },
        (progress, token) => runStreaming(cwd, ['analysis', 'run', ...names], (text) => {
            output.append(text);
            const last = text.trim().split('\n').pop()?.trim();
            if (last) {
                progress.report({ message: last.slice(0, 120) });
            }
        }, token));
    const show = vscode.l10n.t('Show the output');
    if (code === 0) {
        void vscode.window.showInformationMessage(vscode.l10n.t('Octavo: the analysis finished.'));
        return true;
    }
    const msg = code === null
        ? vscode.l10n.t('Octavo: the analysis was stopped, or could not be started.')
        : vscode.l10n.t('Octavo: the analysis failed.');
    void vscode.window.showErrorMessage(msg, show).then((picked) => {
        if (picked === show) {
            output.show();
        }
    });
    return false;
}
