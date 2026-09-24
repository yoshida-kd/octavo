// bib.ts — `octavo checkbib --json` の結果をキャッシュして配る。
//
// 判定ロジック（何が壊れているか）は Python 側の octavo/check.py に1箇所
// だけある。この拡張はそれを JSON で受け取って表示するだけで、BibTeX の
// パーサや検査ルールを TypeScript 側で作り直さない。`octavo checkbib` を手で
// 打ったときと拡張の診断が食い違うことが無いようにするため。

import * as vscode from 'vscode';
import { dirOf, findConfig, runCapture } from './runner';

export interface BibEntry {
    key: string;
    type: string;
    authors: string;
    year: string;
    title: string;
}

export interface BibProblem {
    key: string;
    issue: string;
    detail: string;
    accepted: boolean;
    reason: string;
}

export interface CheckbibReport {
    bib_file: string;
    entry_count: number;
    entries: Record<string, BibEntry>;
    cited: string[];
    cited_by_doc: Record<string, string[]>;
    missing: string[];
    suggestions: Record<string, string>;
    duplicates: string[][];
    problems: BibProblem[];
    accepted: BibProblem[];
    unused: string[];
}

export class BibCache {
    private report: CheckbibReport | undefined;
    private configUri: vscode.Uri | undefined;
    private refreshing: Promise<CheckbibReport | undefined> | undefined;

    private readonly onDidUpdateEmitter = new vscode.EventEmitter<CheckbibReport | undefined>();
    readonly onDidUpdate = this.onDidUpdateEmitter.event;

    private readonly onErrorEmitter = new vscode.EventEmitter<string>();
    readonly onError = this.onErrorEmitter.event;

    get current(): CheckbibReport | undefined {
        return this.report;
    }

    get lastConfig(): vscode.Uri | undefined {
        return this.configUri;
    }

    /** 実行中なら同じ Promise に相乗りする（保存イベントが連続しても二重に走らせない）。 */
    async refresh(force = false): Promise<CheckbibReport | undefined> {
        if (this.refreshing && !force) {
            return this.refreshing;
        }
        this.refreshing = this.doRefresh();
        try {
            return await this.refreshing;
        } finally {
            this.refreshing = undefined;
        }
    }

    private async doRefresh(): Promise<CheckbibReport | undefined> {
        const configUri = await findConfig();
        if (!configUri) {
            this.report = undefined;
            this.configUri = undefined;
            return undefined;
        }
        this.configUri = configUri;
        const cwd = dirOf(configUri);
        // -c は付けない。cwd を octavo.config.py のあるディレクトリにしてあるので
        // CLI の既定（カレントの octavo.config.py）に任せる。configUri.fsPath は
        // Windows 形式のことがあり、wsl.exe 越しにはそのままでは渡せないため。
        const result = await runCapture(cwd, ['checkbib', '--json']);

        // checkbib は「引いていないキーが有る」だけでも exit 1 を返す設計では
        // ない（missing がある時だけ 1）。JSON さえ吐いていれば内容を使う。
        const text = result.stdout.trim();
        if (!text) {
            this.onErrorEmitter.fire(result.stderr.trim() ||
                vscode.l10n.t('octavo checkbib --json returned nothing'));
            return this.report;
        }
        try {
            // stderr に警告が混じって stdout の前に出ることがあるため、
            // 最後の "{" から先を JSON として読む。
            const jsonStart = text.lastIndexOf('\n{');
            const jsonText = jsonStart >= 0 ? text.slice(jsonStart + 1) : text;
            this.report = JSON.parse(jsonText) as CheckbibReport;
            this.onDidUpdateEmitter.fire(this.report);
            return this.report;
        } catch (e) {
            this.onErrorEmitter.fire(
                vscode.l10n.t('Could not read the checkbib output as JSON: {0}', String(e)) +
                '\n' + text.slice(0, 500));
            return this.report;
        }
    }

    dispose(): void {
        this.onDidUpdateEmitter.dispose();
        this.onErrorEmitter.dispose();
    }
}
