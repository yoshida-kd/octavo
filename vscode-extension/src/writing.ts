// writing.ts — 文章のルールとフレーズバンク（octavo writing）。
//
// 中身はぜんぶ CLI から取る（sidebar.ts と同じ方針）:
//   一覧     octavo writing --json                     （見つかったパック）
//   原稿の分 octavo writing --for DOC --all --json     （使うパック・ファイル・項目。使わない理由つき）
//   ここ     octavo writing --file F --line N --print --json   （カーソルの節の分を重ねた本文）
//   変更     octavo config [--doc DOC] set|unset writing|writing_off
// どのパックを使うか、どの節か、どれを除くかは writing.py が決める。ここでは判断しない。
import * as vscode from 'vscode';
import { DocInfo } from './preview';
import { resolvePathFromTool, runCapture } from './runner';

/** `octavo writing --json` のパック1つ */
export interface PackInfo {
    name: string; title: string; path: string; where: string; extends: string[]; sections: string[];
    description: string; files: number;
}
export interface PacksReport { packs: PackInfo[]; sections: string[]; warnings: string[] }

/** 1つの項目（`## 見出し`）。id は writing_off に書く名前 */
export interface WritingItem { title: string; slug: string; line: number; id: string; off: boolean }
/** 1つのファイル。skipped は使わない理由（applies / lang / section / off）、使うなら null */
export interface WritingFile {
    id: string; pack: string; kind: string; path: string; title: string; where: string;
    section: string[]; used: boolean; skipped: string | null; items: WritingItem[];
}
/** `octavo writing --for DOC --json` */
export interface WritingReport {
    doc: string; packs: string[]; chosen: boolean; chosen_here: boolean; section: string | null;
    heading: string | null; sections: string[]; off: string[]; off_here: string[];
    files: WritingFile[]; warnings: string[]; text?: string;
}
interface SetReport { ok: boolean; error?: string }

function lastJson<T>(text: string): T | undefined {
    const s = text.trim();
    const at = s.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? s.slice(at + 1) : s) as T;
    } catch {
        return undefined;
    }
}

export async function fetchPacks(cwd: string): Promise<PacksReport | undefined> {
    const r = await runCapture(cwd, ['writing', '--json'], 30000);
    return lastJson<PacksReport>(r.stdout);
}

export async function fetchWriting(cwd: string, doc: string, log: (s: string) => void): Promise<WritingReport | undefined> {
    const r = await runCapture(cwd, ['writing', '--for', doc, '--all', '--json'], 30000);
    const got = lastJson<WritingReport>(r.stdout);
    if (!got) {
        log(`[writing] octavo writing --for ${doc}: ${r.stderr.trim()}`);
    }
    return got;
}

/** 原稿の冒頭に書くので、その原稿に未保存の編集があれば先に保存させる。 */
function dirty(doc: DocInfo): boolean {
    const uri = resolvePathFromTool(doc.src);
    const open = uri ? vscode.workspace.textDocuments.find((d) => d.uri.fsPath === uri.fsPath) : undefined;
    if (open?.isDirty) {
        void vscode.window.showWarningMessage(vscode.l10n.t(
            'Save {0} first: its settings are written at the top of the manuscript.',
            open.uri.path.split('/').pop() ?? doc.name));
        return true;
    }
    return false;
}

async function setValue(cwd: string, key: string, value: string[] | null, doc?: string): Promise<boolean> {
    const args = value === null ? ['config', 'unset', key, '--json']
                                : ['config', 'set', key, value.join(';'), '--json'];
    if (doc) {
        args.push('--doc', doc);
    }
    const r = await runCapture(cwd, args, 30000);
    const got = lastJson<SetReport>(r.stdout);
    if (!got || !got.ok) {
        void vscode.window.showErrorMessage(got?.error ?? (r.stderr.trim() || vscode.l10n.t('Could not change {0}.', key)));
        return false;
    }
    return true;
}

/**
 * 使うパックを、一般的なものから1つずつ選ばせる（並びに意味があるので、まとめて選ぶ画面にしない）。
 * doc を渡せばその原稿の冒頭に、渡さなければプロジェクトの設定に書く。
 */
export async function choosePacks(cwd: string, doc?: DocInfo, now?: string[] | null): Promise<boolean> {
    if (doc && dirty(doc)) {
        return false;
    }
    const report = await fetchPacks(cwd);
    const packs = (report?.packs ?? []).filter((p) => p.name !== 'local');
    if (!packs.length) {
        void vscode.window.showInformationMessage(vscode.l10n.t(
            'No writing rule packs yet. A pack is a folder in ~/.config/octavo/writing/ or notes/writing/ with rules/ and phrases/ in it.'));
        return false;
    }
    const title = doc ? vscode.l10n.t('Writing rules for {0}', doc.name) : vscode.l10n.t('Writing rules for the project');
    const chosen: string[] = [];
    type Item = vscode.QuickPickItem & { raw: string | 'done' | 'all' | 'follow' };
    for (;;) {
        const items: Item[] = packs.filter((p) => !chosen.includes(p.name)).map((p) => ({
            label: p.name, raw: p.name,
            description: [p.title !== p.name ? p.title : '',
                          p.extends.length ? vscode.l10n.t('brings {0}', p.extends.join(', ')) : ''].filter(Boolean).join(' · '),
            detail: p.description || undefined,
        }));
        if (chosen.length) {
            items.unshift({ label: vscode.l10n.t('$(check) Done: {0}', chosen.join(' → ')), raw: 'done' });
        } else {
            items.push({ label: vscode.l10n.t('Use every pack'), raw: 'all',
                         description: vscode.l10n.t('as when nothing is chosen') });
            if (doc) {
                items.push({ label: vscode.l10n.t('Follow the project'), raw: 'follow' });
            }
        }
        const picked = await vscode.window.showQuickPick(items, {
            title,
            placeHolder: chosen.length
                ? vscode.l10n.t('Next, a more specific pack (it wins where two disagree), or Done')
                : vscode.l10n.t('The most general pack first (now: {0})',
                                now?.length ? now.join(' → ') : vscode.l10n.t('every pack')),
        });
        if (!picked) {
            return false;
        }
        if (picked.raw === 'done') {
            break;
        }
        if (picked.raw === 'all') {
            // 「全部」: 原稿なら none と書く（プロジェクトの選び方より優先）、プロジェクトなら消す
            return setValue(cwd, 'writing', doc ? ['none'] : null, doc?.name);
        }
        if (picked.raw === 'follow') {
            return setValue(cwd, 'writing', null, doc?.name);
        }
        chosen.push(picked.raw);
        if (chosen.length === packs.length) {
            break;
        }
    }
    return setValue(cwd, 'writing', chosen, doc?.name);
}

/** 1つの項目を、その原稿では使わない・また使う（原稿の冒頭の writing_off）。 */
export async function toggleItem(cwd: string, doc: DocInfo, report: WritingReport, id: string): Promise<boolean> {
    if (dirty(doc)) {
        return false;
    }
    const here = report.off_here ?? [];
    if (report.off.includes(id) && !here.includes(id)) {
        void vscode.window.showInformationMessage(vscode.l10n.t(
            '{0} is turned off for the whole project. Change Writing rules turned off in the project settings.', id));
        return false;
    }
    const next = here.includes(id) ? here.filter((x) => x !== id) : [...here, id];
    return setValue(cwd, 'writing_off', next.length ? next : null, doc.name);
}

/** カーソルのある所の節の分を、重ねた本文で見せる（AI が読むものと同じ）。 */
export async function showHere(cwd: string, docs: DocInfo[]): Promise<void> {
    const ed = vscode.window.activeTextEditor;
    const fsPath = ed?.document.uri.fsPath;
    const same = (p?: string | null) => !!p && resolvePathFromTool(p)?.fsPath === fsPath;
    const doc = docs.find((d) => same(d.src) || same(d.appendix));
    if (!ed || !doc) {
        void vscode.window.showWarningMessage(vscode.l10n.t('Open a manuscript and put the cursor where you are writing.'));
        return;
    }
    const file = same(doc.src) ? doc.src : doc.appendix!;
    const r = await runCapture(cwd, ['writing', '--file', file, '--line', String(ed.selection.active.line + 1),
                                     '--print', '--json'], 30000);
    const got = lastJson<WritingReport>(r.stdout);
    if (!got?.text) {
        void vscode.window.showErrorMessage(r.stderr.trim() || vscode.l10n.t('Could not read the writing rules.'));
        return;
    }
    const shown = await vscode.workspace.openTextDocument({ content: got.text, language: 'markdown' });
    await vscode.window.showTextDocument(shown, { viewColumn: vscode.ViewColumn.Beside, preview: true, preserveFocus: true });
    void vscode.window.setStatusBarMessage(got.section
        ? vscode.l10n.t('Writing rules for {0} ({1})', got.section, got.heading ?? '')
        : vscode.l10n.t('Writing rules (no section found above the cursor: the rules for every section)'), 6000);
}
