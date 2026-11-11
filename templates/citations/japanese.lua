--[[
日本語の文書の引用と書誌（octavo build が --citeproc の代わりに使う）。

pandoc の citeproc は、書誌全体を1つの言語で組む。日本語（ja-JP）で組むと英語の文献まで
「Smith ほか (2003年)」になり、英語で組むと日本語の文献が「山田 and 田中」になる。
日本語で投稿する雑誌の多くは、欧文献と和文献に別の書き方を決めている。そこで:

  - 本文の中の引用と英語の文献は、選んだ書式（CSL）を英語（en-US）の決まりで使う
  - 本文の中の引用は、漢字・かなの名前をつなぐ and / & を「・」に、et al. を「ほか」にする
  - 日本語の文献（.bib の langid = {japanese}、CSL の language が ja で始まるもの）の書誌は、
    書式にかかわらず、ここで .bib の中身から次の形に組み直す:

      論文      山田太郎・田中花子（2020）「題」『誌名』12（3）: 1–20.
      本        佐藤一郎（2018）『題』出版社.
      本の章    加藤五郎（2015）「章の題」中村六郎編『書名』出版社, 10–20.
      その他    著者（年）「題」『載っているもの』出版社. https://…

    形は設定の japanese_citation_form で選ぶ。形の部品（著者と年、題の括弧、巻・号・頁、終わり）は
    citations/japanese-forms.json と設定の japanese_citation_forms にあり、octavo build が
    文書のメタデータ octavo-ja-<部品> で届ける。ここには形を持たない。組み込みの形:
      standard   上の形（既定）
      fullwidth  山田太郎・田中花子（2020）「題」『誌名』12巻3号、1–20頁。
                 （『年報行政研究』に掲載された論文の文献一覧に多い形）
      period     山田太郎・田中花子．2020．「題」『誌名』12巻3号、1–20頁。
                 （『年報政治学』に掲載された論文の文献一覧に見られる形）
    どちらの雑誌も投稿規程で文献の書き方を決めてはいない。投稿先の指示があればそれに従う。

文書の言語（lang）は変えない。組むあいだだけ en-US にして、あとで戻す。
]]

local stringify = pandoc.utils.stringify
local CJK = '[\227-\233]'    -- UTF-8 で かな・漢字 の先頭バイト（E3-E9）

local function is_cjk_end(s)
  return s:match(CJK .. '[\128-\191][\128-\191][,.]?$') ~= nil
end

local function is_cjk_start(s)
  return s:match('^' .. CJK) ~= nil
end

-- 本文の中の引用: 漢字・かなの名前に挟まれた and / & / ,（3人以上）を ・ に、et al. を ほか に
local function join_names(inls)
  local out = pandoc.List()
  local i = 1
  while i <= #inls do
    local a, handled = inls[i], false
    if a.t == 'Str' and is_cjk_end(a.text) and inls[i + 1] and inls[i + 1].t == 'Space' then
      local text, b = a.text, inls[i + 2]
      if b and b.t == 'Str' and (b.text == 'and' or b.text == '&') and inls[i + 3]
         and inls[i + 3].t == 'Space' and inls[i + 4] and inls[i + 4].t == 'Str'
         and is_cjk_start(inls[i + 4].text) then
        inls[i + 4] = pandoc.Str(text:gsub(',$', '') .. '・' .. inls[i + 4].text)
        i, handled = i + 4, true
      elseif text:match(',$') and b and b.t == 'Str' and is_cjk_start(b.text) then
        inls[i + 2] = pandoc.Str(text:gsub(',$', '') .. '・' .. b.text)
        i, handled = i + 2, true
      elseif b and b.t == 'Str' and b.text == 'et' and inls[i + 3] and inls[i + 3].t == 'Space'
             and inls[i + 4] and inls[i + 4].t == 'Str' and inls[i + 4].text:match('^al%.') then
        inls[i + 4] = pandoc.Str(text .. 'ほか' .. inls[i + 4].text:sub(4))
        i, handled = i + 4, true
      end
    end
    if not handled then
      out:insert(a)
      i = i + 1
    end
  end
  return out
end

-- ---------------------------------------------------------------- 日本語の文献の書誌

local function field(item, key)
  local v = item[key]
  if v == nil then return nil end
  local s = stringify(v)
  if s == '' then return nil end
  return s
end

local function person(p)
  if p.literal then return stringify(p.literal) end
  local family, given = stringify(p.family or ''), stringify(p.given or '')
  if (family .. given):match(CJK) then return family .. given end
  return given ~= '' and (given .. ' ' .. family) or family   -- 日本語の文献に混じる欧文の名前
end

local function people(list)
  if not list or #list == 0 then return nil end
  local names = {}
  for _, p in ipairs(list) do names[#names + 1] = person(p) end
  return table.concat(names, '・')
end

local function pages(item)
  local p = field(item, 'page')
  return p and (p:gsub('%-%-?', '–')) or nil
end

-- citeproc が付けた年（同じ著者・同じ年なら 2020a / 2020b）を、組んだ項目から拾う
local function year_of(item, rendered)
  local y = rendered:match('(%d%d%d%d%l?)')
  if y then return y end
  local dp = item.issued and item.issued['date-parts']
  if dp and dp[1] and dp[1][1] then return tostring(dp[1][1]) end
  return 'n.d.'
end

-- 形の部品。octavo/jaforms.py::FIELDS と同じ並び
local PARTS = { 'head', 'article_title', 'book_title', 'container', 'editor', 'volume', 'issue',
                'issue_alone', 'pages', 'pages_sep', 'chapter_pages', 'stop' }

local function form_of(meta)
  local f = {}
  for _, k in ipairs(PARTS) do
    local v = meta['octavo-ja-' .. k:gsub('_', '-')]
    f[k] = v and stringify(v) or ''
  end
  return f
end

-- 差し込み口 {name} を埋める。値のない口が1つでもあれば ''（jaforms.fill と同じ）
local function fill(pattern, slots)
  local missing = false
  local out = pattern:gsub('{(%w+)}', function(name)
    local v = slots[name]
    if v == nil or v == '' then missing = true; return '' end
    return v
  end)
  return missing and '' or out
end

local function japanese_entry(item, rendered, f)
  local who, eds = people(item.author), people(item.editor)
  local kind = item.type or ''
  local title = field(item, 'title') or ''
  local container, publisher = field(item, 'container-title'), field(item, 'publisher')
  local vol, issue, pp = field(item, 'volume'), field(item, 'issue'), pages(item)

  if not who and eds then who, eds = fill(f.editor, { editor = eds }), nil end
  -- 著者と年は、著者がなくても出す（年だけでも項目の頭になる）
  local s = f.head:gsub('{(%w+)}', { author = who or '', year = year_of(item, rendered) })
  local box = fill(f.container, { container = container })
  if kind == 'book' or (kind == 'thesis' and not container) then
    s = s .. fill(f.book_title, { title = title }) .. (publisher or '')
  elseif kind == 'chapter' or kind == 'paper-conference' or kind == 'entry-encyclopedia' then
    s = s .. fill(f.article_title, { title = title }) .. fill(f.editor, { editor = eds })
    s = s .. box .. (publisher or '') .. fill(f.chapter_pages, { pages = pp })
  else
    s = s .. fill(f.article_title, { title = title }) .. box
    local v = fill(f.volume, { volume = vol })
    v = v .. (v ~= '' and fill(f.issue, { issue = issue }) or fill(f.issue_alone, { issue = issue }))
    local p = fill(f.pages, { pages = pp })
    s = s .. v .. ((v ~= '' and p ~= '') and f.pages_sep or '') .. p
    if not container and publisher then s = s .. publisher end
  end
  s = s .. f.stop
  local doi = field(item, 'doi') or field(item, 'DOI')
  local url = field(item, 'url') or field(item, 'URL')
  if doi then
    s = s .. ' https://doi.org/' .. doi:gsub('^https?://doi%.org/', '')
  elseif url then
    s = s .. ' ' .. url
  end
  return s
end

function Pandoc(doc)
  local form = form_of(doc.meta)
  local lang = doc.meta.lang
  doc.meta.lang = pandoc.MetaString('en-US')
  doc = pandoc.utils.citeproc(doc)
  doc.meta.lang = lang

  local ja = {}
  for _, item in ipairs(pandoc.utils.references(doc)) do
    local l = item.language and stringify(item.language) or ''
    if l:match('^ja') then ja['ref-' .. item.id] = item end
  end

  return doc:walk({
    Cite = function(c)
      -- 名前は link-citations の Link の中にもある
      return c:walk({ Inlines = join_names })
    end,
    Div = function(d)
      local item = ja[d.identifier]
      if item then
        d.content = { pandoc.Para(pandoc.Inlines(japanese_entry(item, stringify(d), form))) }
        return d
      end
    end,
  })
end
