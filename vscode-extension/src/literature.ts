// literature.ts — Zotero のコレクションと、Priorwork（先行研究のサーベイ）への受け渡し。
//
// コレクションは octavo.config.py の zotero_collection に持つ（`octavo bib pull` が毎回それを使う）。
// 1つでも、いくつでもよい（1つのテーマのサーベイを、いくつもの論文で使えるように）。Zotero の
// コレクションは木なので、パス（"親 / 子"）で書き、下のコレクションの文献も取る。
// 一覧と書き換えは CLI を通す（`octavo bib collections --json` / `octavo config set`。bib.ts と同じ方針）。
// Zotero が手元で動いていなければ（SSH でつないだサーバーなど）、CLI がウェブ API で読む
// （キーは `octavo bib login` が ~/.config/octavo/ に書く。プロジェクトには入れない）。
// zotero_collection がメイン（.bib になる）、zotero_linked が関連（Priorwork の調査ごとなど。.bib には
// 入れない）。`octavo bib tidy` はメインを原稿の引用とぴったり同じにする計画を出し、プロジェクトで
// zotero_write を許したときだけ、選んだ文献のコレクションの所属を書き換える（文献は消さない）。
// コレクションを作ることはしないので、Zotero で作ってもらい、ここで読み直す。
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

/** メイン（zotero_collection）か関連（zotero_linked）のコレクションの設定 */
export type CollectionKey = 'zotero_collection' | 'zotero_linked';

/** 設定のコレクション（書いていなければ空の並び。メインならライブラリ全体）。 */
export async function currentCollections(cwd: string, key: CollectionKey = 'zotero_collection'): Promise<string[]> {
    const r = await runCapture(cwd, ['config', '--json'], 30000);
    const v = lastJson<ConfigReport>(r.stdout)?.settings.find((s) => s.key === key)?.value;
    return typeof v === 'string' ? [v] : Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [];
}

async function setConfig(cwd: string, key: string, value: string | undefined): Promise<boolean> {
    const args = value === undefined ? ['config', 'unset', key, '--json'] : ['config', 'set', key, value, '--json'];
    const set = lastJson<SetReport>((await runCapture(cwd, args, 30000)).stdout);
    if (!set?.ok) {
        void vscode.window.showErrorMessage(set?.error ?? vscode.l10n.t('Could not change {0}.', key));
        return false;
    }
    return true;
}

function save(cwd: string, names: string[], key: CollectionKey): Promise<boolean> {
    return setConfig(cwd, key, names.length ? (names.length === 1 ? names[0] : JSON.stringify(names)) : undefined);
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
export async function chooseCollection(onChange?: () => void,
                                       key: CollectionKey = 'zotero_collection'): Promise<string[] | undefined> {
    const configUri = await findConfig();
    if (!configUri) {
        void vscode.window.showWarningMessage(vscode.l10n.t('No octavo.config.py in this workspace.'));
        return undefined;
    }
    const cwd = dirOf(configUri);
    const current = await currentCollections(cwd, key);
    const linked = key === 'zotero_linked';
    const title = linked ? vscode.l10n.t('Linked Zotero collections (surveys)')
                         : vscode.l10n.t('Zotero collections for the references');
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
                title,
                prompt: linked ? vscode.l10n.t('The collections, as in Zotero ("parent / child"); several separated by ";".')
                               : vscode.l10n.t('The collections, as in Zotero ("parent / child"); several separated by ";". Empty means the whole library.'),
                value: current.join('; '),
            });
            if (typed === undefined) {
                return undefined;
            }
            const names = typed.split(';').map((x) => x.trim()).filter(Boolean);
            if (await save(cwd, names, key)) {
                onChange?.();
                return names;
            }
            return undefined;
        }
        const cols = got.collections ?? [];
        const result = await browse(cols, current, title, linked
            ? vscode.l10n.t('Choose a folder to open it, and mark the collections of the surveys for this project (the ones under them come too). They never go into the .bib.')
            : vscode.l10n.t('Choose a folder to open it, and mark the collections this project uses (the ones under them come too). Nothing marked means the whole library.'), !linked);
        if (result === undefined) {
            return undefined;
        }
        if (result === 'reload') {
            continue;
        }
        if (result === 'howto') {
            const again = vscode.l10n.t('Reload the list');
            const picked = await vscode.window.showInformationMessage(
                vscode.l10n.t('Octavo does not make collections, so make it in Zotero: right-click "My Library" (or a collection) → New Collection… and name it. Then reload the list.'),
                again);
            if (picked !== again) {
                return undefined;
            }
            continue;
        }
        // 親とその下の両方に印を付けても、親だけでよい（下のコレクションは親に含まれる）
        const names = result.filter((p, _, all) => !all.some((q) => q !== p && p.startsWith(q + ' / ')));
        if (await save(cwd, names, key)) {
            onChange?.();
            return names;
        }
        return undefined;
    }
}

/** `octavo bib tidy --json` の結果 */
interface TidyEntry { key: string; title: string; from: string | string[]; where?: 'linked' | 'library' }
interface TidyReport {
    ok: boolean; error?: string; write?: boolean; main?: string; linked?: string[];
    add?: TidyEntry[]; remove?: TidyEntry[]; unpinned?: TidyEntry[]; not_found?: string[];
    done?: string[]; failed?: { key: string; why: string }[];
}

/**
 * メインのコレクションを、原稿の引用とぴったり同じにする（`octavo bib tidy`）。計画を出して、
 * どの文献を足す・外すかを選んでもらう。プロジェクトが zotero_write を許していなければ、先に尋ねる。
 */
export async function tidyCollection(onChange?: () => void): Promise<void> {
    const configUri = await findConfig();
    if (!configUri) {
        void vscode.window.showWarningMessage(vscode.l10n.t('No octavo.config.py in this workspace.'));
        return;
    }
    const cwd = dirOf(configUri);
    const tidy = (args: string[]): Thenable<TidyReport | undefined> => vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: vscode.l10n.t('Reading Zotero (web API)…') },
        async () => lastJson<TidyReport>((await runCapture(cwd, ['bib', 'tidy', '--json', ...args], 180000)).stdout));
    const plan = await tidy([]);
    if (!plan?.ok) {
        const web = vscode.l10n.t('Use the Web API…');
        const main = vscode.l10n.t('Choose the Main Collection');
        const picked = await vscode.window.showWarningMessage(
            vscode.l10n.t('Cannot tidy the Zotero collection: {0}', plan?.error ?? ''), web, main);
        if (picked === web) {
            await login();
        } else if (picked === main) {
            await chooseCollection(onChange);
        }
        return;
    }
    const leftAlone = [
        plan.unpinned?.length ? vscode.l10n.t('{0} not cited but left alone (citation key not pinned): {1}',
                                              plan.unpinned.length, plan.unpinned.map((x) => x.key).join(', ')) : '',
        plan.not_found?.length ? vscode.l10n.t('{0} cited but nowhere in the Zotero library: {1}',
                                               plan.not_found.length, plan.not_found.join(', ')) : '',
    ].filter(Boolean).join('\n');
    if (!plan.add?.length && !plan.remove?.length) {
        void vscode.window.showInformationMessage(
            vscode.l10n.t('The main collection "{0}" matches the manuscripts.', plan.main ?? ''));
        if (leftAlone) {
            void vscode.window.showWarningMessage(leftAlone);
        }
        return;
    }
    type Pick = vscode.QuickPickItem & { key?: string };
    const items: Pick[] = [];
    if (plan.add?.length) {
        items.push({ label: vscode.l10n.t('Cited but not in the main collection: add'), kind: vscode.QuickPickItemKind.Separator });
        items.push(...plan.add.map((x) => ({ label: `$(add) ${x.key}`, description: x.title,
                                             detail: x.where === 'library'
                                                 ? vscode.l10n.t('from {0} (found outside the linked collections)', String(x.from))
                                                 : vscode.l10n.t('from {0}', String(x.from)),
                                             key: x.key, picked: true })));
    }
    if (plan.remove?.length) {
        items.push({ label: vscode.l10n.t('In the main collection but cited nowhere: take out'), kind: vscode.QuickPickItemKind.Separator });
        items.push(...plan.remove.map((x) => ({ label: `$(remove) ${x.key}`, description: x.title,
                                                detail: vscode.l10n.t('stays in the library and in other collections'),
                                                key: x.key, picked: true })));
    }
    if (leftAlone) {
        void vscode.window.showWarningMessage(leftAlone);
    }
    const chosen = await vscode.window.showQuickPick(items, {
        canPickMany: true,
        title: vscode.l10n.t('Tidy the main Zotero collection "{0}"', plan.main ?? ''),
        placeHolder: vscode.l10n.t('Untick what to leave as it is. Only which collection each entry is in changes; nothing is deleted.'),
    });
    if (!chosen?.length) {
        return;
    }
    if (!plan.write) {
        const allow = vscode.l10n.t('Allow and Change Zotero');
        const picked = await vscode.window.showWarningMessage(
            vscode.l10n.t('This project does not let Octavo change Zotero yet.'),
            { modal: true, detail: vscode.l10n.t('Allowing it writes \'zotero_write\': True in octavo.config.py. Octavo then only adds entries to the main collection and takes them out of it, through the Zotero web API (the API key needs write access); it never deletes or edits an entry.') },
            allow);
        if (picked !== allow || !(await setConfig(cwd, 'zotero_write', 'true'))) {
            return;
        }
        onChange?.();
    }
    const got = await tidy(['--apply', '--keys', chosen.map((x) => x.key).filter(Boolean).join(',')]);
    if (!got?.ok && !got?.done) {
        void vscode.window.showErrorMessage(vscode.l10n.t('Cannot tidy the Zotero collection: {0}', got?.error ?? ''));
        return;
    }
    const pull = vscode.l10n.t('Pull Now');
    const failed = got.failed ?? [];
    const message = vscode.l10n.t('Changed {0} entries in Zotero. Pull the .bib again (a Zotero on this machine needs to sync first).', got.done?.length ?? 0)
        + (failed.length ? ' ' + vscode.l10n.t('Failed: {0}', failed.map((x) => `${x.key} (${x.why})`).join('; ')) : '');
    const picked = await (failed.length ? vscode.window.showWarningMessage(message, pull)
                                        : vscode.window.showInformationMessage(message, pull));
    if (picked === pull) {
        await vscode.commands.executeCommand('octavo.bibPull');
    }
}

/**
 * フォルダをたどって、使うコレクションに印を付ける。いちばん上のフォルダだけを並べ、フォルダを選ぶとその中を
 * 並べる（中にフォルダの無いものは、選ぶと印が付く・外れる）。開いたフォルダそのものは先頭の行で印を付ける。
 * 「決める」で終わる。戻り値: 印を付けたパスの並び、または 'reload' / 'howto'、取り消しは undefined。
 */
async function browse(cols: Collection[], current: string[], title: string, hint: string,
                      noneIsLibrary: boolean): Promise<string[] | 'reload' | 'howto' | undefined> {
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
        qp.title = `${title} — ${flat ? vscode.l10n.t('all folders') : here ? here.path : vscode.l10n.t('My Library')}`;
        qp.placeholder = hint;
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
            ...(selected.size ? [{ label: '$(clear-all) ' + (noneIsLibrary ? vscode.l10n.t('Unmark all (the whole library)')
                                                                              : vscode.l10n.t('Unmark all')),
                                   act: 'clear' } as Item] : []),
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
    const linked = cwd ? await currentCollections(cwd, 'zotero_linked') : [];
    const root = cwd ? lastJson<{ root?: string }>((await runCapture(cwd, ['documents', '--json'], 30000)).stdout)?.root ?? cwd : '';
    const how = await vscode.window.showQuickPick([
        { label: vscode.l10n.t('Make a survey from this manuscript'), detail: vscode.l10n.t('Priorwork reads the manuscript and proposes a draft of its introduction, literature review and hypotheses, or advice on it.'), use: false },
        { label: vscode.l10n.t('Use surveys already in Priorwork'), detail: vscode.l10n.t('Surveys on a topic can serve several papers: link them to this project and write their text with its citation keys.'), use: true },
    ], { title: vscode.l10n.t('Ask Priorwork for the Literature') });
    if (!how) {
        return;
    }
    const coll = collections.map((c) => `"${c}"`).join(', ');
    // 調査の文献はメインに入れず、調査ごとのコレクションに。メインには、原稿が引いたものを Octavo が足す
    const zotero = (coll ? vscode.l10n.t('The project\'s references are the Zotero collection {0}; Octavo adds to it the papers the manuscript cites, so do not put survey papers there.', coll)
                         : vscode.l10n.t('The project has no main Zotero collection yet; ask me which one to use.'))
        + (linked.length ? ' ' + vscode.l10n.t('Its linked collections (surveys) are {0}.', linked.map((c) => `"${c}"`).join(', ')) : '')
        + ' ' + vscode.l10n.t('Gather each survey\'s papers in a Zotero collection of its own; the export names it, and I link it to the project from Octavo.');
    const text = how.use
        ? vscode.l10n.t('With Priorwork, use surveys we already have for my manuscript in {0}, in the Octavo project {1}: list the surveys and propose which fit (wait for my answer), link each to the project (./priorwork scope SURVEY --octavo {1}), and write their text for it (./priorwork export SURVEY --octavo {1}): it goes into the project\'s literature/priorwork/ with its manifest, and I take it into the manuscript from Octavo.', target, root)
          + ' ' + zotero
        : vscode.l10n.t('My manuscript is in {0}, in an Octavo project. With Priorwork, read it (./priorwork read reads the project\'s results and the literature it cites too), then propose what to make from it and wait for my answer: what for (a draft of its introduction, literature review and theory and hypotheses, advice on it such as missing literature, the direction of its citations and the argument, additions to fill in the manuscript in progress, or several of these as separate reports), which parts of the manuscript to cover, and the scope of the searches. Export for Octavo (./priorwork export SURVEY --octavo): it goes into the project\'s literature/priorwork/ with its manifest, and I take it into the manuscript from Octavo. Do not rewrite the manuscript.', target)
          + ' ' + zotero;
    // Priorwork のワークスペースが分かっていれば、依頼をファイルで送る（.priorwork/requests/）。
    // 分からなければ、前と同じくクリップボードに
    const ws = priorworkWorkspace();
    if (ws && cwd) {
        interface AskReport { ok: boolean; id?: string; error?: string }
        const manuscript = doc?.src ?? target;
        const r = await runCapture(cwd, ['priorwork', 'ask', '--workspace', ws,
            '--kind', how.use ? 'use-surveys' : 'start', '--manuscript', manuscript, '--text', text, '--json'], 30000);
        const got = lastJson<AskReport>(r.stdout);
        if (got?.ok) {
            onRequestSent?.();
            void vscode.window.showInformationMessage(vscode.l10n.t(
                'Sent the request to Priorwork. In the Priorwork window, ask for it from "Requests from Octavo" in the sidebar.'));
            return;
        }
        void vscode.window.showWarningMessage(vscode.l10n.t('Could not send it to the Priorwork workspace ({0}); copied it instead.',
                                                            got?.error ?? r.stderr.trim()));
    }
    await vscode.env.clipboard.writeText(text);
    const set = vscode.l10n.t('Set the Priorwork Workspace…');
    const picked = await vscode.window.showInformationMessage(
        vscode.l10n.t('Copied a request for Priorwork. Paste it into your agent\'s chat in the window of your Priorwork workspace.'),
        ...(ws ? [] : [set]));
    if (picked === set) {
        await choosePriorworkWorkspace();
    }
}

/** 依頼を送ったあと（サイドバーを読み直す） */
let onRequestSent: (() => void) | undefined;
export function whenRequestSent(f: () => void): void {
    onRequestSent = f;
}

/** 設定の Priorwork のワークスペース（CLI から見たパス）。無ければ undefined。 */
export function priorworkWorkspace(): string | undefined {
    const v = vscode.workspace.getConfiguration('octavo').get<string>('priorworkWorkspace', '').trim();
    return v || undefined;
}

/** Priorwork のワークスペース（根に .priorwork/ のあるフォルダ）を選んで設定に書く。 */
export async function choosePriorworkWorkspace(): Promise<void> {
    const got = await vscode.window.showOpenDialog({
        canSelectFolders: true, canSelectFiles: false, canSelectMany: false,
        openLabel: vscode.l10n.t('Use This Folder'),
        title: vscode.l10n.t('The Priorwork workspace (the folder with .priorwork/ in it)'),
    });
    if (!got?.length) {
        return;
    }
    try {
        await vscode.workspace.fs.stat(vscode.Uri.joinPath(got[0], '.priorwork'));
    } catch {
        void vscode.window.showWarningMessage(vscode.l10n.t('{0} has no .priorwork/ folder, so it is not a Priorwork workspace.', got[0].fsPath));
        return;
    }
    const p = got[0].fsPath;
    const value = resolveMode() === 'wsl' && /^[A-Za-z]:\\/.test(p) ? toWslPath(p) : p;
    await vscode.workspace.getConfiguration('octavo').update('priorworkWorkspace', value, vscode.ConfigurationTarget.Global);
    void vscode.window.showInformationMessage(vscode.l10n.t('Requests to Priorwork now go to {0}.', value));
    onRequestSent?.();
}

/** `octavo priorwork --json` の1つ（sidebar.ts の Survey と同じ形。ここで読むのは survey と kind だけ） */
interface SurveyRef { survey?: string; kind?: string; text?: string; json: string }

/**
 * 受け取ったサーベイを原稿に取り込む依頼文をコピーする（Octavo のプロジェクトで使うエージェントに貼る）。
 * 取り込み方の約束（提案して答えを待つ、引用はそのまま、受け取り場所は書き換えない）は AGENTS.md にある。
 */
export async function priorworkRequest(s?: SurveyRef): Promise<void> {
    if (!s?.survey) {
        return;
    }
    const text = (s.kind === 'complete'
        ? vscode.l10n.t('Bring the Priorwork additions for my manuscript ({0}, in literature/priorwork/) into the manuscript: find each item\'s place from its "Where" quotation, propose where and how each goes, and wait for my answer before changing anything. Keep the citations as they are.', s.survey)
        : vscode.l10n.t('Bring the Priorwork draft {0} (in literature/priorwork/) into my manuscript: read it with its manifest and the manuscript, propose where and how each part goes, and wait for my answer before changing anything. Keep the citations as they are.', s.survey));
    await vscode.env.clipboard.writeText(text);
    void vscode.window.showInformationMessage(
        vscode.l10n.t('Copied a request. Paste it into your AI assistant\'s chat in this project.'));
}

/** @PRIORWORK:<DOI> を .bib のキーに置き換える（octavo priorwork resolve）。先に何が変わるかを見せる。 */
export async function priorworkResolve(onChange?: () => void): Promise<void> {
    const configUri = await findConfig();
    if (!configUri) {
        return;
    }
    const cwd = dirOf(configUri);
    interface ResolveReport { ok: boolean; replaced: number; left: string[] }
    const dry = lastJson<ResolveReport>((await runCapture(cwd, ['priorwork', 'resolve', '--dry-run', '--json'], 60000)).stdout);
    if (!dry) {
        return;
    }
    if (!dry.replaced) {
        void vscode.window.showInformationMessage(dry.left.length
            ? vscode.l10n.t('None can be replaced yet: put these papers in Zotero and pull the .bib first: {0}', dry.left.join(', '))
            : vscode.l10n.t('There are no Priorwork marks left.'));
        return;
    }
    const go = vscode.l10n.t('Replace');
    const dirty = vscode.workspace.textDocuments.filter((d) => d.isDirty && d.languageId === 'markdown');
    const picked = await vscode.window.showInformationMessage(
        vscode.l10n.t('Replace {0} Priorwork marks with the .bib keys (in the manuscripts and in literature/priorwork/)?', dry.replaced),
        { modal: true, detail: dirty.length ? vscode.l10n.t('Save the open manuscripts first: unsaved edits would clash.') : undefined }, go);
    if (picked !== go || dirty.length) {
        return;
    }
    const done = lastJson<ResolveReport>((await runCapture(cwd, ['priorwork', 'resolve', '--json'], 60000)).stdout);
    void vscode.window.showInformationMessage(vscode.l10n.t('Replaced {0} marks.', done?.replaced ?? 0));
    onChange?.();
}

/** 添え状の Zotero コレクションを関連のコレクション（zotero_linked）に足す（octavo priorwork link）。 */
export async function priorworkLink(survey?: string, onChange?: () => void): Promise<void> {
    const configUri = await findConfig();
    if (!configUri) {
        return;
    }
    interface LinkReport { ok: boolean; added: string[] }
    const got = lastJson<LinkReport>((await runCapture(dirOf(configUri),
        ['priorwork', 'link', ...(survey ? [survey] : []), '--json'], 30000)).stdout);
    void vscode.window.showInformationMessage(got?.added.length
        ? vscode.l10n.t('Linked collections: {0}. octavo bib tidy looks there for papers the manuscripts cite.', got.added.map((c) => `"${c}"`).join(', '))
        : vscode.l10n.t('Nothing to link.'));
    onChange?.();
}
