# -*- coding: utf-8 -*-
"""`octavo ai` — 決まった頼みごと（仕事）を AI に渡して、答えをファイルに受け取る。

Octavo が話すのは OpenAI 互換の口（`<ai_url>/chat/completions`）だけ。Ollama・LM Studio・
llama.cpp の server・vLLM はどれもこれを出すので、手元のモデルもクラウドの API も同じ設定で使える。
モデルを入れる・選ぶ・動かすのはその口の側で、Octavo は何も入れない（標準ライブラリの urllib だけ）。

- **仕事はファイル**（`templates/ai/<名前>.md`。ほかのひな型と同じに、プロジェクトの `templates/ai/`
  とユーザーの `~/.config/octavo/templates/ai/` が同梱のものに勝ち、足せば仕事が増える）。冒頭に
  title・input（text / pdf / image / pdf-pages）・output（書き出す先。{dir} {name} {task}）、本文が AI への指示。
- **原稿は書き換えない。** 答えは output のファイルに書くだけで、どう使うかは人が決める。書き出す
  ファイルの1行目に印（`<!-- octavo ai … -->`）を付け、印のないファイル（自分で書いたもの）と原稿・
  付録は上書きしない。
- **共有できないもの**（`ai_private`。既定は `refs/private/`）は、手元の口（localhost と `ai_allow`）
  にしか送らない。
- 鍵は環境変数 `OCTAVO_AI_KEY` だけから読む（設定ファイルは git に入るので書かない）。
"""
from __future__ import annotations

import base64
import ipaddress
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import __version__
from . import md as mdlib
from . import tmpl
from .i18n import t

IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
               '.gif': 'image/gif'}
INPUTS = ('text', 'pdf', 'image', 'pdf-pages')
# 仕事の冒頭の writing: 原稿を送るときに、その範囲の推敲のルールを添える（rules）か、
# octavo revise の回に分けて1回ずつ頼む（revise）
WRITING = ('rules', 'revise')
PASS = '=== {title} ==='
MARK = '<!-- octavo ai: '
PAGE = '=== page {n} ==='


class AIError(Exception):
    pass


@dataclass
class Task:
    name: str
    title: str
    inputs: tuple
    output: str
    prompt: str
    path: Path
    layer: str = ''
    writing: str = ''                 # '' | rules（推敲のルールを添える）| revise（推敲の回ごとに頼む）


def tasks(root: Path | None = None) -> dict:
    """{名前: Task}。プロジェクト・ユーザー・同梱の templates/ai/ から。"""
    out = {}
    for rel, p in sorted(tmpl.tree(['ai'], root).items()):
        if not rel.endswith('.md') or '/' in rel:
            continue
        name = rel[:-3]
        meta, body = mdlib.split_front_matter(p.read_text(encoding='utf-8'))
        raw = meta.get('input') or ['text']
        inputs = tuple(x for x in ([raw] if isinstance(raw, str) else raw) if x in INPUTS) or ('text',)
        layer = tmpl.resolve(f'ai/{rel}', root)[0]
        writing = str(meta.get('writing') or '').strip().lower()
        out[name] = Task(name, str(meta.get('title') or name), inputs,
                         str(meta.get('output') or 'notes/ai/{name}.{task}.md'), body.strip(), p, layer,
                         writing if writing in WRITING else '')
    return out


# ---------------------------------------------------------------- つなぎ先

@dataclass
class Endpoint:
    url: str
    model: str
    timeout: int
    key: str | None = None
    allow: tuple = ()

    @property
    def local(self) -> bool:
        """手元の口か（localhost・ループバック・ai_allow に書いたもの）。"""
        host = (urllib.parse.urlsplit(self.url).hostname or '').lower()
        if host in ('localhost',) or host in {a.lower() for a in self.allow}:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False


def endpoint(cfg) -> Endpoint:
    """設定と環境変数から。どちらにも口がなければ AIError。"""
    url = os.environ.get('OCTAVO_AI_URL') or cfg['ai_url']
    model = os.environ.get('OCTAVO_AI_MODEL') or cfg['ai_model']
    if not url:
        raise AIError(t('no AI is set: write ai_url (and ai_model) in octavo.config.py, or set '
                        'OCTAVO_AI_URL (for example http://localhost:11434/v1 for Ollama)'))
    if not model:
        raise AIError(t('no AI model is set: write ai_model in octavo.config.py, or set OCTAVO_AI_MODEL'))
    return Endpoint(url.rstrip('/'), model, int(cfg['ai_timeout']),
                    os.environ.get('OCTAVO_AI_KEY') or None, tuple(cfg['ai_allow'] or ()))


def _post(ep: Endpoint, path: str, body: dict) -> dict:
    headers = {'Content-Type': 'application/json', 'User-Agent': f'octavo/{__version__}'}
    if ep.key:
        headers['Authorization'] = f'Bearer {ep.key}'
    req = urllib.request.Request(ep.url + path, data=json.dumps(body).encode('utf-8'),
                                 headers=headers, method='POST')
    return _send(req, ep)


def _send(req, ep: Endpoint) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=ep.timeout) as r:
            return json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')[:300].strip()
        raise AIError(t('the AI at {url} answered {code}: {detail}', url=ep.url, code=e.code,
                        detail=detail or e.reason)) from e
    except (urllib.error.URLError, OSError) as e:
        reason = getattr(e, 'reason', e)
        raise AIError(t('could not reach the AI at {url} ({reason}) — is the server running?',
                        url=ep.url, reason=reason)) from e
    except ValueError as e:
        raise AIError(t('the AI at {url} did not answer in JSON', url=ep.url)) from e


def ask(ep: Endpoint, prompt: str, text: str | None = None, image: tuple | None = None) -> str:
    """1回の問い合わせ。image は (MIME, バイト列)。答えの本文を返す。"""
    content: list | str
    if image is None:
        content = text or ''
    else:
        content = [{'type': 'image_url',
                    'image_url': {'url': f'data:{image[0]};base64,' + base64.b64encode(image[1]).decode('ascii')}}]
        if text:
            content.insert(0, {'type': 'text', 'text': text})
    got = _post(ep, '/chat/completions', {
        'model': ep.model, 'stream': False,
        'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': content}]})
    try:
        return str(got['choices'][0]['message']['content']).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise AIError(t('the AI at {url} answered without a message', url=ep.url)) from e


def check(cfg) -> dict:
    """つなぎ先が答えるか（GET <ai_url>/models）。{url, model, local, ok, models, error}。"""
    try:
        ep = endpoint(cfg)
    except AIError as e:
        return {'url': None, 'model': None, 'local': None, 'ok': False, 'models': [], 'error': str(e)}
    out = {'url': ep.url, 'model': ep.model, 'local': ep.local, 'ok': False, 'models': [], 'error': None}
    headers = {'User-Agent': f'octavo/{__version__}'}
    if ep.key:
        headers['Authorization'] = f'Bearer {ep.key}'
    try:
        got = _send(urllib.request.Request(ep.url + '/models', headers=headers), ep)
        out['models'] = sorted(str(m.get('id')) for m in got.get('data', []) if isinstance(m, dict))
        out['ok'] = True
        if out['models'] and ep.model not in out['models']:
            out['error'] = t('the server does not list the model {model}', model=ep.model)
    except AIError as e:
        out['error'] = str(e)
    return out


# ---------------------------------------------------------------- 入力と出力

@dataclass
class Job:
    task: Task
    source: Path
    kind: str                         # text | pdf | image | pdf-pages
    text: str | None = None
    lines: tuple | None = None        # (始め, 終わり)。原稿の一部だけのとき
    section: str | None = None
    output: Path | None = None
    private: bool = False
    pages: list = field(default_factory=list)      # pdf-pages の画像（バイト列）
    passes: list = field(default_factory=list)     # writing: revise のとき [(見出し, 送る本文)]


def is_private(cfg, path: Path) -> bool:
    root = Path(cfg.root).resolve()
    try:
        rel = path.resolve().relative_to(root).as_posix()
    except ValueError:
        return False
    for p in cfg['ai_private'] or ():
        p = p.replace('\\', '/').strip('/')
        if rel == p or rel.startswith(p + '/'):
            return True
    return False


def _kind(task: Task, path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_TYPES:
        if 'image' not in task.inputs:
            raise AIError(t('the task {task} does not take images (it takes: {kinds})',
                            task=task.name, kinds=', '.join(task.inputs)))
        return 'image'
    if ext == '.pdf':
        for k in ('pdf', 'pdf-pages'):
            if k in task.inputs:
                return k
        raise AIError(t('the task {task} does not take PDFs (it takes: {kinds})',
                        task=task.name, kinds=', '.join(task.inputs)))
    if 'text' not in task.inputs:
        raise AIError(t('the task {task} does not take text files (it takes: {kinds})',
                        task=task.name, kinds=', '.join(task.inputs)))
    return 'text'


def _pdf_text(path: Path) -> str:
    tool = shutil.which('pdftotext')
    if not tool:
        raise AIError(t('reading a PDF needs pdftotext (poppler-utils / poppler)'))
    r = subprocess.run([tool, '-enc', 'UTF-8', '-layout', str(path), '-'], capture_output=True)
    text = r.stdout.decode('utf-8', 'replace').strip()
    if r.returncode or not text:
        raise AIError(t('{file} has no text to read (a scan? transcribe it with the ocr task first)',
                        file=path.name))
    return text


def _pdf_pages(path: Path) -> list:
    tool = shutil.which('pdftoppm')
    if not tool:
        raise AIError(t('reading the pages of a PDF needs pdftoppm (poppler-utils / poppler)'))
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([tool, '-r', '150', '-png', str(path), str(Path(d) / 'page')], capture_output=True)
        if r.returncode:
            raise AIError(t('pdftoppm could not read {file}', file=path.name))
        return [p.read_bytes() for p in sorted(Path(d).glob('page*.png'),
                                                 key=lambda p: int(re.sub(r'\D', '', p.stem) or 0))]


def _manuscripts(cfg) -> set:
    out = set()
    for d in cfg.documents.values():
        out.add(Path(d.src).resolve())
        if d.appendix:
            out.add(Path(d.appendix).resolve())
    return out


def output_path(cfg, task: Task, source: Path, section: str | None = None) -> Path:
    root = Path(cfg.root)
    try:
        rel_dir = source.resolve().parent.relative_to(root.resolve()).as_posix()
    except ValueError:
        rel_dir = source.resolve().parent.as_posix()
    name = source.stem + (f'.{section}' if section else '')
    pattern = task.output.replace('{dir}', rel_dir).replace('{name}', name).replace('{task}', task.name)
    p = Path(pattern)
    return (p if p.is_absolute() else root / p).resolve()


def prepare(cfg, task: Task, source: Path, lines: tuple | None = None, section: str | None = None,
            out: Path | None = None, force: bool = False) -> Job:
    """送るものを揃える（まだ送らない）。書き出し先が自分のファイル・原稿なら AIError。"""
    source = Path(source)
    if not source.is_file():
        raise AIError(t('no such file: {file}', file=source))
    kind = _kind(task, source)
    job = Job(task, source, kind, lines=lines, section=section, private=is_private(cfg, source))
    if kind == 'text':
        text = source.read_text(encoding='utf-8', errors='replace')
        if section:
            from . import translation as trmod
            found = {s.key: s for s in trmod.sections(text)}
            if section not in found:
                raise AIError(t('no section {key} in {file} (sections: {keys})', key=section,
                                file=cfg.rel(source), keys=', '.join(found) or t('none')))
            text = found[section].text
        elif lines:
            a, b = lines
            text = '\n'.join(text.split('\n')[a - 1:b])
        job.text = text
        if task.writing:
            _with_writing(cfg, job, source, lines, section)
    elif kind == 'pdf':
        job.text = _pdf_text(source)
    job.output = Path(out).resolve() if out else output_path(cfg, task, source, section)
    if job.output in _manuscripts(cfg) or job.output == source.resolve():
        raise AIError(t('{file} is a manuscript (or the file sent); octavo ai never writes over it',
                        file=cfg.rel(job.output)))
    if job.output.is_file() and not force and not job.output.read_text(
            encoding='utf-8', errors='replace').startswith(MARK):
        raise AIError(t('{file} is already there and octavo ai did not write it — pass --out, or --force '
                        'to replace it', file=cfg.rel(job.output)))
    return job


def _with_writing(cfg, job: Job, source: Path, lines, section) -> None:
    """原稿なら、推敲のルール（octavo revise と同じもの）を添えるか、回に分ける。"""
    from . import revise as revmod
    from . import writing as writingmod
    doc = writingmod.doc_for_file(cfg, source)
    if doc is None:
        return
    got = revmod.collect(cfg, doc)
    rel = cfg.rel(source)
    if section:
        from . import translation as trmod
        found = {s.key: s for s in trmod.sections(source.read_text(encoding='utf-8', errors='replace'))}
        s = found[section]
        lines = (s.line, s.line + s.text.count('\n'))
    if job.task.writing == 'rules':
        rules = revmod.rules_text(got, rel, lines)
        if rules:
            job.text = rules + '\n# ' + t('Text') + '\n\n' + job.text
    else:
        job.passes = [(p['title'], p['text']) for p in revmod.passes(got, rel, lines, every=True)]


def run(cfg, job: Job, ep: Endpoint, say=lambda s: None) -> str:
    """送って、答えを job.output に書く。書いた本文を返す。"""
    if job.private and not ep.local:
        raise AIError(t('{file} is in {where}, which is sent only to an AI on this machine (localhost, or '
                        'ai_allow); {url} is not', file=job.source.name,
                        where=', '.join(cfg['ai_private']), url=ep.url))
    say(t('asking {model} at {url} ({task}) …', model=ep.model, url=ep.url, task=job.task.name))
    if job.kind == 'image':
        answer = ask(ep, job.task.prompt, image=(IMAGE_TYPES[job.source.suffix.lower()], job.source.read_bytes()))
    elif job.kind == 'pdf-pages':
        pages = _pdf_pages(job.source)
        parts = []
        for n, png in enumerate(pages, 1):
            say(t('page {n} of {total}', n=n, total=len(pages)))
            parts.append(PAGE.format(n=n) + '\n\n' + ask(ep, job.task.prompt, image=('image/png', png)))
        answer = '\n\n'.join(parts)
    elif job.passes:
        parts = []
        for n, (title, text) in enumerate(job.passes, 1):
            say(t('pass {n} of {total}', n=n, total=len(job.passes)))
            parts.append(PASS.format(title=title) + '\n\n' + ask(ep, job.task.prompt, text=text))
        answer = '\n\n'.join(parts)
    else:
        answer = ask(ep, job.task.prompt, text=job.text)
    where = cfg.rel(job.source) + (f' {job.section}' if job.section else '') \
        + (f' lines {job.lines[0]}-{job.lines[1]}' if job.lines else '')
    head = (f'{MARK}{job.task.name} | {where} | {ep.model} | '
            f'{datetime.now().isoformat(timespec="seconds")} -->\n\n')
    job.output.parent.mkdir(parents=True, exist_ok=True)
    job.output.write_text(head + answer.rstrip() + '\n', encoding='utf-8')
    return answer
