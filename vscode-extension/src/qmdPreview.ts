// qmdPreview.ts — .qmd を開いたとき、その分析の**いまある HTML**（Quarto が書き出したもの）を
// エディタの右に出す。
//
// 既定では「見せるだけ」: .qmd を保存しても組み直さない（分析の実行は analysis.ts の
// ボタンか `octavo analysis run`。重い推定が保存のたびに走るのを避けるため）。設定
// octavo.qmdPreviewOnSave をオンにすると、地の文だけが変わった保存では `octavo analysis prose` が
// コードを実行せずに組み直す（判断は CLI がする）。実行が
// 終わって HTML が書き換わったら、出ている画面を読み直す。画面が出ていなくても、その .qmd が
// エディタに見えていれば開く（実行は結果を見たいという意思表示なので、自分で閉じたあとでも開く）。
//
// 出すのは Octavo のプロジェクトの中の .qmd だけ（Quarto だけを使っている .qmd には出ない）。
// HTML は `embed-resources: true`（新しい .qmd の既定）で1枚に収まっている前提。
// 画面を自分で閉じたら、その .qmd を開き直すまで出さない（タブを閉じて開き直すか、別の .qmd へ
// 移るか、タイトルバーの「HTML を表示」で出る）。HTML がまだないときは、その旨の画面を出す。
// 原稿のカーソルの位置へ、画面もスクロールする（PDF のプレビューと同じ。設定 octavo.previewFollowCursor。
// 行の頭の文字を HTML の文字の中から探す）。
// Quarto 拡張機能のプレビュー（Preview ボタン）の画面が出ているあいだは、自動では出さない。
// 出たらこちらを閉じる（同じ HTML が2つ並ばないように）。検知は、その画面（webview の viewType
// quarto.previewView）だけで行う。ターミナル「Quarto Preview」は見ない: 画面が見えないまま
// ターミナルだけが残る場合（トンネル接続など）に、どちらのプレビューも見られなくなるため。
import * as path from 'path';
import * as vscode from 'vscode';
import { dirOf, findConfig } from './runner';
import { plainText, samePath } from './preview';
import { renderProse } from './analysis';

const isQmd = (p: string): boolean => /\.qmd$/i.test(p);
const htmlOf = (qmd: string): string => qmd.replace(/\.qmd$/i, '.html');

/** Quarto のプレビューの画面が出ているか。 */
export function quartoPreviewShown(): boolean {
    return vscode.window.tabGroups.all.some((g) => g.tabs.some((tab) =>
        tab.input instanceof vscode.TabInputWebview && /quarto\.previewView$/.test(tab.input.viewType)));
}

export class QmdPreview implements vscode.Disposable {
    private panel?: vscode.WebviewPanel;
    private current?: string;            // いま映している .qmd
    private closedByUser?: string;       // 自分で閉じた .qmd（開き直すまで出さない）
    private reloadTimer?: NodeJS.Timeout;
    private readonly subs: vscode.Disposable[] = [];

    constructor(private readonly log: (s: string) => void,
                private readonly analysisRunning: () => boolean = () => false) {
        const watcher = vscode.workspace.createFileSystemWatcher('**/*.html');
        const changed = (u: vscode.Uri): void => this.onHtmlChanged(u.fsPath);
        this.subs.push(
            watcher, watcher.onDidChange(changed), watcher.onDidCreate(changed),
            vscode.window.onDidChangeActiveTextEditor((e) => void this.onEditor(e)),
            vscode.window.onDidChangeTextEditorSelection((e) => this.onCursor(e)),
            vscode.workspace.onDidSaveTextDocument((d) => void this.onSave(d)),
            vscode.window.tabGroups.onDidChangeTabs(() => {
                this.forgetClosedIfTabGone();
                this.onQuartoChange();
            }),
        );
        void this.onEditor(vscode.window.activeTextEditor);
    }

    dispose(): void {
        clearTimeout(this.reloadTimer);
        clearTimeout(this.syncTimer);
        this.disposing = true;
        for (const s of this.subs) {
            s.dispose();
        }
        this.panel?.dispose();
    }

    private quarto = false;

    /** 手で閉じた記録は、その .qmd のタブがなくなったら消す（開き直せば、また出る）。 */
    private forgetClosedIfTabGone(): void {
        const closed = this.closedByUser;
        if (closed && !vscode.window.tabGroups.all.some((g) => g.tabs.some((tab) =>
            tab.input instanceof vscode.TabInputText && samePath(tab.input.uri.fsPath, closed)))) {
            this.closedByUser = undefined;
        }
    }

    /** Quarto のプレビューの画面が出たらこちらを閉じ、消えたら（.qmd を開いていれば）出し直す。 */
    private onQuartoChange(): void {
        const running = quartoPreviewShown();
        if (running === this.quarto) {
            return;
        }
        this.quarto = running;
        if (running && this.panel) {
            this.closingForQuarto = true;    // 利用者が閉じたことにしない（onDidDispose が読む）
            this.panel.dispose();
            this.log("[qmd] Quarto's preview is showing: closed the HTML view");
        } else if (!running) {
            this.closedByUser = undefined;
            void this.onEditor(vscode.window.activeTextEditor);
        }
    }

    private get enabled(): boolean {
        return vscode.workspace.getConfiguration('octavo').get<boolean>('qmdPreview', true);
    }

    /** Octavo のプロジェクトの中の .qmd か。 */
    private async inProject(fsPath: string): Promise<boolean> {
        const config = await findConfig(vscode.Uri.file(fsPath));
        if (!config) {
            return false;
        }
        const root = dirOf(config).replace(/\\/g, '/').replace(/\/+$/, '');
        const p = fsPath.replace(/\\/g, '/');
        return p.toLowerCase().startsWith(root.toLowerCase() + '/');
    }

    private async onEditor(editor: vscode.TextEditor | undefined): Promise<void> {
        // 画面（webview）にフォーカスが移ったときは editor が undefined になる。何もしない
        if (!editor) {
            return;
        }
        const p = editor.document.uri.fsPath;
        if (!isQmd(p)) {
            this.closedByUser = undefined;
            return;
        }
        // 手で出した画面（設定がオフ、Quarto の画面が出ている）は、移った先の .qmd についていく
        if (!this.panel && !this.enabled) {
            return;
        }
        if (!this.panel && quartoPreviewShown()) {
            this.log(`[qmd] ${this.fileName(p)}: Quarto's preview is showing, so the HTML view stays closed`);
            return;
        }
        if (samePath(this.closedByUser, p)) {
            this.log(`[qmd] ${this.fileName(p)}: you closed the HTML view (Show the HTML in the title bar brings it back)`);
            return;
        }
        this.closedByUser = undefined;
        if (samePath(this.current, p) && this.panel) {
            return;
        }
        if (!(await this.inProject(p))) {
            return;
        }
        await this.show(p);
    }

    // -- 保存で組み直す（設定がオンのときだけ） --------------------------
    private rendering = false;
    private readonly savedAgain = new Map<string, vscode.TextDocument>();

    private async onSave(doc: vscode.TextDocument): Promise<void> {
        const p = doc.uri.fsPath;
        if (!isQmd(p) || this.analysisRunning()
            || !vscode.workspace.getConfiguration('octavo').get<boolean>('qmdPreviewOnSave', false)) {
            return;
        }
        // 組み直している間に保存されたら、終わってからファイルごとに1度だけ組み直す
        // （「すべて保存」では何本も続けて来る。別のプロジェクトのものもあるので、そのファイルから探す）
        if (this.rendering) {
            this.savedAgain.set(p, doc);
            return;
        }
        const config = await findConfig(doc.uri);
        if (!config || !(await this.inProject(p))) {
            return;
        }
        this.rendering = true;
        const wait = vscode.window.setStatusBarMessage('$(sync~spin) ' + vscode.l10n.t('Octavo: updating the HTML…'));
        try {
            const cwd = dirOf(config);
            const got = await renderProse(cwd, path.relative(cwd, p).split(path.sep).join('/'));
            if (got?.status === 'skipped') {
                this.log(`[qmd] ${got.message}`);
            } else if (got?.status === 'failed') {
                this.log(`[qmd] ${got.message}`);
                void vscode.window.showWarningMessage(vscode.l10n.t('Octavo: could not update the HTML. See the Octavo output.'));
            } else if (got) {
                this.log(`[qmd] ${got.message}`);
                vscode.window.setStatusBarMessage(`Octavo: ${got.message}`, 8000);
            }
        } finally {
            wait.dispose();
            this.rendering = false;
        }
        const [next] = this.savedAgain.entries();
        if (next) {
            this.savedAgain.delete(next[0]);
            await this.onSave(next[1]);
        }
    }

    // -- カーソルに合わせてスクロール ------------------------------------
    private syncTimer?: NodeJS.Timeout;
    private lastSyncLine = -1;

    private onCursor(e: vscode.TextEditorSelectionChangeEvent): void {
        if (!this.panel || !this.current || !samePath(this.current, e.textEditor.document.uri.fsPath)) {
            return;
        }
        if (!vscode.workspace.getConfiguration('octavo').get<boolean>('previewFollowCursor', true)) {
            return;
        }
        // 矢印キーを押しっぱなしにしたときに追いかけ続けないように、少し待つ
        clearTimeout(this.syncTimer);
        this.syncTimer = setTimeout(() => this.syncNow(e.textEditor.document), 150);
    }

    private syncNow(doc: vscode.TextDocument): void {
        const editor = vscode.window.activeTextEditor;
        if (!this.panel || !editor || editor.document !== doc) {
            return;
        }
        const line = editor.selection.active.line;
        if (line === this.lastSyncLine) {
            return;                         // 同じ行の中で動いただけなら、画面は動かさない
        }
        this.lastSyncLine = line;
        const lines: string[] = [];
        for (let i = 0; i < doc.lineCount; i++) {
            lines.push(doc.lineAt(i).text);
        }
        void this.panel.webview.postMessage({
            type: 'sync',
            needles: qmdNeedles(lines, line),
            ratio: line / Math.max(1, doc.lineCount - 1),
        });
    }

    private onHtmlChanged(htmlPath: string): void {
        const shownNow = this.panel && this.current && samePath(htmlOf(this.current), htmlPath);
        const opened = shownNow ? undefined : this.editorOfHtml(htmlPath);
        if (!shownNow && !opened) {
            return;
        }
        // 書き出しの途中を読まないように、少し待ってから読む
        clearTimeout(this.reloadTimer);
        this.reloadTimer = setTimeout(() => void (async () => {
            if (shownNow) {
                await this.show(this.current!, true);
            } else if (opened && this.enabled && !quartoPreviewShown() && await this.inProject(opened)) {
                this.closedByUser = undefined;
                await this.show(opened);
            }
        })(), 400);
    }

    /**
     * いま書かれた HTML の .qmd がエディタに見えていれば、そのパス。画面が別の .qmd を
     * 映しているときは、まとめて実行しても画面が次々に替わらないよう、作業中の .qmd に限る。
     */
    private editorOfHtml(htmlPath: string): string | undefined {
        const editors = this.panel
            ? [vscode.window.activeTextEditor].flatMap((e) => (e ? [e] : []))
            : vscode.window.visibleTextEditors;
        return editors.map((e) => e.document.uri.fsPath)
            .find((p) => isQmd(p) && samePath(htmlOf(p), htmlPath));
    }

    /** タイトルバーの「HTML を表示」。自動で出さない理由（手で閉じた・設定・Quarto の画面）を超えて出す。 */
    async showNow(uri?: vscode.Uri): Promise<void> {
        const p = uri?.fsPath ?? vscode.window.activeTextEditor?.document.uri.fsPath ?? this.current;
        if (!p || !isQmd(p)) {
            void vscode.window.showInformationMessage(vscode.l10n.t('Open a .qmd file first.'));
            return;
        }
        this.closedByUser = undefined;
        await this.show(p);
        this.panel?.reveal(undefined, true);
    }

    private fileName(p: string): string {
        return p.replace(/\\/g, '/').split('/').pop() ?? p;
    }

    private async show(qmd: string, reload = false): Promise<void> {
        const uri = vscode.Uri.file(htmlOf(qmd));
        let text: string | undefined;
        try {
            text = Buffer.from(await vscode.workspace.fs.readFile(uri)).toString('utf-8');
        } catch {
            text = undefined;
        }
        const name = this.fileName(qmd);
        if (!this.panel) {
            this.panel = vscode.window.createWebviewPanel(
                'octavo.qmdPreview', htmlOf(name), { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true },
                // enableFindWidget: 画面をクリックして Ctrl+F（Mac は Cmd+F）で文字列を探せる。
                // retainContextWhenHidden が要る（付けている）
                { enableScripts: true, retainContextWhenHidden: true, enableFindWidget: true });
            this.panel.onDidDispose(() => {
                if (this.current && !this.disposing && !this.closingForQuarto) {
                    this.closedByUser = this.current;
                }
                this.closingForQuarto = false;
                this.panel = undefined;
            });
        }
        this.current = qmd;
        this.lastSyncLine = -1;
        this.panel.title = htmlOf(name);
        this.panel.webview.html = text === undefined
            ? this.notRendered(name)
            : withPreviewScript(text, qmd);
        if (!reload) {
            this.log(`[qmd] ${htmlOf(name)}`);
        }
    }

    private disposing = false;
    private closingForQuarto = false;

    private notRendered(name: string): string {
        const msg = vscode.l10n.t('{0} has no HTML yet. Run the analysis (the ▶ button in the title bar) and the result appears here. A .qmd that makes no HTML has nothing to show: the setting octavo.qmdPreview turns this view off.', name);
        const esc = msg.replace(/&/g, '&amp;').replace(/</g, '&lt;');
        return `<!DOCTYPE html><html><body style="font-family:var(--vscode-font-family);`
            + `color:var(--vscode-foreground);padding:24px"><p>${esc}</p></body></html>`;
    }
}

/**
 * カーソルの行 → HTML の中で探す文字列の候補（その行の頭、なければ直前の見出し）。
 * .qmd は Markdown の本文とコードのチャンク（```）が混ざる。チャンクの中の行は、そのコードの
 * 頭（echo があれば HTML にも出る）。`#|` で始まる行（チャンクの設定）と先頭の YAML は HTML に
 * 出ないので探さない。見出しはチャンクの外のものだけ（コードの `# コメント` は見出しではない）。
 */
export function qmdNeedles(lines: string[], line: number): string[] {
    let fence = false;
    let yaml = lines.length > 0 && lines[0].trim() === '---';
    let heading = '';
    let here = '';
    for (let i = 0; i <= line && i < lines.length; i++) {
        const t = lines[i];
        if (yaml) {
            if (i > 0 && /^(---|\.\.\.)\s*$/.test(t)) {
                yaml = false;
            }
            continue;
        }
        if (/^\s*(```|~~~)/.test(t)) {
            fence = !fence;
            continue;
        }
        if (fence) {
            const code = t.trim();
            if (i === line && !code.startsWith('#|') && code.length >= 3) {
                here = code.slice(0, 24);
            }
            continue;
        }
        if (/^#{1,6}\s+\S/.test(t)) {
            heading = plainText(t);
        }
        if (i === line) {
            here = plainText(t);
        }
    }
    const out: string[] = [];
    for (const n of [here, heading]) {
        if (n.length >= 3 && !out.includes(n)) {
            out.push(n);
        }
    }
    return out;
}

// 画面に足す1枚のスクリプト（acquireVsCodeApi は1回しか呼べないので、全部ここに入れる）。
//  - 読み直しても同じ場所に残るように、スクロール位置を覚える（webview の state）
//  - 原稿のカーソルの行に合わせてスクロールする（{type:'sync', needles, ratio}）:
//    needles の頭の文字を HTML の文字の中から探し、同じ文が何か所かあるときは、原稿の位置の
//    割合に近いものを取る。見つからなければ割合だけで合わせる。折りたたんだ所（見えない所）は
//    候補にしない。すでに見える位置（上から 12%〜80%）なら動かさない（PDF のプレビューと同じ）。
//  - 日本語の id へのページ内リンク（目次など）を飛べるようにする。VS Code は webview の window で
//    クリックを受け、href の文字列と a.hash が同じときだけページ内リンクとして扱う。a.hash は
//    パーセントエンコードされるので、日本語では一致せず、外部リンクとして渡されて何も起きない。
//    一致しないリンクだけここで飛び、window へ伝えない（一致するものは VS Code に任せる）。
//    document の bubble で受けるので、Quarto や Bootstrap がリンクに付けた処理は先に動く。
// JS の正規表現の \ をそのまま残すため String.raw。バッククォートと ${ は使わないこと。
const PAGE_SCRIPT = String.raw`(function(){
var vs=acquireVsCodeApi();var K=__KEY__;
var s=vs.getState();
if(s&&s.k===K){window.addEventListener('load',function(){window.scrollTo(0,s.y||0);});}
var t;window.addEventListener('scroll',function(){clearTimeout(t);
t=setTimeout(function(){vs.setState({k:K,y:window.scrollY});},100);});
function norm(x){return x.normalize('NFKC').toLowerCase().replace(/\s+/g,'');}
var idx=null;
function build(){
  var text='',nodes=[],offs=[];
  var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
    var p=n.parentNode;if(!p)return 2;var tn=p.nodeName;
    return(tn==='SCRIPT'||tn==='STYLE'||tn==='NOSCRIPT')?2:1;}});
  var n;
  while((n=w.nextNode())){
    var v=n.nodeValue;
    for(var i=0;i<v.length;){
      var ch=String.fromCodePoint(v.codePointAt(i));var c=norm(ch);
      for(var j=0;j<c.length;j++){nodes.push(n);offs.push(i);}
      text+=c;i+=ch.length;
    }
  }
  idx={len:document.body.textContent.length,text:text,nodes:nodes,offs:offs};
}
function hidden(el){
  // 閉じた <details>（Quarto の code-fold）の中は、見出し（summary）以外は見えない
  for(var d=el.closest('details');d;d=d.parentElement&&d.parentElement.closest('details')){
    if(!d.open){var sm=el.closest('summary');if(!(sm&&sm.parentNode===d))return true;}
  }
  return false;
}
function yOf(at){
  var n=idx.nodes[at];var o=idx.offs[at];
  if(n.parentElement&&hidden(n.parentElement))return null;
  var r=document.createRange();
  try{r.setStart(n,o);r.setEnd(n,Math.min(o+1,n.nodeValue.length));}catch(e){return null;}
  var rs=r.getClientRects();
  if(!rs.length||(rs[0].width===0&&rs[0].height===0))return null;
  return rs[0].top+window.scrollY;
}
function apply(m){
  if(!idx||idx.len!==document.body.textContent.length)build();
  var ratio=Math.min(1,Math.max(0,m.ratio||0));
  var total=Math.max(1,document.documentElement.scrollHeight);
  var y=null;
  var needles=m.needles||[];
  for(var k=0;k<needles.length&&y===null;k++){
    var nd=norm(needles[k]);if(nd.length<3)continue;
    var best=null,at=-1;
    while((at=idx.text.indexOf(nd,at+1))>=0){
      var yy=yOf(at);if(yy===null)continue;
      var d=Math.abs(yy/total-ratio);
      if(best===null||d<best.d)best={y:yy,d:d};
    }
    if(best)y=best.y;
  }
  if(y===null)y=ratio*Math.max(0,total-window.innerHeight)+window.innerHeight*0.3;
  var rel=y-window.scrollY;
  if(rel<window.innerHeight*0.12||rel>window.innerHeight*0.8){
    window.scrollTo(0,Math.max(0,y-window.innerHeight*0.3));
  }
}
window.addEventListener('message',function(e){var m=e.data;if(m&&m.type==='sync')apply(m);});
document.addEventListener('click',function(e){
  var a=e.target&&e.target.closest?e.target.closest('a[href^="#"]'):null;
  if(!a)return;
  var h=a.getAttribute('href');
  if(h==='#'||h===a.hash)return;
  e.preventDefault();e.stopPropagation();
  var id=h.slice(1);
  try{id=decodeURIComponent(id);}catch(x){}
  var el=document.getElementById(h.slice(1))||document.getElementById(id);
  if(el)el.scrollIntoView();
});
})();`;

export function withPreviewScript(html: string, key: string): string {
    const script = '<script>' + PAGE_SCRIPT.replace('__KEY__', () => JSON.stringify(key)) + '</script>';
    return /<\/body>/i.test(html) ? html.replace(/<\/body>/i, () => script + '</body>') : html + script;
}
