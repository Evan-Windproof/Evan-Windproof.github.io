"""Generate only owned blog artifacts; preserve the existing desktop and projects."""
from pathlib import Path
import argparse, datetime as dt, email.utils, html, json, re, xml.etree.ElementTree as ET
import hashlib, unicodedata
import markdown, yaml, bleach
from pygments.formatters import HtmlFormatter
ROOT=Path(__file__).resolve().parents[1]
BASE='https://evanwindproof.top'
PAGE_SIZE = 12
def esc(s): return html.escape(str(s),quote=True)
def tag_key(name):
    return unicodedata.normalize('NFC', name.strip()).casefold()

def tag_id(key):
    if len(key) <= 80 and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', key):
        return key
    return 'u_' + hashlib.sha256(key.encode('utf-8')).hexdigest()

def tag_url(name):
    return f'/blog/tags/{tag_id(tag_key(name))}/'

def tag_links(names):
    if not names:
        return ''
    links = ''.join(f'<a class="tag-link" href="{tag_url(name)}">{esc(name.strip())}</a>' for name in names)
    return f'<div class="tag-list">{links}</div>'

def load_posts():
    posts=[]; seen=set()
    for file in sorted((ROOT/'content/blog').rglob('*.md')):
        source = file.read_text()
        if not source.strip():
            continue  # An empty placeholder is not a publishable article.
        parts=source.split('---',2)
        if len(parts)!=3 or parts[0].strip(): raise ValueError(f'Missing front matter: {file}')
        meta=yaml.safe_load(parts[1]); required={'title','description','date','updated','tags','category','slug','draft','language'}
        if not required<=meta.keys(): raise ValueError(f'Missing metadata: {file}')
        if type(meta['draft']) is not bool or not isinstance(meta['tags'],list): raise ValueError('Invalid draft/tags')
        slug=meta['slug']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug) or slug in seen or slug == 'tags': raise ValueError('Invalid/duplicate slug')
        seen.add(slug)
        for key in ['date','updated']: meta[key]=dt.date.fromisoformat(str(meta[key])).isoformat()
        if meta['updated']<meta['date']: raise ValueError('updated precedes date')
        if meta['draft']: continue
        if not all(isinstance(tag, str) for tag in meta['tags']):
            raise ValueError(f'Tags must be strings: {file}')
        unique_tags = {}
        for tag in meta['tags']:
            if key := tag_key(tag):
                unique_tags.setdefault(key, tag)
        meta['tags'] = list(unique_tags.values())
        md=markdown.Markdown(extensions=['fenced_code','tables','toc','codehilite'],extension_configs={'codehilite':{'guess_lang':False}})
        body=md.convert(parts[2])
        # Keep only static reading markup, safe URLs, and highlight/anchor attributes.
        body=bleach.clean(body,tags=['p','h1','h2','h3','h4','h5','h6','a','img','table','thead','tbody','tr','th','td','pre','code','span','div','ul','ol','li','blockquote','hr','br','strong','em'],attributes={'*':['id','class'],'a':['href','title'],'img':['src','alt','title']},protocols=['http','https','mailto'],strip=True)
        posts.append(dict(meta,body=body,toc=md.toc if md.toc_tokens else '',url=f'/blog/{slug}/',
                          source_path=file.relative_to(ROOT).as_posix()))
    return sorted(posts,key=lambda p:(p['date'],p['slug']),reverse=True)
def shell(title,desc,path,body,language='zh-CN',article=False):
    return f'''<!doctype html><html lang="{esc(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} — Evan Windproof</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{BASE}{path}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{BASE}{path}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:site_name" content="Evan Windproof"><link rel="alternate" type="application/rss+xml" title="Evan Windproof RSS" href="/rss.xml"><link rel="icon" type="image/svg+xml" href="/assets/favicon.svg"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/blog/blog.css"><script src="/locales/zh-CN.js" defer></script><script src="/locales/zh-TW.js" defer></script><script src="/locales/en.js" defer></script><script src="/js/i18n.js" defer></script><script src="/blog/blog.js" defer></script><!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "89b901650704455ebd95dfcc68e9c488"}}'></script><!-- End Cloudflare Web Analytics --></head><body class="blog-body"><header class="blog-header"><a href="/" data-i18n="backDesktop">返回桌面</a><nav><a href="/blog/">Blog</a><a href="/blog/tags/" data-i18n="blogTags">标签</a><a href="/rss.xml">RSS</a></nav><label><span data-i18n="language">Language / 语言</span><select id="blog-language"><option value="zh-CN">简体中文</option><option value="zh-TW">繁體中文</option><option value="en">English</option></select></label><button id="blog-theme" data-i18n="appearance">外观</button></header><main class="blog-main">{body}</main><footer class="blog-footer"><a href="https://github.com/Evan-Windproof">Evan Windproof</a> · Personal Technology Blog · <a href="/">Evavind Desktop</a> · <a href="mailto:evan.windproof@tutanota.de" aria-label="Email Evan Windproof">evan.windproof@tutanota.de</a></footer></body></html>'''
def card(p):
    return f'<article class="post-card" data-search="{esc(" ".join([p["title"],p["description"],p["category"],*p["tags"]]))}"><time datetime="{p["date"]}">{p["date"]}</time><h2><a href="{p["url"]}">{esc(p["title"])}</a></h2><p>{esc(p["description"])}</p><p class="muted">{esc(p["category"])}</p>{tag_links(p["tags"])}</article>'
def page_path(base, number):
    return base if number == 1 else f'{base}page/{number}/'


def pagination(base, current, pages, count):
    if pages <= 1:
        return ''
    links = []
    if current > 1:
        links.append(f'<a rel="prev" href="{page_path(base, current - 1)}#article-list" data-i18n="blogPrevPage">上一页</a>')
    numbers = sorted({1, pages, *range(max(1, current - 1), min(pages, current + 1) + 1)})
    previous = 0
    for number in numbers:
        if number - previous == 2:
            links.append(f'<a href="{page_path(base, previous + 1)}#article-list">{previous + 1}</a>')
        elif number - previous > 2:
            links.append('<span aria-hidden="true">…</span>')
        if number == current:
            links.append(f'<span aria-current="page">{number}</span>')
        else:
            links.append(f'<a href="{page_path(base, number)}#article-list">{number}</a>')
        previous = number
    if current < pages:
        links.append(f'<a rel="next" href="{page_path(base, current + 1)}#article-list" data-i18n="blogNextPage">下一页</a>')
    return (f'<nav class="blog-pagination" aria-label="文章分页" data-i18n-aria-label="blogPagination">{"".join(links)}'
            f'<span class="pagination-count" data-post-count="{count}">共 {count} 篇文章</span></nav>')


def write_listing(base, title, description, heading, posts):
    pages = max(1, (len(posts) + PAGE_SIZE - 1) // PAGE_SIZE)
    paths = []
    for number in range(1, pages + 1):
        path = page_path(base, number)
        start = (number - 1) * PAGE_SIZE
        cards = ''.join(map(card, posts[start:start + PAGE_SIZE]))
        body = (heading
                + '<label class="search-label"><span data-i18n="blogSearch">搜索文章</span><input id="blog-search" type="search"></label>'
                + f'<section id="article-list" tabindex="-1" data-list-base="{base}" data-page-size="{PAGE_SIZE}" data-page-count="{pages}">'
                + '<p id="search-empty" role="status" hidden data-i18n="noPosts">没有匹配的文章</p>'
                + '<p id="search-error" role="status" hidden data-i18n="blogSearchError">无法加载文章索引</p>'
                + f'<div id="article-cards">{cards}</div><div id="article-pagination">{pagination(base, number, pages, len(posts))}</div></section>')
        target = ROOT / path.lstrip('/') / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        page_title = title if number == 1 else f'{title} · Page {number}'
        target.write_text(shell(page_title, description, path, body))
        paths.append(path)
    return paths


def write_tags(out, posts):
    groups = {}
    ids = {}
    for post in posts:
        for name in post['tags']:
            key = tag_key(name)
            identifier = tag_id(key)
            if ids.setdefault(identifier, key) != key:
                raise ValueError(f'Tag URL collision: {name}')
            groups.setdefault(key, (name.strip(), []))[1].append(post)

    root = out / 'tags'
    root.mkdir(exist_ok=True)
    overview = ['<h1 data-i18n="blogTags">标签</h1>']
    paths = ['/blog/tags/']
    overview.append('<div class="tag-list">')
    for key, (name, articles) in sorted(groups.items()):
        url = tag_url(name)
        overview.append(f'<a class="tag-link" href="{url}">{esc(name)} <span class="tag-count">({len(articles)})</span></a>')
        heading = f'<a href="/blog/tags/" data-i18n="blogAllTags">所有标签</a><h1>{esc(name)}</h1>'
        paths.extend(write_listing(url, name, f'Articles tagged {name}', heading, articles))
    overview.append('</div>')
    if not groups:
        overview.append('<p data-i18n="blogNoTags">暂无标签</p>')
    (root / 'index.html').write_text(shell('Tags', 'Browse articles by tag.', paths[0], ''.join(overview)))
    return paths

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
        toc=f'<details open class="toc"><summary data-i18n="contents">目录</summary>{p["toc"]}</details>' if p['toc'] else ''
        body=f'<a href="/blog/" data-i18n="backBlog">返回博客首页</a><article lang="{esc(p["language"])}"><header><h1>{esc(p["title"])}</h1><p><time datetime="{p["date"]}">{p["date"]}</time> · <span data-i18n="updated">更新</span> {p["updated"]}</p><p>{esc(p["category"])}</p>{tag_links(p["tags"])}<p class="muted">{esc(p["description"])}</p></header>{toc}<div class="prose">{p["body"]}</div></article><nav class="post-nav">{"".join(links)}</nav>'
        target=out/p['slug']/'index.html';target.parent.mkdir(exist_ok=True);target.write_text(shell(p['title'],p['description'],p['url'],body,p['language'],True));files.append(str(target.relative_to(ROOT)))
    heading = ('<p class="eyebrow">SYSTEMS / CODE / OPEN SOURCE</p><h1>Evan Windproof</h1>'
               '<p data-i18n="blogIntro">独立技术博客：操作系统、系统编程与开源实验。</p>')
    listing_paths = write_listing('/blog/', 'Personal Technology Blog',
                                  '操作系统、C / C++ / Rust 系统编程、开源项目与开发笔记。', heading, posts)
    tag_paths = write_tags(out, posts)
    files.extend(path.lstrip('/') + 'index.html' for path in listing_paths + tag_paths)
    manifest.write_text(json.dumps(files,indent=2))
    fields = ('title', 'description', 'date', 'slug', 'url', 'category', 'tags', 'language')
    index = [dict({key: post[key] for key in fields}, tagUrls=[tag_url(tag) for tag in post['tags']])
             for post in posts]
    (out/'articles.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    rss=ET.Element('rss',version='2.0');channel=ET.SubElement(rss,'channel')
    for k,v in [('title','Evan Windproof — Personal Technology Blog'),('link',BASE+'/blog/'),('description','Systems programming, operating systems and open-source notes.')]:ET.SubElement(channel,k).text=v
    for p in posts:
        item=ET.SubElement(channel,'item')
        for k,v in [('title',p['title']),('link',BASE+p['url']),('guid',BASE+p['url']),('description',p['description']),('pubDate',email.utils.format_datetime(dt.datetime.fromisoformat(p['date']).replace(tzinfo=dt.timezone.utc)))]: ET.SubElement(item,k).text=v
    ET.ElementTree(rss).write(ROOT/'rss.xml',encoding='utf-8',xml_declaration=True)
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns);sitemap=ET.Element('{'+ns+'}urlset')
    for path in ['/','/blog/','/projects/hooftty/']+[p['url'] for p in posts]+listing_paths[1:]+tag_paths:ET.SubElement(ET.SubElement(sitemap,'{'+ns+'}url'),'{'+ns+'}loc').text=BASE+path
    ET.ElementTree(sitemap).write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    (ROOT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    latest='<section class="latest-posts" aria-label="Latest articles"><h2 data-i18n="latestPosts">最新文章</h2>'+''.join(f'<a href="{p["url"]}"><time>{p["date"]}</time> {esc(p["title"])}</a>' for p in posts[:3])+'</section>'
    home=ROOT/'index.html';text=home.read_text();text=re.sub(r'<!-- latest:start -->.*?<!-- latest:end -->','<!-- latest:start -->'+latest+'<!-- latest:end -->',text,flags=re.S);home.write_text(text)
    (out/'highlight.css').write_text(HtmlFormatter().get_style_defs('.codehilite'))
    print(f'Built {len(posts)} published posts')
    return posts

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--indexnow-manifest', type=Path)
    parser.add_argument('--commit')
    args = parser.parse_args()
    if bool(args.indexnow_manifest) != bool(args.commit):
        parser.error('--indexnow-manifest and --commit must be provided together')
    posts = build()
    if args.indexnow_manifest:
        import indexnow_manifest
        args.indexnow_manifest.write_bytes(
            indexnow_manifest.encode(indexnow_manifest.generate(posts, BASE, args.commit))
        )
