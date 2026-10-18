// literature.ts — Zotero のコレクションと、Priorwork（先行研究のサーベイ）への受け渡し。
//
// コレクションは octavo.config.py の zotero_collection に持つ（`octavo bib pull` が毎回それを使う）。
// 1つでも、いくつでもよい（1つのテーマのサーベイを、いくつもの論文で使えるように）。Zotero の
// コレクションは木なので、パス（"親 / 子"）で書き、下のコレクションの文献も取る。
// 一覧と書き換えは CLI を通す（`octavo bib collections --json` / `octavo config set`。bib.ts と同じ方針）。
// Zotero が手元で動いていなければ（SSH でつないだサーバーなど）、CLI がウェブ API で読む
// （キーは `octavo bib login` が ~/.config/octavo/ に書く。プロジェクトには入れない）。
// Octavo は Zotero に書き込まないので、コレクションは Zotero で作ってもらい、ここで読み直す。
//
// Priorwork のワークスペースは別のフォルダ（ふつうは別のウィンドウ）なので、拡張機能どうしで
// コマンドは呼べない。代わりに、原稿・プロジェクトのパスと Zotero のコレクションを入れた依頼文を
// コピーし、Priorwork のウィンドウのエージェントに貼ってもらう。
import * as vscode from 'vscode';
import { DocInfo } from './preview';
import { dirOf, findConfig, resolveMode, runCapture, toWslPath } from './runner';

function lastJson<T>(text: string): T | undefined {
    const s = text.trim();
    const at = s.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? s.slice(at + 1) : s) as T;
    } catch {
        return undefined;
    }
}

interface ConfigRow { key: string; value: unknown }
interface ConfigReport { settings: ConfigRow[] }
/** `octavo bib collections --json` の1つ（Zotero と同じ木の順。path は "親 / 子"） */
interface Collection { key: string; name: string; parent: string; path: string; depth: number; items: number }
interface CollectionsReport { ok: boolean; collections?: Collection[]; error?: string }
interface SetReport { ok: boolean; error?: string }

function samePath(a: string, b: string): boolean {
    const norm = (p: string): string => p.split('/').map((x) => x.trim().toLowerCase()).join('/');
    return norm(a) === norm(b);
}

/** 設定の zotero_collection（書いていなければ空の並び = ライブラリ全体）。 */
export async function currentCollections(cwd: string): Promise<string[]> {
    const r = await runCapture(cwd, ['config', '--json'], 30000);
    const v = lastJson<ConfigReport>(r.stdout)?.settings.find((s) => s.key === 'zotero_collection')?.value;
    return typeof v === 'string' ? [v] : Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [];
}

async function save(cwd: string, names: string[]): Promise<boolean> {
    const args = names.length
        ? ['config', 'set', 'zotero_collection', names.length === 1 ? names[0] : JSON.stringify(names), '--json']
        : ['config', 'unset', 'zotero_collection', '--json'];
    const set = lastJson<SetReport>((await runCapture(cwd, args, 30000)).stdout);
    if (!set?.ok) {
        void vscode.window.showErrorMessage(set?.error ?? vscode.l10n.t('Could not change {0}.', 'zotero_collection'));
        return false;
    }
    return true;
}

/** ウェブ API のキーを入れる（`octavo bib login`）。 */
export async function login(): Promise<boolean> {
    const configUri = await findConfig();
    const cwd = configUri ? dirOf(configUri) : undefined;
    if (!cwd) {
        void vscode.window.showWarningMessage(vscode.l10n.t('No octavo.config.py in this workspace.'));
        return false;
    }
    const uid = (await vscode.window.showInputBox({
        title: vscode.l10n.t('Zotero web API (1/2)'),
        prompt: vscode.l10n.t('Your user ID: the number in "Your user ID for use in API calls" at zotero.org/settings/keys'),
        validateInput: (v) => (/^\d+$/.test(v.trim()) ? undefined : vscode.l10n.t('A number.')),
        ignoreFocusOut: true,
    }))?.trim();
    if (!uid) {
        return false;
    }
    const key = (await vscode.window.showInputBox({
        title: vscode.l10n.t('Zotero web API (2/2)'),
        prompt: vscode.l10n.t('An API key that can read your library (zotero.org/settings/keys → Create new private key)'),
        password: true,
        ignoreFocusOut: true,
    }))?.trim();
    if (!key) {
        return false;
    }
    const r = await runCapture(cwd, ['bib', 'login', '--user-id', uid, '--api-key', key], 60000);
    if (r.code !== 0) {
        void vscode.window.showErrorMessage(r.stderr.trim() || vscode.l10n.t('Could not reach the Zotero web API.'));
        return false;
    }
    void vscode.window.showInformationMessage(r.stdout.trim());
    return true;
}

/**
 * コレクションを選んで設定に書く（いくつでも。何も選ばなければライブラリ全体）。
 * 戻り値: 選んだパスの並び、取り消しは undefined。
 */
export async function chooseCollection(onChange?: () => void): Promise<string[] | undefined> {
    const configUri = await findConfig();
    if (!configUri) {
        void vscode.window.showWarningMessage(vscode.l10n.t('No octavo.config.py in this workspace.'));
        return undefined;
    }
    const cwd = dirOf(configUri);
    const current = await currentCollections(cwd);
    for (;;) {
        const r = await vscode.window.withProgress(
            { location: vscode.ProgressLocation.Window, title: vscode.l10n.t('Reading the Zotero collections') },
            () => runCapture(cwd, ['bib', 'collections', '--json'], 60000));
        const got = lastJson<CollectionsReport>(r.stdout);
        if (!got?.ok) {
            // 手元の Zotero もウェブ API も使えない: キーを入れるか、名前を打つ
            const web = vscode.l10n.t('Use the Web API…');
            const type = vscode.l10n.t('Type the Names');
            const retry = vscode.l10n.t('Try Again');
            const picked = await vscode.window.showWarningMessage(
                vscode.l10n.t('Cannot read the Zotero collections: {0}', got?.error ?? r.stderr.trim()),
                { modal: true, detail: vscode.l10n.t('Start Zotero on this machine, or use the Zotero web API (an API key; it works on a server too).') },
                web, retry, type);
            if (picked === web) {
                if (await login()) {
                    continue;
                }
                return undefined;
            }
            if (picked === retry) {
                continue;
            }
            if (picked !== type) {
                return undefined;
            }
            const typed = await vscode.window.showInputBox({
                title: vscode.l10n.t('Zotero collections for the references'),
                prompt: vscode.l10n.t('The collections, as in Zotero ("parent / child"); several separated by ";". Empty means the whole library.'),
                value: current.join('; '),
            });
            if (typed === undefined) {
                return undefined;
            }
            const names = typed.split(';').map((x) => x.trim()).filter(Boolean);
            if (await save(cwd, names)) {
                onChange?.();
                return names;
            }
            return undefined;
        }
        const cols = got.collections ?? [];
        const result = await browse(cols, current);
        if (result === undefined) {
            return undefined;
        }
        if (result === 'reload') {
            continue;
        }
        if (result === 'howto') {
            const again = vscode.l10n.t('Reload the list');
            const picked = await vscode.window.showInformationMessage(
                vscode.l10n.t('Octavo never writes to Zotero, so make the collection there: in Zotero, right-click "My Library" (or a collection) → New Collection… and name it. Then reload the list.'),
                again);
            if (picked !== again) {
                return undefined;
            }
            continue;
        }
        // 親とその下の両方に印を付けても、親だけでよい（下のコレクションは親に含まれる）
        const names = result.filter((p, _, all) => !all.some((q) => q !== p && p.startsWith(q + ' / ')));
        if (await save(cwd, names)) {
            onChange?.();
            return names;
        }
        return undefined;
    }
}

/**
 * フォルダをたどって、使うコレクションに印を付ける。いちばん上のフォルダだけを並べ、フォルダを選ぶとその中を
 * 並べる（中にフォルダの無いものは、選ぶと印が付く・外れる）。開いたフォルダそのものは先頭の行で印を付ける。
 * 「決める」で終わる。戻り値: 印を付けたパスの並び、または 'reload' / 'howto'、取り消しは undefined。
 */
async function browse(cols: Collection[], current: string[]): Promise<string[] | 'reload' | 'howto' | undefined> {
    type Act = 'open' | 'toggle' | 'up' | 'here' | 'done' | 'all' | 'clear' | 'reload' | 'howto';
    type Item = vscode.QuickPickItem & { act: Act; key?: string };
    const byKey = new Map(cols.map((c) => [c.key, c]));
    const children = (key: string): Collection[] => cols.filter((c) => (c.parent || '') === key)
        .sort((a, b) => a.name.localeCompare(b.name));
    const selected = new Set<string>(cols.filter((c) => current.some((n) => samePath(c.path, n)
        || (!n.includes('/') && c.name.toLowerCase() === n.toLowerCase()))).map((c) => c.path));
    for (const n of current) {          // Zotero に見つからない名前も、印として残す
        if (!cols.some((c) => samePath(c.path, n))) {
            selected.add(n);
        }
    }
    const marked = (c: Collection): boolean => selected.has(c.path);
    const below = (c: Collection): boolean => [...selected].some((p) => p.startsWith(c.path + ' / '));
    const icon = (c: Collection): string => marked(c) ? '$(pass-filled) ' : below(c) ? '$(folder-opened) ' : '$(folder) ';
    const describe = (c: Collection): string => {
        const n = children(c.key).length;
        return [vscode.l10n.t('{0} items', c.items), n ? vscode.l10n.t('{0} folders inside', n) : ''].filter(Boolean).join(' · ');
    };
    const qp = vscode.window.createQuickPick<Item>();
    qp.matchOnDescription = true;
    let at = '';
    let flat = false;
    const render = (): void => {
        const here = byKey.get(at);
        qp.title = `${vscode.l10n.t('Zotero collections for the references')} — ${flat ? vscode.l10n.t('all folders') : here ? here.path : vscode.l10n.t('My Library')}`;
        qp.placeholder = vscode.l10n.t('Choose a folder to open it, and mark the collections this project uses (the ones under them come too). Nothing marked means the whole library.');
        qp.buttons = at || flat ? [vscode.QuickInputButtons.Back] : [];
        qp.value = '';
        const done: Item = {
            label: '$(check-all) ' + vscode.l10n.t('Done ({0} marked)', selected.size),
            description: [...selected].join(', '),
            act: 'done',
        };
        if (flat) {
            qp.items = [done, ...cols.map((c) => ({ label: (marked(c) ? '$(pass-filled) ' : '$(folder) ') + c.path,
                                                    description: describe(c), act: 'toggle' as Act, key: c.key }))];
            return;
        }
        qp.items = [
            done,
            ...(here ? [
                { label: '$(arrow-up) ' + vscode.l10n.t('Up'), act: 'up' } as Item,
                { label: (marked(here) ? '$(pass-filled) ' + vscode.l10n.t('Unmark this folder: {0}', here.name)
                                       : '$(circle-large-outline) ' + vscode.l10n.t('Mark this folder: {0}', here.name)),
                  description: describe(here), act: 'here', key: here.key } as Item,
                { label: vscode.l10n.t('Folders inside'), kind: vscode.QuickPickItemKind.Separator, act: 'open' } as Item,
            ] : []),
            ...children(at).map((c) => ({ label: icon(c) + c.name + (children(c.key).length ? '  ›' : ''), description: describe(c),
                                          act: (children(c.key).length ? 'open' : 'toggle') as Act, key: c.key })),
            { label: '', kind: vscode.QuickPickItemKind.Separator, act: 'reload' },
            { label: '$(search) ' + vscode.l10n.t('Search all folders'), description: vscode.l10n.t('by name, with the path'), act: 'all' },
            { label: '$(refresh) ' + vscode.l10n.t('Reload the list (after making a collection in Zotero)'), act: 'reload' },
            { label: '$(question) ' + vscode.l10n.t('How to make a new collection'), act: 'howto' },
            ...(selected.size ? [{ label: '$(clear-all) ' + vscode.l10n.t('Unmark all (the whole library)'), act: 'clear' } as Item] : []),
        ];
    };
    const toggle = (key?: string): void => {
        const c = key ? byKey.get(key) : undefined;
        if (c) {
            if (selected.has(c.path)) {
                selected.delete(c.path);
            } else {
                selected.add(c.path);
            }
        }
    };
    render();
    return new Promise((resolve) => {
        let finished = false;
        const finish = (r: string[] | 'reload' | 'howto' | undefined): void => {
            if (!finished) {
                finished = true;
                resolve(r);
                qp.hide();
            }
        };
        qp.onDidTriggerButton(() => {
            if (flat) {
                flat = false;
            } else {
                at = byKey.get(at)?.parent ?? '';
            }
            render();
        });
        qp.onDidAccept(() => {
            const item = qp.selectedItems[0] ?? qp.activeItems[0];
            if (!item) {
                return;
            }
            switch (item.act) {
                case 'open': at = item.key ?? ''; break;
                case 'up': at = byKey.get(at)?.parent ?? ''; break;
                case 'toggle':
                case 'here': toggle(item.key); break;
                case 'all': flat = true; break;
                case 'clear': selected.clear(); break;
                case 'done': finish([...selected]); return;
                case 'reload': finish('reload'); return;
                case 'howto': finish('howto'); return;
            }
            render();
        });
        qp.onDidHide(() => {
            finish(undefined);
            qp.dispose();
        });
        qp.show();
    });
}

/**
 * Priorwork への依頼文をコピーする。doc はサイドバーの論文（src は実行環境側の絶対パス）。
 * 無ければ、開いている Markdown の原稿。新しくサーベイを作るか、Priorwork にあるサーベイを
 * この論文で使うかを選ぶ（1つのサーベイをいくつもの論文で使うこともある）。
 */
export async function askPriorwork(doc?: DocInfo): Promise<void> {
    let target: string | undefined;
    if (doc) {
        // papers/<名前>/paper.md のように論文ごとのフォルダなら、フォルダごと（付録・main.typ も読む）
        target = doc.rel.includes('/') ? doc.src.replace(/[\\/][^\\/]*$/, '') : doc.src;
    } else {
        const editor = vscode.window.activeTextEditor;
        if (editor?.document.languageId === 'markdown' && editor.document.uri.scheme === 'file') {
            const p = editor.document.uri.fsPath;
            target = resolveMode() === 'wsl' && /^[A-Za-z]:\\/.test(p) ? toWslPath(p) : p;
        }
    }
    if (!target) {
        void vscode.window.showWarningMessage(vscode.l10n.t('Open the manuscript, or right-click a paper in the Octavo sidebar.'));
        return;
    }
    const configUri = await findConfig();
    const cwd = configUri ? dirOf(configUri) : undefined;
    const collections = cwd ? await currentCollections(cwd) : [];
    const root = cwd ? lastJson<{ root?: string }>((await runCapture(cwd, ['documents', '--json'], 30000)).stdout)?.root ?? cwd : '';
    const how = await vscode.window.showQuickPick([
        { label: vscode.l10n.t('Make a survey from this manuscript'), detail: vscode.l10n.t('Priorwork reads the manuscript and proposes a draft of its introduction, literature review and hypotheses, or advice on it.'), use: false },
        { label: vscode.l10n.t('Use surveys already in Priorwork'), detail: vscode.l10n.t('Surveys on a topic can serve several papers: link them to this project and write their text with its citation keys.'), use: true },
    ], { title: vscode.l10n.t('Ask Priorwork for the Literature') });
    if (!how) {
        return;
    }
    const coll = collections.map((c) => `"${c}"`).join(', ');
    const text = how.use
        ? vscode.l10n.t('With Priorwork, use surveys we already have for my manuscript in {0}, in the Octavo project {1}: list the surveys and propose which fit (wait for my answer), link each to the project (./priorwork scope SURVEY --octavo {1}), and write their text for it (./priorwork export SURVEY --octavo {1}).', target, root)
          + ' ' + (coll ? vscode.l10n.t('The project fetches its references from the Zotero collections {0}; tell me if a survey\'s collection is not among them or under them.', coll)
                        : vscode.l10n.t('The project has no Zotero collection yet; tell me which collections to add to it.'))
        : vscode.l10n.t('My manuscript is in {0}, in an Octavo project. With Priorwork, read it (./priorwork read reads the project\'s results and the literature it cites too), then propose what to make from it and wait for my answer: what for (a draft of its introduction, literature review and theory and hypotheses, advice on it such as missing literature, the direction of its citations and the argument, or both as separate reports), which parts of the manuscript to cover, and the scope of the searches. Write drafts for Octavo (./priorwork export --draft --octavo). Do not rewrite the manuscript.', target)
          + ' ' + (coll ? vscode.l10n.t('The project fetches its references from the Zotero collections {0}; link the survey to one of them, or to a collection under one (one for each survey).', coll)
                        : vscode.l10n.t('The project has no Zotero collection yet; ask me which one to use.'));
    await vscode.env.clipboard.writeText(text);
    void vscode.window.showInformationMessage(
        vscode.l10n.t('Copied a request for Priorwork. Paste it into your agent\'s chat in the window of your Priorwork workspace.'));
}
