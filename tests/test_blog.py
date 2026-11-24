"""Protect publication boundaries independently of the example article."""
import importlib.util, tempfile, unittest, xml.etree.ElementTree as ET
from pathlib import Path
spec=importlib.util.spec_from_file_location('build',Path(__file__).resolve().parents[1]/'scripts/build_blog.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
class BlogPublication(unittest.TestCase):
 def test_publication(self):
  original=build.ROOT
  with tempfile.TemporaryDirectory() as folder:
   try:
    build.ROOT=Path(folder);content=build.ROOT/'content/blog';content.mkdir(parents=True)
    (build.ROOT/'index.html').write_text('<!-- latest:start --><!-- latest:end -->')
    (content/'placeholder.md').write_text('\n')
    for slug,draft in [('first',False),('second',False),('private-draft',True)]:
     (content/(slug+'.md')).write_text(f'''---
title: 'Title & <example>'
description: 'A & B <summary>'
date: 2026-11-21
updated: 2026-11-21
tags: [C]
category: Test
slug: {slug}
draft: {str(draft).lower()}
language: zh-CN
---
## Header
<script>alert(1)</script>
[bad](javascript:alert(1))
''')
    for slug, tags in [('first', '[Gecko, gecko, 中文, "C++", C, " "]'), ('second', '[GECKO]'), ('private-draft', '[Secret, Gecko]')]:
     source=content/(slug+'.md')
     source.write_text(source.read_text().replace('tags: [C]', 'tags: '+tags))
    build.build()
    rss=ET.parse(build.ROOT/'rss.xml');self.assertEqual(len(rss.findall('./channel/item')),2)
    self.assertEqual(rss.findtext('./channel/item/title'),'Title & <example>')
    for file in ['rss.xml','sitemap.xml','blog/index.html','index.html']:
     self.assertNotIn('private-draft',(build.ROOT/file).read_text())
    overview=(build.ROOT/'blog/tags/index.html').read_text()
    self.assertIn('>GECKO <span class="tag-count">(2)',overview)
    self.assertNotIn('Secret',overview)
    self.assertEqual(len(list((build.ROOT/'blog/tags').glob('*/index.html'))),4)
    archive=(build.ROOT/'blog/tags/gecko/index.html').read_text()
    self.assertLess(archive.index('/blog/second/'),archive.index('/blog/first/'))
    for tag in ['中文','C++','C','Gecko']:
     url=build.tag_url(tag)
     self.assertTrue((build.ROOT/url.lstrip('/')/'index.html').exists())
     self.assertIn(build.BASE+url,(build.ROOT/'sitemap.xml').read_text())
    index=build.json.loads((build.ROOT/'blog/articles.json').read_text())
    self.assertEqual([post['slug'] for post in index],['second','first'])
    self.assertEqual(index[1]['tags'],['Gecko','中文','C++','C'])
    article=(build.ROOT/'blog/first/index.html').read_text();self.assertNotIn('<script>alert',article);self.assertNotIn('href="javascript:',article);self.assertIn('/blog/second/',article)
    with_toc=article
    self.assertIn('<details open class="toc">',with_toc)
    self.assertIn('href="#header"',with_toc)
    rss_before=(build.ROOT/'rss.xml').read_bytes()
    source=content/'first.md'
    source.write_text(source.read_text().replace('## Header', 'Plain paragraph without headings.'))
    build.build()
    without_toc=(build.ROOT/'blog/first/index.html').read_text()
    self.assertNotIn('<details open class="toc">',without_toc)
    self.assertIn('Plain paragraph without headings.',without_toc)
    self.assertEqual(rss_before,(build.ROOT/'rss.xml').read_bytes())
    (content/'first.md').unlink();build.build();self.assertFalse((build.ROOT/'blog/first/index.html').exists())
    self.assertFalse((build.ROOT/build.tag_url('中文').lstrip('/')/'index.html').exists())
   finally:build.ROOT=original
if __name__=='__main__':unittest.main()
