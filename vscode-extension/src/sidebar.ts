// sidebar.ts — アクティビティバーの Octavo。原稿・設定・道具を1か所に並べる。
//
// 中身はぜんぶ CLI から取る（bib.ts / preview.ts と同じ方針）:
//   原稿   octavo documents --json   （講義ノートは回ごとの行範囲つき）
//   設定   octavo config --json      （画面に出す鍵・型・選択肢・既定かどうか）
//   変更   octavo config set|unset   （octavo.config.py のその1行だけを書き換え、
//                                    設定として読めるか確かめてから保存する）
//   分析   octavo analysis --json    （.qmd ごとの 最新/古い/手動。走らせるのは analysis.ts）
// どの鍵を出すか、値として正しいかは confedit.py が決める。ここでは判断しない。
import * as vscode from 'vscode';
import { AnalysisReport, AnalysisUnit, fetchAnalysis } from './analysis';
import { DocInfo, Part } from './preview';
import { dirOf, findConfig, resolvePathFromTool, runCapture } from './runner';

export interface Setting {
    key: string;
    section: string;
    section_label: string;
    label: string;
    kind: string;                   // 'choice' | 'bool' | 'color' | 'int' | 'text'
    choices: (string | null)[];
    value: unknown;
    default: unknown;
    explicit: boolean;
}

interface ConfigReport { config: string; settings: Setting[] }
interface SetReport { ok: boolean; error?: string }
interface DocumentsReport { documents: DocInfo[] }

type Node =
    | { kind: 'group'; id: 'docs' | 'analysis' | 'settings' | 'tools' }
    | { kind: 'unit'; u: AnalysisUnit }
    | { kind: 'doc'; doc: DocInfo }
    | { kind: 'part'; doc: DocInfo; part: Part }
    | { kind: 'section'; label: string; items: Setting[] }
    | { kind: 'setting'; s: Setting }
    | { kind: 'action'; label: string; command: string; icon: string; args?: unknown[] }
    | { kind: 'message'; label: string };

function lastJson<T>(text: string): T | undefined {
    const s = text.trim();
    const at = s.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? s.slice(at + 1) : s) as T;
    } catch {
        return undefined;
    }
}

function show(v: unknown): string {
    if (v === null || v === undefined) {
        return vscode.l10n.t('none');
    }
    if (typeof v === 'boolean') {
        return v ? vscode.l10n.t('on') : vscode.l10n.t('off');
    }
    return String(v);
}

const DOC_ICON: Record<string, string> = { paper: 'book', slides: 'vm', handout: 'mortar-board' };

export class OctavoTree implements vscode.TreeDataProvider<Node>, vscode.Disposable {
    private readonly changed = new vscode.EventEmitter<Node | undefined>();
    readonly onDidChangeTreeData = this.changed.event;
    private configUri?: vscode.Uri;
    private docs?: DocInfo[];
    private settings?: Setting[];
    private analysis?: AnalysisReport | null;       // null = 読めなかった
    private readonly subs: vscode.Disposable[] = [];

    constructor(private readonly log: (s: string) => void) {
        // 設定や原稿が変わったら読み直す（新しい原稿は octavo new で増える）
        const watcher = vscode.workspace.createFileSystemWatcher('**/{octavo.config.py,*.md}');
        this.subs.push(watcher, watcher.onDidCreate(() => this.refresh()),
                       watcher.onDidDelete(() => this.refresh()),
                       vscode.workspace.onDidSaveTextDocument((d) => {
                           if (d.uri.fsPath.endsWith('octavo.config.py')) {
                               this.refresh();
                           } else if (/\.qmd$/i.test(d.uri.fsPath)) {
                               this.refreshAnalysis();      // 保存した .qmd は「古い」になる
                           }
                       }));
    }

    dispose(): void {
        for (const s of this.subs) {
            s.dispose();
        }
        this.changed.dispose();
    }

    refresh(): void {
        this.docs = undefined;
        this.settings = undefined;
        this.analysis = undefined;
        this.changed.fire(undefined);
    }

    /** 分析の状態だけ読み直す（走らせたあと・.qmd を保存したあと）。 */
    refreshAnalysis(): void {
        this.analysis = undefined;
        this.changed.fire(undefined);
    }

    // -- 読む ------------------------------------------------------------
    private async cwd(): Promise<string | undefined> {
        this.configUri = await findConfig();
        return this.configUri ? dirOf(this.configUri) : undefined;
    }

    private async loadDocs(): Promise<DocInfo[] | undefined> {
        const cwd = await this.cwd();
        if (!cwd) {
            return undefined;
        }
        if (!this.docs) {
            const r = await runCapture(cwd, ['documents', '--json'], 30000);
            const got = lastJson<DocumentsReport>(r.stdout);
            if (!got) {
                this.log(`[sidebar] octavo documents --json: ${r.stderr.trim()}`);
            }
            this.docs = got?.documents ?? [];
        }
        return this.docs;
    }

    private async loadSettings(): Promise<Setting[] | undefined> {
        const cwd = await this.cwd();
        if (!cwd) {
            return undefined;
        }
        if (!this.settings) {
            const r = await runCapture(cwd, ['config', '--json'], 30000);
            const got = lastJson<ConfigReport>(r.stdout);
            if (!got) {
                this.log(`[sidebar] octavo config --json: ${r.stderr.trim()}`);
            }
            this.settings = got?.settings ?? [];
        }
        return this.settings;
    }

    private async loadAnalysis(): Promise<AnalysisReport | null | undefined> {
        const cwd = await this.cwd();
        if (!cwd) {
            return undefined;
        }
        if (this.analysis === undefined) {
            const got = await fetchAnalysis(cwd);
            if (!got) {
                this.log('[sidebar] octavo analysis --json returned nothing');
            }
            this.analysis = got ?? null;
        }
        return this.analysis;
    }

    // -- 木 --------------------------------------------------------------
    async getChildren(node?: Node): Promise<Node[]> {
        if (!node) {
            return [{ kind: 'group', id: 'docs' }, { kind: 'group', id: 'analysis' },
                    { kind: 'group', id: 'settings' }, { kind: 'group', id: 'tools' }];
        }
        if (node.kind === 'group' && node.id === 'docs') {
            const docs = await this.loadDocs();
            if (docs === undefined) {
                return [{ kind: 'message', label: vscode.l10n.t('No octavo.config.py in this workspace.') },
                        { kind: 'action', label: vscode.l10n.t('New project'), command: 'octavo.init',
                          icon: 'new-folder' }];
            }
            const rows: Node[] = docs.map((d) => ({ kind: 'doc', doc: d }));
            rows.push({ kind: 'action', label: vscode.l10n.t('Add a manuscript…'),
                        command: 'octavo.new', icon: 'add' });
            return rows;
        }
        if (node.kind === 'doc') {
            return node.doc.parts.map((p) => ({ kind: 'part', doc: node.doc, part: p }));
        }
        if (node.kind === 'group' && node.id === 'analysis') {
            const a = await this.loadAnalysis();
            if (a === undefined) {
                return [{ kind: 'message', label: vscode.l10n.t('No octavo.config.py in this workspace.') }];
            }
            if (a === null) {
                return [{ kind: 'message', label: vscode.l10n.t('Could not read the analysis (see the output).') }];
            }
            if (!a.units.length) {
                return [{ kind: 'message', label: vscode.l10n.t('No analysis (.qmd) is registered.') }];
            }
            const rows: Node[] = a.units.map((u) => ({ kind: 'unit', u }));
            if (!a.quarto) {
                rows.push({ kind: 'message',
                            label: vscode.l10n.t('Quarto is not installed, so nothing can be run (see Diagnose the Environment).') });
            } else if (a.stale) {
                rows.push({ kind: 'action', label: vscode.l10n.t('Run the stale ones ({0})', a.stale),
                            command: 'octavo.analysisRun', icon: 'run-all' });
            }
            return rows;
        }
        if (node.kind === 'group' && node.id === 'settings') {
            const settings = await this.loadSettings();
            if (settings === undefined) {
                return [{ kind: 'message', label: vscode.l10n.t('No octavo.config.py in this workspace.') }];
            }
            const sections: Node[] = [];
            for (const s of settings) {
                const last = sections[sections.length - 1];
                if (last && last.kind === 'section' && last.label === s.section_label) {
                    last.items.push(s);
                } else {
                    sections.push({ kind: 'section', label: s.section_label, items: [s] });
                }
            }
            sections.push({ kind: 'action', label: vscode.l10n.t('Open octavo.config.py'),
                            command: 'octavo.openConfig', icon: 'go-to-file' });
            return sections;
        }
        if (node.kind === 'section') {
            return node.items.map((s) => ({ kind: 'setting', s }));
        }
        if (node.kind === 'group' && node.id === 'tools') {
            return [
                { kind: 'action', label: vscode.l10n.t('Check before submitting (check)'),
                  command: 'octavo.check', icon: 'checklist' },
                { kind: 'action', label: vscode.l10n.t('Run the analysis (analysis run)'),
                  command: 'octavo.analysisRun', icon: 'graph' },
                { kind: 'action', label: vscode.l10n.t('Check the Bibliography (checkbib)'),
                  command: 'octavo.checkbib', icon: 'book' },
                { kind: 'action', label: vscode.l10n.t('Set Up This Project\'s Analysis Environment (env)'),
                  command: 'octavo.envSetup', icon: 'package' },
                { kind: 'action', label: vscode.l10n.t('Diagnose the Environment (doctor)'),
                  command: 'octavo.doctor', icon: 'pulse' },
                { kind: 'action', label: vscode.l10n.t('Install or Update the Tools (setup)'),
                  command: 'octavo.setup', icon: 'tools' },
            ];
        }
        return [];
    }

    getTreeItem(node: Node): vscode.TreeItem {
        const E = vscode.TreeItemCollapsibleState.Expanded;
        const C = vscode.TreeItemCollapsibleState.Collapsed;
        const N = vscode.TreeItemCollapsibleState.None;
        switch (node.kind) {
            case 'group': {
                const label = { docs: vscode.l10n.t('Manuscripts'), analysis: vscode.l10n.t('Analysis'),
                                settings: vscode.l10n.t('Settings'), tools: vscode.l10n.t('Tools') }[node.id];
                return new vscode.TreeItem(label, E);
            }
            case 'doc': {
                const it = new vscode.TreeItem(node.doc.name, node.doc.parts.length ? C : N);
                it.description = node.doc.rel;
                it.iconPath = new vscode.ThemeIcon(DOC_ICON[node.doc.profile] ?? 'file');
                it.contextValue = 'octavo.doc';
                it.tooltip = `${node.doc.rel} · ${node.doc.profile} · ${node.doc.targets.join(', ')}`;
                const uri = resolvePathFromTool(node.doc.src);
                if (uri) {
                    it.resourceUri = uri;
                    it.command = { command: 'vscode.open', title: '', arguments: [uri] };
                }
                return it;
            }
            case 'part': {
                const it = new vscode.TreeItem(node.part.title, N);
                it.description = node.part.name;
                it.iconPath = new vscode.ThemeIcon('symbol-number');
                const uri = resolvePathFromTool(node.doc.src);
                if (uri) {
                    const at = new vscode.Position(Math.max(0, node.part.start_line - 1), 0);
                    it.command = { command: 'vscode.open', title: '',
                                   arguments: [uri, { selection: new vscode.Range(at, at) }] };
                }
                return it;
            }
            case 'unit': {
                const u = node.u;
                const it = new vscode.TreeItem(u.key.split('/').pop() ?? u.key, N);
                const state = !u.exists ? vscode.l10n.t('missing')
                    : u.stale ? vscode.l10n.t('stale') : vscode.l10n.t('up to date');
                it.description = u.manual ? `${state} · ${vscode.l10n.t('manual')}` : state;
                it.iconPath = new vscode.ThemeIcon(!u.exists ? 'error' : u.stale ? 'warning' : 'pass');
                it.tooltip = u.manual
                    ? vscode.l10n.t('{0} — runs only when you run it (manual)', u.key)
                    : u.key;
                it.contextValue = 'octavo.analysisUnit';
                const uri = resolvePathFromTool(u.src);
                if (uri) {
                    it.command = { command: 'vscode.open', title: '', arguments: [uri] };
                }
                return it;
            }
            case 'section':
                return new vscode.TreeItem(node.label, E);
            case 'setting': {
                const it = new vscode.TreeItem(node.s.label, N);
                it.description = show(node.s.value)
                    + (node.s.explicit ? '' : '  ' + vscode.l10n.t('(default)'));
                it.tooltip = `${node.s.key} = ${JSON.stringify(node.s.value)}`;
                it.iconPath = new vscode.ThemeIcon(node.s.explicit ? 'circle-filled' : 'circle-outline');
                it.command = { command: 'octavo.editSetting', title: '', arguments: [node.s] };
                return it;
            }
            case 'action': {
                const it = new vscode.TreeItem(node.label, N);
                it.iconPath = new vscode.ThemeIcon(node.icon);
                it.command = { command: node.command, title: node.label,
                               arguments: node.args ?? [] };
                return it;
            }
            case 'message':
                return new vscode.TreeItem(node.label, N);
        }
    }

    // -- 変える ----------------------------------------------------------
    /** 1つの設定を選ばせて書き換える。値の検査は CLI（confedit.py）がやる。 */
    async edit(s: Setting): Promise<boolean> {
        const back = vscode.l10n.t('Back to the default ({0})', show(s.default));
        let raw: string | null | undefined;          // null = 既定に戻す
        if (s.kind === 'bool' || s.kind === 'choice' || s.kind === 'color') {
            const items: (vscode.QuickPickItem & { raw: string | null | 'ask' })[] = [];
            if (s.kind === 'bool') {
                items.push({ label: vscode.l10n.t('on'), raw: 'true' },
                           { label: vscode.l10n.t('off'), raw: 'false' });
            } else if (s.kind === 'choice') {
                for (const c of s.choices) {
                    items.push({ label: c === null ? vscode.l10n.t('none') : c,
                                 raw: c === null ? 'none' : c });
                }
            } else {
                items.push({ label: vscode.l10n.t('Enter a colour (#RRGGBB)…'), raw: 'ask' },
                           { label: vscode.l10n.t('No accent (plain black)'), raw: 'none' });
            }
            items.push({ label: back, raw: null });
            const picked = await vscode.window.showQuickPick(items, {
                title: `${s.label} (${s.key})`,
                placeHolder: vscode.l10n.t('now: {0}', show(s.value)),
            });
            if (!picked) {
                return false;
            }
            if (picked.raw === 'ask') {
                raw = await vscode.window.showInputBox({
                    title: `${s.label} (${s.key})`,
                    value: typeof s.value === 'string' ? s.value : '#0e2f92',
                    validateInput: (v) => (/^#[0-9a-fA-F]{6}$/.test(v.trim()) ? undefined
                        : vscode.l10n.t('Write it as #RRGGBB')),
                });
                if (raw === undefined) {
                    return false;
                }
            } else {
                raw = picked.raw;
            }
        } else {
            const typed = await vscode.window.showInputBox({
                title: `${s.label} (${s.key})`,
                value: s.value === null || s.value === undefined ? '' : String(s.value),
                prompt: vscode.l10n.t('Leave it empty to go back to the default ({0})',
                                      show(s.default)),
            });
            if (typed === undefined) {
                return false;
            }
            raw = typed.trim() === '' ? null : typed.trim();
        }

        const cwd = await this.cwd();
        if (!cwd) {
            return false;
        }
        const args = raw === null ? ['config', 'unset', s.key, '--json']
                                  : ['config', 'set', s.key, raw, '--json'];
        const r = await runCapture(cwd, args, 30000);
        const got = lastJson<SetReport>(r.stdout);
        if (!got || !got.ok) {
            void vscode.window.showErrorMessage(
                got?.error ?? (r.stderr.trim() || vscode.l10n.t('Could not change {0}.', s.key)));
            return false;
        }
        this.refresh();
        return true;
    }

    async openConfig(): Promise<void> {
        await this.cwd();
        if (this.configUri) {
            await vscode.window.showTextDocument(this.configUri);
        }
    }
}
