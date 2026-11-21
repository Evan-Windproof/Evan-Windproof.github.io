"""Generate only owned blog artifacts; preserve the existing desktop and projects."""
from pathlib import Path
import datetime as dt, email.utils, html, json, re, xml.etree.ElementTree as ET
import markdown, yaml, bleach
from pygments.formatters import HtmlFormatter
ROOT=Path(__file__).resolve().parents[1]
BASE='https://evan.v-1.top'
def esc(s): return html.escape(str(s),quote=True)
def load_posts():
    posts=[]; seen=set()
    for file in sorted((ROOT/'content/blog').rglob('*.md')):
        parts=file.read_text().split('---',2)
        if len(parts)!=3 or parts[0].strip(): raise ValueError(f'Missing front matter: {file}')
        meta=yaml.safe_load(parts[1]); required={'title','description','date','updated','tags','category','slug','draft','language'}
        if not required<=meta.keys(): raise ValueError(f'Missing metadata: {file}')
        if type(meta['draft']) is not bool or not isinstance(meta['tags'],list): raise ValueError('Invalid draft/tags')
        slug=meta['slug']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug) or slug in seen: raise ValueError('Invalid/duplicate slug')
        seen.add(slug)
        for key in ['date','updated']: meta[key]=dt.date.fromisoformat(str(meta[key])).isoformat()
        if meta['updated']<meta['date']: raise ValueError('updated precedes date')
        if meta['draft']: continue
        md=markdown.Markdown(extensions=['fenced_code','tables','toc','codehilite'],extension_configs={'codehilite':{'guess_lang':False}})
        body=md.convert(parts[2])
        # Keep only static reading markup, safe URLs, and highlight/anchor attributes.
        body=bleach.clean(body,tags=['p','h1','h2','h3','h4','h5','h6','a','img','table','thead','tbody','tr','th','td','pre','code','span','div','ul','ol','li','blockquote','hr','br','strong','em'],attributes={'*':['id','class'],'a':['href','title'],'img':['src','alt','title']},protocols=['http','https','mailto'],strip=True)
        posts.append(dict(meta,body=body,toc=md.toc,url=f'/blog/{slug}/'))
    return sorted(posts,key=lambda p:(p['date'],p['slug']),reverse=True)
def shell(title,desc,path,body,language='zh-CN',article=False):
    return f'''<!doctype html><html lang="{esc(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} — Evan Windproof</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{BASE}{path}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{BASE}{path}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:site_name" content="Evan Windproof"><link rel="alternate" type="application/rss+xml" title="Evan Windproof RSS" href="/rss.xml"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/blog/blog.css"><script src="/locales/zh-CN.js" defer></script><script src="/locales/zh-TW.js" defer></script><script src="/locales/en.js" defer></script><script src="/js/i18n.js" defer></script><script src="/blog/blog.js" defer></script></head><body class="blog-body"><header class="blog-header"><a href="/">Evan Windproof</a><nav><a href="/blog/">Blog</a><a href="/rss.xml">RSS</a><a href="/C-Skeleton/">C-Skeleton</a></nav><label><span data-i18n="language">Language / 语言</span><select id="blog-language"><option value="zh-CN">简体中文</option><option value="zh-TW">繁體中文</option><option value="en">English</option></select></label><button id="blog-theme" data-i18n="appearance">外观</button></header><main class="blog-main">{body}</main><footer class="blog-footer">Evan Windproof · Personal Technology Blog · <a href="/">Evavind Desktop</a></footer></body></html>'''
def card(p):
    return f'<article class="post-card" data-search="{esc(" ".join([p["title"],p["description"],p["category"],*p["tags"]]))}"><time datetime="{p["date"]}">{p["date"]}</time><h2><a href="{p["url"]}">{esc(p["title"])}</a></h2><p>{esc(p["description"])}</p><p class="muted">{esc(p["category"])} · {esc(" / ".join(p["tags"]))}</p></article>'
def build():
    posts=load_posts(); out=ROOT/'blog'; out.mkdir(exist_ok=True)
    # Remove only paths previously owned by this generator.
    manifest=out/'.generated.json'
    if manifest.exists():
        for path in json.loads(manifest.read_text()):
            target=ROOT/path
            if target.is_relative_to(out) and target.name=='index.html': target.unlink(missing_ok=True)
    files=[]
    for i,p in enumerate(posts):
        links=[]
        for idx,label in [(i+1,'previousPost'),(i-1,'nextPost')]:
            if 0<=idx<len(posts): links.append(f'<a href="{posts[idx]["url"]}"><span data-i18n="{label}">{"上一篇" if idx>i else "下一篇"}</span>：{esc(posts[idx]["title"])}</a>')
        body=f'<a href="/blog/" data-i18n="backBlog">返回博客首页</a><article lang="{esc(p["language"])}"><header><h1>{esc(p["title"])}</h1><p><time datetime="{p["date"]}">{p["date"]}</time> · <span data-i18n="updated">更新</span> {p["updated"]}</p><p>{esc(p["category"])} · {esc(" / ".join(p["tags"]))}</p><p class="muted">{esc(p["description"])}</p></header><details open class="toc"><summary data-i18n="contents">目录</summary>{p["toc"]}</details><div class="prose">{p["body"]}</div></article><nav class="post-nav">{"".join(links)}</nav>'
        target=out/p['slug']/'index.html';target.parent.mkdir(exist_ok=True);target.write_text(shell(p['title'],p['description'],p['url'],body,p['language'],True));files.append(str(target.relative_to(ROOT)))
    listing='<p class="eyebrow">SYSTEMS / CODE / OPEN SOURCE</p><h1>Evan Windproof</h1><p data-i18n="blogIntro">独立技术博客：操作系统、系统编程与开源实验。</p><label class="search-label"><span data-i18n="blogSearch">搜索文章</span><input id="blog-search" type="search"></label><p id="search-empty" hidden data-i18n="noPosts">没有匹配的文章</p>'+''.join(map(card,posts))
    (out/'index.html').write_text(shell('Personal Technology Blog','操作系统、C / C++ / Rust 系统编程、开源项目与开发笔记。','/blog/',listing))
    manifest.write_text(json.dumps(files,indent=2))
    rss=ET.Element('rss',version='2.0');channel=ET.SubElement(rss,'channel')
    for k,v in [('title','Evan Windproof — Personal Technology Blog'),('link',BASE+'/blog/'),('description','Systems programming, operating systems and open-source notes.')]:ET.SubElement(channel,k).text=v
    for p in posts:
        item=ET.SubElement(channel,'item')
        for k,v in [('title',p['title']),('link',BASE+p['url']),('guid',BASE+p['url']),('description',p['description']),('pubDate',email.utils.format_datetime(dt.datetime.fromisoformat(p['date']).replace(tzinfo=dt.timezone.utc)))]: ET.SubElement(item,k).text=v
    ET.ElementTree(rss).write(ROOT/'rss.xml',encoding='utf-8',xml_declaration=True)
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns);sitemap=ET.Element('{'+ns+'}urlset')
    for path in ['/','/blog/']+[p['url'] for p in posts]:ET.SubElement(ET.SubElement(sitemap,'{'+ns+'}url'),'{'+ns+'}loc').text=BASE+path
    ET.ElementTree(sitemap).write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    (ROOT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    latest='<section class="latest-posts" aria-label="Latest articles"><h2 data-i18n="latestPosts">最新文章</h2>'+''.join(f'<a href="{p["url"]}"><time>{p["date"]}</time> {esc(p["title"])}</a>' for p in posts[:3])+'</section>'
    home=ROOT/'index.html';text=home.read_text();text=re.sub(r'<!-- latest:start -->.*?<!-- latest:end -->','<!-- latest:start -->'+latest+'<!-- latest:end -->',text,flags=re.S);home.write_text(text)
    (out/'highlight.css').write_text(HtmlFormatter().get_style_defs('.codehilite'))
    print(f'Built {len(posts)} published posts')
if __name__=='__main__':build()
