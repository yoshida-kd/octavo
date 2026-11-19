// ai.ts — 決まった頼みごと（校正・要約・文字起こし…）を AI に渡し、答えを横に開く。
//
// 中身はぜんぶ CLI から取る:
//   仕事の一覧   octavo ai list --json
//   実行         octavo ai run <仕事> <ファイル> [--lines A-B] --json  （答えはファイルに書かれる）
// どこへ送るか、送ってよいか、どこに書くかは ai.py が決める。ここでは判断しない。
import * as path from 'path';
import * as vscode from 'vscode';
import { findConfig, dirOf, resolvePathFromTool, runCapture } from './runner';

export interface AITask {
    name: string;
    title: string;
    inputs: string[];        // text / pdf / image / pdf-pages
    output: string;
    layer: string;           // project / user / bundled
}

interface AITaskReport { tasks: AITask[] }

export interface AIRunReport {
    ok: boolean;
    error: string | null;
    output: string | null;   // 書いたファイル（実行環境側の絶対パス）
}

function lastJson<T>(text: string): T | undefined {
    const t = text.trim();
    const at = t.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? t.slice(at + 1) : t) as T;
    } catch {
        return undefined;
    }
}

const IMAGE = /\.(png|jpe?g|webp|gif)$/i;

function kindOf(file: string): string[] {
    if (IMAGE.test(file)) return ['image'];
    if (/\.pdf$/i.test(file)) return ['pdf', 'pdf-pages'];
    return ['text'];
}

/** 開いているファイル（かエクスプローラーで選んだもの）を、選んだ仕事に渡す。 */
export async function runTask(log: (s: string) => void, target?: vscode.Uri): Promise<void> {
    const ed = vscode.window.activeTextEditor;
    const uri = target ?? ed?.document.uri;
    if (!uri) {
        void vscode.window.showInformationMessage(vscode.l10n.t('Open the file to send to the AI first.'));
        return;
    }
    if (!target && ed?.document.isDirty) {
        await ed.document.save();
    }
    const configUri = await findConfig(uri);
    if (!configUri) {
        void vscode.window.showErrorMessage(vscode.l10n.t('No octavo.config.py above this file.'));
        return;
    }
    const cwd = dirOf(configUri);
    const listed = lastJson<AITaskReport>((await runCapture(cwd, ['ai', 'list', '--json'], 30000)).stdout);
    const kinds = kindOf(uri.fsPath);
    const fits = (listed?.tasks ?? []).filter((x) => x.inputs.some((k) => kinds.includes(k)));
    if (!fits.length) {
        void vscode.window.showInformationMessage(vscode.l10n.t('No AI task takes this kind of file.'));
        return;
    }
    const pick = await vscode.window.showQuickPick(
        fits.map((x) => ({ label: x.title, description: x.name, detail: x.output, task: x })),
        { title: vscode.l10n.t('What should the AI do with {0}?', path.basename(uri.fsPath)) });
    if (!pick) return;
    const rel = path.relative(cwd, uri.fsPath).split(path.sep).join('/');
    const args = ['ai', 'run', pick.task.name, rel, '--json'];
    const sel = !target && ed && !ed.selection.isEmpty ? ed.selection : undefined;
    if (sel && kinds.includes('text')) {
        const end = sel.end.character === 0 && sel.end.line > sel.start.line ? sel.end.line : sel.end.line + 1;
        args.push('--lines', `${sel.start.line + 1}-${end}`);
    }
    const r = await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification,
          title: vscode.l10n.t('Asking the AI: {0}', pick.task.title) },
        () => runCapture(cwd, args, 60 * 60 * 1000));
    if (r.stderr.trim()) log(r.stderr.trim());
    const got = lastJson<AIRunReport>(r.stdout);
    if (!got?.ok || !got.output) {
        void vscode.window.showErrorMessage(got?.error ?? (r.stderr.trim() || vscode.l10n.t('The AI task failed (see the output).')));
        return;
    }
    const out = resolvePathFromTool(got.output);
    if (out) {
        await vscode.window.showTextDocument(await vscode.workspace.openTextDocument(out),
                                             { viewColumn: vscode.ViewColumn.Beside, preview: false });
    }
}
