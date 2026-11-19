// translation.ts — 言語違いの原稿（docs/<名前>/<名前>.en.md など）と主の原稿の、節ごとの対応。
//
// 中身はぜんぶ CLI から取る:
//   対応     octavo translation <文書> --json   （節ごとの状態・行・食い違い）
//   記録     octavo translation <文書> --mark [鍵]（合わせた、と docs/<名前>/translation.json に書く）
//   材料     octavo translation <文書> --print 鍵（AI に渡す、両方の節と食い違い）
// どの節が対応するか、どちらが古いかは translation.py が決める。ここでは判断しない。
import * as vscode from 'vscode';
import { resolvePathFromTool, runCapture } from './runner';

export interface TranslationSide {
    title: string;
    line: number;
    file: string;            // プロジェクトからの相対パス
}

export interface TranslationSection {
    key: string;
    state: string;           // synced | unsynced | main-changed | other-changed | both-changed | only-main | only-other
    main: TranslationSide | null;
    other: TranslationSide | null;
    differs: Record<string, { main_only: string[]; other_only: string[] }>;
}

export interface TranslationReport {
    main: string;
    other: string;
    lang: string;
    record: string;
    sections: TranslationSection[];
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

export async function fetchTranslation(cwd: string, doc: string,
                                       log: (s: string) => void): Promise<TranslationReport | undefined> {
    const r = await runCapture(cwd, ['translation', doc, '--json'], 30000);
    const got = lastJson<TranslationReport>(r.stdout);
    if (!got) {
        log(`[translation] octavo translation ${doc} --json: ${r.stderr.trim()}`);
    }
    return got;
}

export function stateLabel(state: string): string {
    switch (state) {
        case 'synced': return vscode.l10n.t('matched');
        case 'unsynced': return vscode.l10n.t('never matched');
        case 'main-changed': return vscode.l10n.t('the main manuscript changed');
        case 'other-changed': return vscode.l10n.t('this language changed');
        case 'both-changed': return vscode.l10n.t('both changed');
        case 'only-main': return vscode.l10n.t('only in the main manuscript');
        case 'only-other': return vscode.l10n.t('only in this language');
        default: return state;
    }
}

export function stateIcon(state: string): string {
    return state === 'synced' ? 'pass'
        : state === 'only-main' || state === 'only-other' ? 'circle-slash'
        : state === 'unsynced' ? 'circle-large-outline' : 'diff';
}

/** 節を開く（言語違いの側。なければ主の原稿の側）。 */
export async function openSection(root: string, s: TranslationSection): Promise<void> {
    const side = s.other ?? s.main;
    if (!side) return;
    const uri = resolvePathFromTool(`${root}/${side.file}`);
    if (!uri) return;
    const doc = await vscode.workspace.openTextDocument(uri);
    const pos = new vscode.Position(Math.max(0, side.line - 1), 0);
    await vscode.window.showTextDocument(doc, { selection: new vscode.Range(pos, pos) });
}

/** 合わせた、と記録する（key がなければ両方にある節すべて）。 */
export async function markMatched(cwd: string, doc: string, key: string | undefined,
                                  log: (s: string) => void): Promise<boolean> {
    if (!key) {
        const yes = vscode.l10n.t('Record Them');
        const pick = await vscode.window.showWarningMessage(
            vscode.l10n.t('Record every section in both manuscripts as matched as they are now?'),
            { modal: true }, yes);
        if (pick !== yes) return false;
    }
    const r = await runCapture(cwd, ['translation', doc, '--mark', ...(key ? [key] : [])], 30000);
    log(r.stdout.trim() + (r.stderr.trim() ? '\n' + r.stderr.trim() : ''));
    if (r.code !== 0) {
        void vscode.window.showErrorMessage(r.stderr.trim() || vscode.l10n.t('Could not record it (see the output).'));
        return false;
    }
    return true;
}

/** AI に渡す材料（両方の節・食い違い・対訳表）をクリップボードに。 */
export async function copyMaterial(cwd: string, doc: string, key: string): Promise<void> {
    const r = await runCapture(cwd, ['translation', doc, '--print', key], 30000);
    if (r.code !== 0) {
        void vscode.window.showErrorMessage(r.stderr.trim() || vscode.l10n.t('Could not read the section.'));
        return;
    }
    await vscode.env.clipboard.writeText(r.stdout);
    void vscode.window.showInformationMessage(
        vscode.l10n.t('Copied what is needed to bring {0} in line. Paste it to the AI.', key));
}
