// cards.ts — 原稿の [@key] にカーソルを当てると、Priorwork のカード（採用論文の要点）を出す。
//
// Priorwork は受け取り場所（literature/priorwork/<survey>.cards.json）に、サーベイが採った論文の
// カードを書く。読むのは CLI（`octavo priorwork cards --json`。.bib のキーでも、resolve する前の
// 印 PRIORWORK:<DOI> でも引ける）。ここは出すだけ（bib.ts と同じ方針）。
import * as vscode from 'vscode';
import { dirOf, findConfig, runCapture } from './runner';

/** `octavo priorwork cards --json` の1枚 */
export interface Card {
    survey: string; label: string; title: string; year?: number | null;
    evidence: string; fields: Record<string, string>; doi: string;
}
interface CardsReport { cards: Record<string, Card[]> }

const AT_KEY = /-?@(?:\{[^}\n]+\}|[\w][\w:.#$%&+?<>~/-]*[\w])/;

function lastJson<T>(text: string): T | undefined {
    const s = text.trim();
    const at = s.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? s.slice(at + 1) : s) as T;
    } catch {
        return undefined;
    }
}

export class CardCache implements vscode.Disposable {
    current: Record<string, Card[]> = {};
    private readonly subs: vscode.Disposable[] = [];

    constructor() {
        // カードが届いた・変わった、.bib が変わった（resolve のあとのキーで引くため）ら読み直す
        const w = vscode.workspace.createFileSystemWatcher('**/{literature/priorwork/*.cards.json,*.bib}');
        const again = (): void => void this.refresh();
        this.subs.push(w, w.onDidCreate(again), w.onDidChange(again), w.onDidDelete(again));
        void this.refresh();
    }

    dispose(): void {
        this.subs.forEach((s) => s.dispose());
    }

    async refresh(): Promise<void> {
        const configUri = await findConfig();
        if (!configUri) {
            this.current = {};
            return;
        }
        const r = await runCapture(dirOf(configUri), ['priorwork', 'cards', '--json'], 30000);
        this.current = lastJson<CardsReport>(r.stdout)?.cards ?? {};       // 古い CLI なら出さない
    }
}

function evidenceText(e: string): string {
    return e === 'fulltext' ? vscode.l10n.t('checked in the full text')
        : e === 'abstract' ? vscode.l10n.t('checked in the abstract only')
            : vscode.l10n.t('not checked');
}

export class CardHoverProvider implements vscode.HoverProvider {
    constructor(private readonly cache: CardCache) {}

    provideHover(document: vscode.TextDocument, position: vscode.Position): vscode.Hover | undefined {
        const range = document.getWordRangeAtPosition(position, AT_KEY);
        if (!range) {
            return undefined;
        }
        const key = document.getText(range).replace(/^-?@/, '').replace(/^\{(.*)\}$/, '$1');
        const cards = this.cache.current[key];
        if (!cards?.length) {
            return undefined;
        }
        const md = new vscode.MarkdownString();
        md.supportThemeIcons = true;
        cards.forEach((c, i) => {
            if (i) {
                md.appendMarkdown('\n\n---\n\n');
            }
            md.appendMarkdown(`$(library) **${c.label}** — ${c.title}\n\n`);
            md.appendMarkdown(`${vscode.l10n.t('Priorwork survey {0}', c.survey)} · ${evidenceText(c.evidence)}\n\n`);
            for (const [field, label] of [['rq', vscode.l10n.t('Question')], ['findings', vscode.l10n.t('Findings')],
                                          ['role', vscode.l10n.t('Role in the review')]] as const) {
                if (c.fields[field]) {
                    md.appendMarkdown(`**${label}**: `);
                    md.appendText(c.fields[field]);
                    md.appendMarkdown('\n\n');
                }
            }
        });
        return new vscode.Hover(md, range);
    }
}
