// revise.ts — 推敲の読み直す所（octavo revise）。
//
// 中身はぜんぶ CLI から取る:
//   一覧     octavo revise <文書> --json            （回は記録しない）
//   記録     octavo revise <文書> --fine <キー>      （直さなくてよい。その文が変わるまで出ない）
// 何を読み直す所とするか、新しいか、どれが判断済みかは revise.py が決める。ここでは判断しない。
import * as vscode from 'vscode';
import { resolvePathFromTool, runCapture } from './runner';

export interface ReviseFinding {
    key: string;
    check: string;           // rule | count | lookup | octavo | outline | ask | lint | translation
    rule: string;
    title: string;
    file: string;            // プロジェクトからの相対パス
    line: number;
    text: string;
    note: string;
    state: string;           // new | seen | fine
}

export interface ReviseReport {
    doc: string;
    base: string | null;
    findings: ReviseFinding[];
    paragraphs: number;
    changed: number;
    fine: number;
    warnings: string[];
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

export async function fetchRevise(cwd: string, doc: string, log: (s: string) => void): Promise<ReviseReport | undefined> {
    const r = await runCapture(cwd, ['revise', doc, '--json'], 60000);
    const got = lastJson<ReviseReport>(r.stdout);
    if (!got) {
        log(`[revise] octavo revise ${doc} --json: ${r.stderr.trim()}`);
    }
    return got;
}

export function findingIcon(f: ReviseFinding): string {
    return f.check === 'ask' ? 'question' : f.check === 'translation' ? 'globe'
        : f.check === 'lint' ? 'symbol-number' : f.check === 'outline' ? 'list-tree'
        : f.state === 'new' ? 'circle-filled' : 'circle-outline';
}

export async function openFinding(root: string, f: ReviseFinding): Promise<void> {
    const uri = resolvePathFromTool(`${root}/${f.file}`);
    if (!uri) return;
    const doc = await vscode.workspace.openTextDocument(uri);
    const pos = new vscode.Position(Math.max(0, f.line - 1), 0);
    await vscode.window.showTextDocument(doc, { selection: new vscode.Range(pos, pos) });
}

/** 直さなくてよい、と記録する。 */
export async function markFine(cwd: string, doc: string, f: ReviseFinding, log: (s: string) => void): Promise<boolean> {
    const r = await runCapture(cwd, ['revise', doc, '--fine', f.key], 30000);
    log(r.stdout.trim() + (r.stderr.trim() ? '\n' + r.stderr.trim() : ''));
    if (r.code !== 0) {
        void vscode.window.showErrorMessage(r.stderr.trim() || vscode.l10n.t('Could not record it (see the output).'));
        return false;
    }
    return true;
}
